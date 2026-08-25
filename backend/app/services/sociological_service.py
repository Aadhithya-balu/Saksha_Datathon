"""Sociological insights service — demographic, geographic, and socio-economic crime analysis.

Computes crime correlations with population density, urban/rural classifications,
age/gender demographics, and socio-economic indicators using real DB data
combined with a versioned Karnataka socio-economic dataset
(backend/data/socioeconomic/karnataka_socioeconomic_indicators.csv).

Closes gap M3: indicator values are loaded from a versioned CSV dataset
(Census 2011 / Economic Survey / PLFS approximations) instead of hardcoded
code constants, and correlations are computed from actual joined data.
"""
from __future__ import annotations

import csv
import os
from functools import lru_cache
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.location import Location
from app.models.victim import Victim


# Karnataka district reference data (population in lakhs, area in sq km).
# FALLBACK ONLY — superseded by the versioned CSV dataset when present.
KARNATAKA_DISTRICTS = {
    "Bengaluru Urban": {"population_lakhs": 131.9, "area_sq_km": 741, "type": "urban", "literacy_rate": 88.5, "sex_ratio": 916, "avg_income_lakhs": 4.2},
    "Mysuru": {"population_lakhs": 30.0, "area_sq_km": 6268, "type": "semi_urban", "literacy_rate": 84.1, "sex_ratio": 970, "avg_income_lakhs": 2.8},
    "Mangaluru": {"population_lakhs": 25.0, "area_sq_km": 3550, "type": "semi_urban", "literacy_rate": 86.3, "sex_ratio": 980, "avg_income_lakhs": 2.6},
    "Belagavi": {"population_lakhs": 47.8, "area_sq_km": 13415, "type": "semi_urban", "literacy_rate": 80.5, "sex_ratio": 960, "avg_income_lakhs": 2.1},
    "Ballari": {"population_lakhs": 25.3, "area_sq_km": 4265, "type": "semi_urban", "literacy_rate": 72.4, "sex_ratio": 973, "avg_income_lakhs": 2.0},
    "Kalaburagi": {"population_lakhs": 25.7, "area_sq_km": 10951, "type": "rural", "literacy_rate": 68.1, "sex_ratio": 959, "avg_income_lakhs": 1.8},
    "Hassan": {"population_lakhs": 18.9, "area_sq_km": 6814, "type": "rural", "literacy_rate": 76.3, "sex_ratio": 978, "avg_income_lakhs": 2.0},
    "Tumkuru": {"population_lakhs": 26.8, "area_sq_km": 10597, "type": "rural", "literacy_rate": 75.2, "sex_ratio": 971, "avg_income_lakhs": 1.9},
    "Dharwad": {"population_lakhs": 18.5, "area_sq_km": 4260, "type": "semi_urban", "literacy_rate": 82.7, "sex_ratio": 965, "avg_income_lakhs": 2.3},
}

DATASET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "socioeconomic", "karnataka_socioeconomic_indicators.csv",
)

_DATASET_NUMERIC_COLUMNS = (
    "population_lakhs", "area_sq_km", "literacy_rate", "sex_ratio",
    "avg_income_lakhs", "unemployment_rate", "urbanization_share_pct",
)

_INDICATOR_TABLE = "socioeconomic_indicators"
_DATASET_VERSION = "2.0.0"

# Explicit data states — the frontend must be able to distinguish a real zero
# from missing/unknown evidence (issue 7 §6). Values are never fabricated.
DATA_AVAILABLE = "AVAILABLE"
DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
MAPPING_MATCHED = "MATCHED"
MAPPING_UNMAPPED = "UNMAPPED"

# Indicator registry — provenance metadata for every analytic field (issue 7 §8).
# `source_dataset` documents where the value originates; `approximated` marks
# indicators that are documented approximations rather than census figures.
INDICATOR_META: dict[str, dict[str, Any]] = {
    "population_lakhs": {"name": "Population", "unit": "lakhs", "source_dataset": "Census of India 2011", "approximated": False},
    "area_sq_km": {"name": "Area", "unit": "sq km", "source_dataset": "Census of India 2011", "approximated": False},
    "literacy_rate": {"name": "Literacy Rate", "unit": "%", "source_dataset": "Census of India 2011", "approximated": False},
    "sex_ratio": {"name": "Sex Ratio", "unit": "females per 1000 males", "source_dataset": "Census of India 2011", "approximated": False},
    "avg_income_lakhs": {"name": "Average Income", "unit": "lakhs INR", "source_dataset": "Economic Survey approximation", "approximated": True},
    "unemployment_rate": {"name": "Unemployment Rate", "unit": "%", "source_dataset": "PLFS approximation", "approximated": True},
    "urbanization_share_pct": {"name": "Urbanization Share", "unit": "%", "source_dataset": "Census of India 2011", "approximated": False},
}

# District alias table (issue 7 §4): alternate/historical spellings and DB-side
# naming variants resolved to the canonical dataset key. Matching is done on a
# normalized (lowercase, collapsed-whitespace) form; display names are never
# mutated silently — every resolved row reports its match method.
DISTRICT_ALIASES: dict[str, str] = {
    "bangalore": "Bengaluru Urban",
    "bengaluru": "Bengaluru Urban",
    "bangalore urban": "Bengaluru Urban",
    "bengaluru urban": "Bengaluru Urban",
    "chikkaballapura": "Chikkaballapur",
    "chikballapur": "Chikkaballapur",
    "bagalkote": "Bagalkot",
    "yadagir": "Yadgir",
    "shimoga": "Shivamogga",
    "bellary": "Ballari",
    "gulbarga": "Kalaburagi",
    "tumkur": "Tumkuru",
    "tumakuru": "Tumkuru",
    "mangalore": "Mangaluru",
    # The dataset's "Mangaluru" row carries Dakshina Kannada district figures
    # (Census 2011: 20.9 lakh pop / 4866 sq km), so the official district name
    # resolves to that canonical key.
    "dakshina kannada": "Mangaluru",
}


def _normalize_district_name(name: Any) -> str:
    return " ".join(str(name or "").strip().lower().split())


def resolve_district(name: Any, reference: dict[str, dict[str, Any]] | None = None) -> tuple[str | None, str]:
    """Resolve a raw district string to a canonical dataset key.

    Returns (canonical_key | None, match_method) where match_method is one of
    ``exact``, ``case_insensitive``, ``alias`` or ``unmapped``. Unresolvable
    names are NEVER silently reassigned (issue 7 §5).
    """
    reference = district_reference() if reference is None else reference
    needle = _normalize_district_name(name)
    if not needle:
        return None, "unmapped"
    raw_key = str(name).strip() if name is not None else ""
    if raw_key in reference:
        return raw_key, "exact"
    by_normalized = {_normalize_district_key(k): k for k in reference}
    if needle in by_normalized:
        return by_normalized[needle], "case_insensitive"
    canonical = DISTRICT_ALIASES.get(needle)
    if canonical and canonical in reference:
        return canonical, "alias"
    return None, "unmapped"


def _normalize_district_key(key: str) -> str:
    return " ".join(key.lower().replace("_", " ").split())


def _indicator_period_label(entry: dict[str, Any]) -> tuple[Any, str]:
    """Return (period_value, human_label) from the record's data_year.

    The label preserves the actual source period (issue 7 §7) — e.g.
    Census-year data is labelled 'Census 2011', never presented as current.
    """
    year = entry.get("data_year")
    if year is None:
        return None, DATA_UNAVAILABLE
    try:
        year_int = int(year)
    except (TypeError, ValueError):
        return None, DATA_UNAVAILABLE
    if year_int <= 2011:
        return year_int, f"Census {year_int}"
    return year_int, str(year_int)


def _indicator_state(entry: dict[str, Any] | None, column: str) -> tuple[str, Any]:
    """Return (status, value) for one indicator cell.

    status is DATA_AVAILABLE only when a real recorded numeric value exists;
    missing values surface as DATA_UNAVAILABLE and are never coerced to zero.
    """
    if entry is None:
        return DATA_UNAVAILABLE, None
    value = entry.get(column)
    if value is None:
        return DATA_UNAVAILABLE, None
    return DATA_AVAILABLE, value


def _coerce_indicator_entry(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize one indicator row (CSV or DB) into the module's entry shape.

    Missing/unparseable values stay None (issue 7 §6) — no fabricated zeros.
    """
    urban_type = row.get("urbanization_type")
    if isinstance(urban_type, str) and urban_type.strip():
        entry_type: str | None = urban_type.strip()
    else:
        entry_type = None
    entry: dict[str, Any] = {"type": entry_type, "unemployment_rate": None}
    for column in _DATASET_NUMERIC_COLUMNS:
        raw = row.get(column)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            entry[column] = None
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            entry[column] = None
            continue
        # Smallint columns arrive as floats from NUMERIC — keep ints integral.
        entry[column] = int(value) if column in ("sex_ratio", "data_year") and value == int(value) else value
    return entry


def _load_indicators_from_db() -> dict[str, dict[str, Any]]:
    """Load indicators from the Supabase table when it exists and is populated.

    Raises silently-caught exceptions upward; callers fall back to CSV.
    """
    from sqlalchemy import text

    from app.database.postgres import SessionLocal  # local import avoids cycles

    session = SessionLocal()
    try:
        rows = session.execute(
            text(f"SELECT * FROM {_INDICATOR_TABLE}")  # nosec: fixed identifier
        ).mappings().all()
        loaded: dict[str, dict[str, Any]] = {}
        for row in rows:
            district = str(row.get("district") or "").strip()
            if district:
                loaded[district] = _coerce_indicator_entry(dict(row))
                source_year = row.get("data_year")
                loaded[district]["data_year"] = float(source_year) if source_year is not None else None
        return loaded
    finally:
        session.close()


@lru_cache(maxsize=1)
def _load_socioeconomic_dataset() -> tuple[dict[str, dict[str, Any]], str | None]:
    """Load Karnataka socio-economic indicators.

    Order of preference:
      1. Supabase `socioeconomic_indicators` table (updatable without deploys).
      2. Bundled versioned CSV (offline / demo fallback).
      3. Built-in constants (last-resort degradation).

    Returns (district_reference, source_label).
    """
    fallback = {k: {**v, "unemployment_rate": None} for k, v in KARNATAKA_DISTRICTS.items()}
    try:
        db_rows = _load_indicators_from_db()
        if db_rows:
            return db_rows, f"supabase_{_INDICATOR_TABLE}"
    except Exception:  # noqa: BLE001 - any DB failure degrades to CSV fallback
        pass
    if not os.path.isfile(DATASET_PATH):
        return fallback, "built_in_fallback"
    try:
        loaded: dict[str, dict[str, Any]] = {}
        with open(DATASET_PATH, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                district = (row.get("district") or "").strip()
                if not district:
                    continue
                entry = _coerce_indicator_entry(row)
                year_raw = row.get("data_year")
                try:
                    entry["data_year"] = float(year_raw) if str(year_raw or "").strip() else None
                except ValueError:
                    entry["data_year"] = None
                loaded[district] = entry
        if not loaded:
            return fallback, "built_in_fallback"
        return loaded, "versioned_csv"
    except OSError:
        return fallback, "built_in_fallback"


def district_reference() -> dict[str, dict[str, Any]]:
    """District socio-economic reference currently backing all sociological analytics."""
    reference, _source = _load_socioeconomic_dataset()
    return reference


def dataset_info() -> dict[str, Any]:
    """Provenance metadata for the active socio-economic dataset."""
    reference, source = _load_socioeconomic_dataset()
    years = sorted({int(v["data_year"]) for v in reference.values() if v.get("data_year")})
    records_without_year = [d for d, v in reference.items() if not v.get("data_year")]
    partial_records = [
        {"district": d, "available_indicators": sum(1 for c in _DATASET_NUMERIC_COLUMNS if v.get(c) is not None),
         "total_indicators": len(_DATASET_NUMERIC_COLUMNS)}
        for d, v in sorted(reference.items())
        if any(v.get(c) is None for c in _DATASET_NUMERIC_COLUMNS)
    ]
    # Duplicate detection on normalized names (issue 7 §4).
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for district in reference:
        normalized = _normalize_district_name(district)
        if normalized in seen:
            duplicates.append(f"{seen[normalized]} / {district}")
        else:
            seen[normalized] = district
    return {
        "source": source,
        "file": "backend/data/socioeconomic/karnataka_socioeconomic_indicators.csv",
        "table": _INDICATOR_TABLE if (source or "").startswith("supabase_") else None,
        "version": _DATASET_VERSION,
        "demo_data": True,
        "data_years": years,
        "records_missing_period": sorted(records_without_year),
        "districts": sorted(reference.keys()),
        "district_count": len(reference),
        "duplicate_district_keys": duplicates,
        "indicators": [
            {
                "column": column,
                "name": meta["name"],
                "unit": meta["unit"],
                "source_dataset": meta["source_dataset"],
                "approximated": meta["approximated"],
            }
            for column, meta in INDICATOR_META.items()
        ],
        "approximations": [c for c, m in INDICATOR_META.items() if m["approximated"]],
        "partial_records": partial_records,
        "notes": [
            "Census 2011 base figures; income and unemployment are documented approximations.",
            "Indicator values are reported as recorded; missing values surface as DATA_UNAVAILABLE, never as zero.",
            f"Updatable in Supabase via backend/scripts/socioeconomic_indicators.sql ({_INDICATOR_TABLE} table).",
        ],
    }

# Karnataka urbanization reference (for classification)
URBANIZATION_TIERS = {
    "urban": {"label": "Urban", "crime_multiplier": 1.35, "color": "#C94A2A"},
    "semi_urban": {"label": "Semi-Urban", "crime_multiplier": 1.0, "color": "#D4820A"},
    "rural": {"label": "Rural", "crime_multiplier": 0.75, "color": "#1E6FD9"},
    # Districts with no valid socio-economic mapping are reported explicitly
    # instead of being silently defaulted to a classification (issue 7 §5).
    "unmapped": {"label": "Unmapped", "crime_multiplier": None, "color": "#64748B"},
}


def get_data_quality_report(db: Session) -> dict[str, Any]:
    """Dataset coverage + district-mapping validation report (issue 7 §3-§7).

    Everything is computed from the live database and the active indicator
    dataset — expected counts, coverage percentages, missing districts and
    unmapped rows are never hardcoded.
    """
    from datetime import datetime, timezone

    reference, source = _load_socioeconomic_dataset()
    source_block = _overlay_source_block(reference, source)

    # Operational universe = every district actually referenced by locations.
    db_districts = sorted({d for (d,) in db.query(Location.district).distinct() if d})
    expected_count = len(db_districts)

    matched: list[dict[str, Any]] = []
    unmapped_db: list[dict[str, Any]] = []
    resolved_keys: set[str] = set()
    for district in db_districts:
        resolved, method = resolve_district(district, reference)
        if resolved:
            matched.append({"district": district, "canonical_district": resolved, "match_method": method})
            resolved_keys.add(resolved)
        else:
            unmapped_db.append({
                "district": district,
                "mapping_status": MAPPING_UNMAPPED,
                "limitation": "No socio-economic record maps to this district; its indicators are reported as DATA_UNAVAILABLE.",
            })

    # Dataset rows that no operational district resolves to (informational).
    orphan_dataset_rows = sorted(set(reference) - resolved_keys)

    # Per-indicator coverage over the operational universe (issue 7 §3).
    indicator_coverage = []
    for column in _DATASET_NUMERIC_COLUMNS:
        meta = INDICATOR_META[column]
        available_districts, missing_districts = [], []
        for district in db_districts:
            resolved, _method = resolve_district(district, reference)
            status, _value = _indicator_state(reference.get(resolved) if resolved else None, column)
            if status == DATA_AVAILABLE:
                available_districts.append(district)
            else:
                missing_districts.append(district)
        coverage_pct = round(len(available_districts) / expected_count * 100, 1) if expected_count else 0.0
        indicator_coverage.append({
            "indicator": column,
            "name": meta["name"],
            "unit": meta["unit"],
            "source_dataset": meta["source_dataset"],
            "approximated": meta["approximated"],
            "expected": expected_count,
            "available": len(available_districts),
            "missing": len(missing_districts),
            "missing_districts": missing_districts,
            "coverage_pct": coverage_pct,
        })

    # Per-record completeness for every matched operational district.
    record_completeness = []
    for item in matched:
        entry = reference[item["canonical_district"]]
        available_cols = [c for c in _DATASET_NUMERIC_COLUMNS if entry.get(c) is not None]
        period_value, period_label = _indicator_period_label(entry)
        record_completeness.append({
            "district": item["district"],
            "canonical_district": item["canonical_district"],
            "match_method": item["match_method"],
            "available_indicators": len(available_cols),
            "total_indicators": len(_DATASET_NUMERIC_COLUMNS),
            "missing_indicators": [c for c in _DATASET_NUMERIC_COLUMNS if c not in available_cols],
            "completeness_pct": round(len(available_cols) / len(_DATASET_NUMERIC_COLUMNS) * 100, 1),
            "partial_record": len(available_cols) < len(_DATASET_NUMERIC_COLUMNS),
            "source_period": period_value,
            "period_label": period_label,
        })

    overall_available = sum(i["available"] for i in indicator_coverage)
    overall_expected = sum(i["expected"] for i in indicator_coverage)
    years = sorted({int(v["data_year"]) for v in reference.values() if v.get("data_year")})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            **source_block,
            "version": _DATASET_VERSION,
            "record_count": len(reference),
            "data_years": years,
            "records_missing_period": sorted(d for d, v in reference.items() if not v.get("data_year")),
        },
        "expected_districts": {
            "count": expected_count,
            "basis": "distinct districts in the locations table",
            "districts": db_districts,
        },
        "mapping_validation": {
            "matched_count": len(matched),
            "matched": matched,
            "unmapped_count": len(unmapped_db),
            "unmapped_districts": unmapped_db,
            "orphan_dataset_rows": {
                "count": len(orphan_dataset_rows),
                "note": "Dataset records that no operational district currently maps to.",
                "districts": orphan_dataset_rows,
            },
            "duplicate_canonical_keys": dataset_info().get("duplicate_district_keys", []),
        },
        "indicator_coverage": indicator_coverage,
        "overall_coverage_pct": round(overall_available / overall_expected * 100, 1) if overall_expected else 0.0,
        "record_completeness": record_completeness,
        "limitations": [
            "Indicator base figures are Census 2011; they are historical and are labelled with their source period.",
            "avg_income_lakhs and unemployment_rate are documented approximations, not survey measurements.",
            "Districts without a mappable socio-economic record are reported UNMAPPED; their indicators are never estimated.",
            "Derived per-lakh/per-sqkm rates are withheld when the required denominator evidence is missing.",
        ],
    }


def get_demographic_analysis(db: Session) -> dict[str, Any]:
    """Crime distribution by victim age groups and gender."""
    victims = db.query(Victim).all()

    age_groups = {"0-18": 0, "19-25": 0, "26-35": 0, "36-50": 0, "51-65": 0, "65+": 0, "Unknown": 0}
    gender_dist = {"Male": 0, "Female": 0, "Other": 0, "Unknown": 0}

    for v in victims:
        if v.age is not None:
            if v.age <= 18:
                age_groups["0-18"] += 1
            elif v.age <= 25:
                age_groups["19-25"] += 1
            elif v.age <= 35:
                age_groups["26-35"] += 1
            elif v.age <= 50:
                age_groups["36-50"] += 1
            elif v.age <= 65:
                age_groups["51-65"] += 1
            else:
                age_groups["65+"] += 1
        else:
            age_groups["Unknown"] += 1

        gender = (v.gender or "").strip().title()
        if gender in gender_dist:
            gender_dist[gender] += 1
        else:
            gender_dist["Unknown"] += 1

    total = len(victims)
    return {
        "age_groups": [{"group": k, "count": v, "percentage": round(v / total * 100, 1) if total else 0} for k, v in age_groups.items()],
        "gender_distribution": [{"gender": k, "count": v, "percentage": round(v / total * 100, 1) if total else 0} for k, v in gender_dist.items()],
        "total_victims": total,
    }


def get_urban_rural_analysis(db: Session) -> dict[str, Any]:
    """Crime distribution by urban vs rural classification.

    Districts that cannot be mapped to a socio-economic record are counted in
    an explicit ``unmapped`` bucket and listed — never defaulted to rural.
    """
    rows = (
        db.query(Location.district, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .group_by(Location.district)
        .all()
    )

    reference = district_reference()
    urban_rural_buckets = {"urban": 0, "semi_urban": 0, "rural": 0, "unmapped": 0}
    district_crimes = {}
    unmapped_districts = []
    for district, count in rows:
        district_crimes[district] = count
        resolved, _method = resolve_district(district, reference)
        ref = reference.get(resolved) if resolved else None
        dtype = (ref or {}).get("type")
        if dtype not in urban_rural_buckets:
            dtype = "unmapped"
            if district not in unmapped_districts:
                unmapped_districts.append(district)
        urban_rural_buckets[dtype] += count

    total = sum(urban_rural_buckets.values()) or 1

    return {
        "urban_rural_distribution": [
            {
                "type": k,
                "label": URBANIZATION_TIERS[k]["label"],
                "count": v,
                "percentage": round(v / total * 100, 1),
                "color": URBANIZATION_TIERS[k]["color"],
                "classification_status": DATA_UNAVAILABLE if k == "unmapped" else DATA_AVAILABLE,
            }
            for k, v in urban_rural_buckets.items()
        ],
        "unmapped_districts": sorted(unmapped_districts),
        "district_crime_density": _compute_district_density(district_crimes),
        "total_crimes": total,
    }


def _overlay_source_block(reference: dict[str, dict[str, Any]], source: str | None) -> dict[str, Any]:
    """Shared provenance block describing the active indicator dataset."""
    if (source or "").startswith("supabase_"):
        origin = f"Supabase table `{_INDICATOR_TABLE}`"
    elif source == "versioned_csv":
        origin = "backend/data/socioeconomic/karnataka_socioeconomic_indicators.csv"
    else:
        origin = "built-in reference constants (degraded fallback — not queryable source data)"
    return {
        "dataset_name": "Karnataka Socio-Economic Indicators",
        "version": _DATASET_VERSION,
        "origin": origin,
        "source_key": source,
    }


def get_socioeconomic_overlay(db: Session) -> dict[str, Any]:
    """Crime correlation with socio-economic indicators by district.

    Every row is evidence-backed (issue 7): it reports the mapping status of
    the district, per-indicator data status, and the source period of the
    underlying record. Missing indicators surface as DATA_UNAVAILABLE —
    they are never coerced to zero or an estimate. Unmapped districts are
    listed explicitly instead of being dropped or silently reclassified.
    """
    rows = (
        db.query(Location.district, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .group_by(Location.district)
        .all()
    )

    district_crimes = {d: c for d, c in rows}
    reference = district_reference()
    _, dataset_source = _load_socioeconomic_dataset()
    source_block = _overlay_source_block(reference, dataset_source)

    overlays = []
    unmapped_districts = []

    # 1. Operational universe first: every district that actually has crime records.
    for district in sorted(district_crimes):
        resolved, method = resolve_district(district, reference)
        ref = reference.get(resolved) if resolved else None
        crime_count = district_crimes[district]
        if ref is None:
            unmapped_districts.append(district)
            overlays.append(_unmapped_overlay_row(district, crime_count, source_block))
            continue

        period_value, period_label = _indicator_period_label(ref)
        statuses = {column: _indicator_state(ref, column)[0] for column in _DATASET_NUMERIC_COLUMNS}
        pop_status, pop = _indicator_state(ref, "population_lakhs")
        area_status, area = _indicator_state(ref, "area_sq_km")
        lit_status, literacy = _indicator_state(ref, "literacy_rate")
        income_status, income = _indicator_state(ref, "avg_income_lakhs")

        density = round(pop * 100000 / area, 0) if pop and area else None
        crime_per_lakh = round(crime_count / pop, 1) if pop else None
        crime_per_sqkm = round(crime_count / area, 4) if area else None

        overlays.append({
            "district": district,
            "canonical_district": resolved,
            "mapping_status": MAPPING_MATCHED,
            "match_method": method,
            "crime_count": crime_count,
            # Derived rates are None when their denominator evidence is missing —
            # a real zero is only reported when the recorded value is zero.
            "population_lakhs": pop,
            "area_sq_km": area,
            "population_density": density,
            "crime_per_lakh": crime_per_lakh,
            "crime_per_sqkm": crime_per_sqkm,
            "derived_metric_status": {
                "population_density": DATA_AVAILABLE if density is not None else DATA_UNAVAILABLE,
                "crime_per_lakh": DATA_AVAILABLE if crime_per_lakh is not None else DATA_UNAVAILABLE,
                "crime_per_sqkm": DATA_AVAILABLE if crime_per_sqkm is not None else DATA_UNAVAILABLE,
            },
            "data_status": statuses,
            "urbanization_type": ref.get("type"),
            "literacy_rate": literacy,
            "sex_ratio": _indicator_state(ref, "sex_ratio")[1],
            "avg_income_lakhs": income,
            "unemployment_rate": _indicator_state(ref, "unemployment_rate")[1],
            "urbanization_share_pct": _indicator_state(ref, "urbanization_share_pct")[1],
            "source_dataset": source_block["dataset_name"],
            "source_period": period_value,
            "period_label": period_label,
            "record_completeness_pct": round(
                sum(1 for s in statuses.values() if s == DATA_AVAILABLE) / len(statuses) * 100, 1
            ),
            "correlation_flags": _compute_correlation_flags(crime_per_lakh, ref),
            "_status_fields": {
                "population_lakhs": pop_status,
                "area_sq_km": area_status,
                "literacy_rate": lit_status,
                "avg_income_lakhs": income_status,
            },
        })

    # 2. Dataset-only districts (no crime records) so coverage gaps stay visible.
    covered = {o["canonical_district"] for o in overlays if o["mapping_status"] == MAPPING_MATCHED}
    for canonical in sorted(reference):
        if canonical in covered:
            continue
        period_value, period_label = _indicator_period_label(reference[canonical])
        statuses = {column: _indicator_state(reference[canonical], column)[0] for column in _DATASET_NUMERIC_COLUMNS}
        pop = reference[canonical].get("population_lakhs")
        area = reference[canonical].get("area_sq_km")
        overlays.append({
            "district": canonical,
            "canonical_district": canonical,
            "mapping_status": MAPPING_MATCHED,
            "match_method": "dataset_only",
            "crime_count": 0,
            "crime_count_note": "NO_CRIME_RECORDS_IN_DB",
            "population_lakhs": pop,
            "area_sq_km": area,
            "population_density": round(pop * 100000 / area, 0) if pop and area else None,
            "crime_per_lakh": None,
            "crime_per_sqkm": None,
            "derived_metric_status": {
                "population_density": DATA_AVAILABLE if pop and area else DATA_UNAVAILABLE,
                "crime_per_lakh": DATA_UNAVAILABLE,
                "crime_per_sqkm": DATA_UNAVAILABLE,
            },
            "data_status": statuses,
            "urbanization_type": reference[canonical].get("type"),
            "literacy_rate": reference[canonical].get("literacy_rate"),
            "sex_ratio": reference[canonical].get("sex_ratio"),
            "avg_income_lakhs": reference[canonical].get("avg_income_lakhs"),
            "unemployment_rate": reference[canonical].get("unemployment_rate"),
            "urbanization_share_pct": reference[canonical].get("urbanization_share_pct"),
            "source_dataset": source_block["dataset_name"],
            "source_period": period_value,
            "period_label": period_label,
            "record_completeness_pct": round(
                sum(1 for s in statuses.values() if s == DATA_AVAILABLE) / len(statuses) * 100, 1
            ),
            "correlation_flags": [],
            "_status_fields": {},
        })

    # Rank matched districts with a usable crime rate; unmapped rows keep their
    # explicit state at the end rather than fabricating a rankable zero.
    ranked = [o for o in overlays if o["mapping_status"] == MAPPING_MATCHED]
    ranked.sort(key=lambda x: x["crime_per_lakh"] if x["crime_per_lakh"] is not None else -1, reverse=True)
    tail = [o for o in overlays if o["mapping_status"] != MAPPING_MATCHED]
    overlays = ranked + tail

    rateable = [o["crime_per_lakh"] for o in ranked if o["crime_per_lakh"] is not None]
    max_crime_per_lakh = max(rateable) if rateable else None
    for overlay in overlays:
        overlay["risk_index"] = (
            round(overlay["crime_per_lakh"] / max_crime_per_lakh * 100, 1)
            if max_crime_per_lakh and overlay["crime_per_lakh"] is not None else None
        )

    literacy_correlation = _compute_correlation(
        [o["literacy_rate"] for o in ranked],
        [o["crime_per_lakh"] for o in ranked],
        require_pair=True,
    )
    income_correlation = _compute_correlation(
        [o["avg_income_lakhs"] for o in ranked],
        [o["crime_per_lakh"] for o in ranked],
        require_pair=True,
    )
    unemployment_correlation = _compute_correlation(
        [o["unemployment_rate"] for o in ranked],
        [o["crime_per_lakh"] for o in ranked],
        require_pair=True,
    )

    return {
        "districts": overlays,
        "correlations": {
            "literacy_vs_crime": literacy_correlation["coefficient"],
            "income_vs_crime": income_correlation["coefficient"],
            "unemployment_vs_crime": unemployment_correlation["coefficient"],
        },
        "correlation_details": {
            "literacy_vs_crime": literacy_correlation,
            "income_vs_crime": income_correlation,
            "unemployment_vs_crime": unemployment_correlation,
        },
        "unmapped_districts": sorted(unmapped_districts),
        "insights": _generate_socio_insights(ranked),
        "provenance": source_block,
        "dataset": dataset_info(),
    }


def _unmapped_overlay_row(district: str, crime_count: int, source_block: dict[str, Any]) -> dict[str, Any]:
    """Explicit UNMAPPED row for a district with no socio-economic record."""
    unavailable = {column: DATA_UNAVAILABLE for column in _DATASET_NUMERIC_COLUMNS}
    return {
        "district": district,
        "canonical_district": None,
        "mapping_status": MAPPING_UNMAPPED,
        "match_method": "unmapped",
        "limitation": (
            f"No socio-economic record maps to district '{district}'. "
            "Indicator values are withheld rather than estimated."
        ),
        "crime_count": crime_count,
        "population_lakhs": None,
        "area_sq_km": None,
        "population_density": None,
        "crime_per_lakh": None,
        "crime_per_sqkm": None,
        "derived_metric_status": {
            "population_density": DATA_UNAVAILABLE,
            "crime_per_lakh": DATA_UNAVAILABLE,
            "crime_per_sqkm": DATA_UNAVAILABLE,
        },
        "data_status": unavailable,
        "urbanization_type": None,
        "literacy_rate": None,
        "sex_ratio": None,
        "avg_income_lakhs": None,
        "unemployment_rate": None,
        "urbanization_share_pct": None,
        "source_dataset": source_block["dataset_name"],
        "source_period": None,
        "period_label": DATA_UNAVAILABLE,
        "record_completeness_pct": 0.0,
        "correlation_flags": [],
        "_status_fields": {},
    }


def get_population_crime_correlation(db: Session) -> dict[str, Any]:
    """Crime rate vs population density scatter data.

    Districts without a mappable socio-economic record are included with an
    explicit UNMAPPED state instead of being silently dropped.
    """
    rows = (
        db.query(Location.district, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .group_by(Location.district)
        .all()
    )

    reference = district_reference()
    scatter_data = []
    unmapped_districts = []
    for district, count in rows:
        resolved, method = resolve_district(district, reference)
        ref = reference.get(resolved) if resolved else None
        if ref is None:
            unmapped_districts.append(district)
            scatter_data.append({
                "district": district,
                "crime_count": count,
                "crime_per_lakh": None,
                "population_density": None,
                "urbanization_type": None,
                "color": URBANIZATION_TIERS["unmapped"]["color"],
                "mapping_status": MAPPING_UNMAPPED,
                "limitation": "No socio-economic record maps to this district; point excluded from correlation evidence.",
            })
            continue
        pop = ref.get("population_lakhs")
        area = ref.get("area_sq_km")
        density = (pop * 100000 / area) if pop and area else None
        crime_per_lakh = round(count / pop, 1) if pop else None
        urban_type = ref.get("type")
        scatter_data.append({
            "district": district,
            "canonical_district": resolved,
            "match_method": method,
            "mapping_status": MAPPING_MATCHED,
            "crime_count": count,
            "crime_per_lakh": crime_per_lakh,
            "population_density": round(density, 0) if density is not None else None,
            "urbanization_type": urban_type,
            "color": URBANIZATION_TIERS[urban_type]["color"] if urban_type in URBANIZATION_TIERS else URBANIZATION_TIERS["unmapped"]["color"],
            "source_period": _indicator_period_label(ref)[0],
        })

    matched_points = [
        p for p in scatter_data
        if p["mapping_status"] == MAPPING_MATCHED and p["population_density"] is not None and p["crime_per_lakh"] is not None
    ]
    correlation = _compute_correlation(
        [p["population_density"] for p in matched_points],
        [p["crime_per_lakh"] for p in matched_points],
        require_pair=True,
    )

    return {
        "scatter": scatter_data,
        "total_districts": len(scatter_data),
        "unmapped_districts": sorted(unmapped_districts),
        "density_crime_correlation": correlation,
    }


def get_temporal_demographic_analysis(db: Session) -> dict[str, Any]:
    """Crime by hour of day and day of week patterns."""

    hour_buckets = {f"{h:02d}:00": 0 for h in range(24)}
    dow_buckets = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_counts = {d: 0 for d in dow_buckets}
    month_counts = {}

    cases = db.query(CrimeCase.occurred_at).filter(CrimeCase.occurred_at.isnot(None)).all()

    for (occurred_at,) in cases:
        if occurred_at:
            hour_key = f"{occurred_at.hour:02d}:00"
            hour_buckets[hour_key] = hour_buckets.get(hour_key, 0) + 1

            dow_idx = occurred_at.weekday()
            dow_counts[dow_buckets[dow_idx]] += 1

            month_key = occurred_at.strftime("%Y-%m")
            month_counts[month_key] = month_counts.get(month_key, 0) + 1

    total_hours = sum(hour_buckets.values()) or 1
    night_crime = sum(hour_buckets[f"{h:02d}:00"] for h in range(20, 24)) + sum(hour_buckets[f"{h:02d}:00"] for h in range(0, 6))
    weekend_crime = dow_counts.get("Saturday", 0) + dow_counts.get("Sunday", 0)

    return {
        "hourly_distribution": [{"hour": k, "count": v, "percentage": round(v / total_hours * 100, 1)} for k, v in hour_buckets.items()],
        "day_of_week_distribution": [{"day": k, "count": v, "percentage": round(v / total_hours * 100, 1)} for k, v in dow_counts.items()],
        "monthly_trend": [{"month": k, "count": v} for k, v in sorted(month_counts.items())],
        "night_crime_percentage": round(night_crime / total_hours * 100, 1),
        "weekend_crime_percentage": round(weekend_crime / total_hours * 100, 1),
    }


def get_offender_demographics(db: Session) -> dict[str, Any]:
    """Criminal offender demographic analysis."""
    criminals = db.query(Criminal).all()

    age_groups = {"18-25": 0, "26-35": 0, "36-50": 0, "50+": 0, "Unknown": 0}
    gender_dist = {"Male": 0, "Female": 0, "Unknown": 0}
    status_dist = {"at_large": 0, "arrested": 0, "convicted": 0, "deceased": 0}

    from datetime import date
    today = date.today()

    for c in criminals:
        if c.date_of_birth:
            age = (today - c.date_of_birth).days // 365
            if age <= 25:
                age_groups["18-25"] += 1
            elif age <= 35:
                age_groups["26-35"] += 1
            elif age <= 50:
                age_groups["36-50"] += 1
            else:
                age_groups["50+"] += 1
        else:
            age_groups["Unknown"] += 1

        gender = (c.gender or "").strip().title()
        if gender in gender_dist:
            gender_dist[gender] += 1
        else:
            gender_dist["Unknown"] += 1

        status_dist[c.status] = status_dist.get(c.status, 0) + 1

    total = len(criminals) or 1
    return {
        "age_groups": [{"group": k, "count": v, "percentage": round(v / total * 100, 1)} for k, v in age_groups.items()],
        "gender_distribution": [{"gender": k, "count": v, "percentage": round(v / total * 100, 1)} for k, v in gender_dist.items()],
        "status_distribution": [{"status": k, "count": v, "percentage": round(v / total * 100, 1)} for k, v in status_dist.items()],
        "total_offenders": len(criminals),
    }


def _compute_district_density(district_crimes: dict) -> list[dict]:
    """Per-district crime density with explicit mapping/data states.

    Districts that cannot be mapped are retained (mapping_status UNMAPPED)
    instead of being dropped; derived rates are None when their denominator
    evidence is missing.
    """
    result = []
    reference = district_reference()
    for district, count in district_crimes.items():
        resolved, method = resolve_district(district, reference)
        ref = reference.get(resolved) if resolved else None
        if ref is None:
            result.append({
                "district": district,
                "canonical_district": None,
                "match_method": "unmapped",
                "mapping_status": MAPPING_UNMAPPED,
                "crime_count": count,
                "crime_per_lakh": None,
                "crime_per_sqkm": None,
                "population_lakhs": None,
                "area_sq_km": None,
                "type": None,
            })
            continue
        pop = ref.get("population_lakhs")
        area = ref.get("area_sq_km")
        result.append({
            "district": district,
            "canonical_district": resolved,
            "match_method": method,
            "mapping_status": MAPPING_MATCHED,
            "crime_count": count,
            "crime_per_lakh": round(count / pop, 1) if pop else None,
            "crime_per_sqkm": round(count / area, 4) if area else None,
            "population_lakhs": pop,
            "area_sq_km": area,
            "type": ref.get("type"),
        })
    result.sort(key=lambda x: x["crime_per_lakh"] if x["crime_per_lakh"] is not None else -1, reverse=True)
    return result


def _compute_correlation_flags(crime_per_lakh: float | None, ref: dict) -> list[str]:
    """Rule flags computed only from actually-available evidence (issue 7 §2)."""
    flags = []
    if crime_per_lakh is None:
        return flags
    if crime_per_lakh > 30:
        flags.append("HIGH_CRIME_RATE")
    literacy = ref.get("literacy_rate")
    if literacy is not None and literacy < 75:
        flags.append("LOW_LITERACY")
    income = ref.get("avg_income_lakhs")
    if income is not None and income < 2.0:
        flags.append("LOW_INCOME")
    urban_type = ref.get("type")
    if urban_type == "urban" and crime_per_lakh > 25:
        flags.append("URBAN_HOTSPOT")
    return flags


def _compute_correlation(x: list[Any], y: list[Any], require_pair: bool = False) -> Any:
    """Pearson correlation over recorded values only.

    With ``require_pair`` (issue 7), rows where either side is missing are
    excluded from the computation instead of being treated as zero, and the
    result carries its sample size plus an explicit status.
    """
    if require_pair:
        pairs = [(xi, yi) for xi, yi in zip(x, y) if xi is not None and yi is not None]
        n = len(pairs)
        if n < 3:
            return {"coefficient": None, "sample_size": n, "status": "INSUFFICIENT_MATCHED_DATA"}
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        return {
            "coefficient": _pearson(xs, ys),
            "sample_size": n,
            "excluded_missing": len(x) - n,
            "status": DATA_AVAILABLE,
        }
    return _pearson(x, y)


def _pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return 0.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
    den_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return round(num / (den_x * den_y), 3)


def _generate_socio_insights(overlays: list[dict]) -> list[dict[str, str]]:
    """Insights derived strictly from available evidence (issue 7 §2).

    Descriptions cite the source period of the indicators they rely on; rows
    with missing evidence are skipped rather than described with zeros.
    """
    rateable = [o for o in overlays if o["crime_per_lakh"] is not None]
    if not rateable:
        return []

    period = rateable[0].get("period_label")
    period_note = f" Indicators reflect {period}." if period and period != DATA_UNAVAILABLE else ""

    insights = []
    top = rateable[0]
    literacy_desc = (
        f" {top['literacy_rate']}% literacy ({period})." if top["literacy_rate"] is not None else ""
    )
    insights.append({
        "type": "high_risk_district",
        "title": f"Highest Crime Rate: {top['district']}",
        "description": f"{top['crime_per_lakh']} crimes per lakh population."
        f"{literacy_desc} {top['urbanization_type'].title()} area.{period_note}",
    })

    low_income = [o for o in overlays if o["avg_income_lakhs"] is not None and o["avg_income_lakhs"] < 2.0]
    if len(low_income) >= 2:
        names = ", ".join(o["district"] for o in low_income[:3])
        insights.append({
            "type": "economic_correlation",
            "title": "Low-Income Districts with Elevated Crime",
            "description": f"Districts with recorded avg income below Rs. 2 lakh: {names}."
            " Income figures are documented approximations — treat as indicative only.",
        })

    urban_hotspots = [
        o for o in overlays
        if o["urbanization_type"] == "urban" and o["crime_per_lakh"] is not None and o["crime_per_lakh"] > 20
    ]
    if urban_hotspots:
        names = ", ".join(o["district"] for o in urban_hotspots)
        insights.append({
            "type": "urban_crime",
            "title": "Urban Crime Concentration",
            "description": f"Urban districts ({names}) show disproportionately high crime rates, consistent with population density effects.{period_note}",
        })

    rural_high = [
        o for o in overlays
        if o["urbanization_type"] == "rural" and o["crime_per_lakh"] is not None and o["crime_per_lakh"] > 15
    ]
    if rural_high:
        names = ", ".join(o["district"] for o in rural_high)
        insights.append({
            "type": "rural_emerging",
            "title": "Emerging Rural Crime Patterns",
            "description": f"Rural districts ({names}) showing elevated crime rates. May indicate emerging criminal activity in underserved areas.{period_note}",
        })

    return insights


DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_temporal_hotspot_matrix(
    db: Session,
    district: str | None = None,
    location_id: str | None = None,
) -> dict[str, Any]:
    """Hour x day-of-week incident matrix (issue #143 gap 131.3).

    Returns the true observed cross-tabulation of incidents by hour (0-23)
    and weekday, optionally filtered to one district or station location,
    plus statistically-flagged peak cells (standardized residuals under an
    independence model) so the frontend heatmap no longer has to fabricate
    a deterministic baseline distribution.
    """
    query = (
        db.query(CrimeCase.id, CrimeCase.case_number, CrimeCase.occurred_at, Location.district, Location.station)
        .join(Location, CrimeCase.location_id == Location.id)
        .filter(CrimeCase.occurred_at.isnot(None))
    )
    if district:
        query = query.filter(Location.district == district)
    if location_id:
        query = query.filter(Location.id == location_id)
    rows = query.all()

    counts = [[0] * 7 for _ in range(24)]          # counts[hour][weekday]
    case_refs: dict[tuple[int, int], list[str]] = {}
    for case_id, case_number, occurred_at, row_district, station in rows:
        hour = occurred_at.hour
        dow = occurred_at.weekday()
        counts[hour][dow] += 1
        case_refs.setdefault((hour, dow), []).append(case_number)

    grand_total = sum(sum(row_counts) for row_counts in counts)
    hour_totals = [sum(counts[h]) for h in range(24)]
    day_totals = [sum(counts[h][d] for h in range(24)) for d in range(7)]

    matrix = []
    peaks = []
    if grand_total:
        for hour in range(24):
            cells = []
            for dow in range(7):
                count = counts[hour][dow]
                expected = hour_totals[hour] * day_totals[dow] / grand_total
                std_residual = (count - expected) / expected ** 0.5 if expected > 0 else 0.0
                cells.append(
                    {
                        "day": DAYS_OF_WEEK[dow],
                        "count": count,
                        "percentage": round(count / grand_total * 100, 2),
                        "expected": round(expected, 2),
                        "std_residual": round(std_residual, 3),
                    }
                )
                if count > 0:
                    peaks.append({"hour": hour, "day": DAYS_OF_WEEK[dow], "count": count, "std_residual": std_residual})
            matrix.append(
                {
                    "hour": hour,
                    "label": f"{hour:02d}:00-{(hour + 1) % 24:02d}:00",
                    "total": hour_totals[hour],
                    "cells": cells,
                }
            )

    peaks.sort(key=lambda item: (-item["std_residual"], -item["count"]))
    significant_peaks = [
        {**peak, "std_residual": round(peak["std_residual"], 3)}
        for peak in peaks
        if peak["std_residual"] > 1.5
    ][:8]

    busiest = max(range(24), key=lambda h: hour_totals[h]) if grand_total else None
    return {
        "filters": {"district": district, "location_id": location_id},
        "days": DAYS_OF_WEEK,
        "matrix": matrix,
        "grand_total": grand_total,
        "hour_totals": [{"hour": h, "count": hour_totals[h]} for h in range(24)],
        "day_totals": [{"day": DAYS_OF_WEEK[d], "count": day_totals[d]} for d in range(7)],
        "peaks": significant_peaks,
        "busiest_hour": busiest,
        "night_share_pct": round(
            sum(hour_totals[h] for h in (20, 21, 22, 23, 0, 1, 2, 3, 4, 5)) / grand_total * 100, 1
        ) if grand_total else 0.0,
        "weekend_share_pct": round((day_totals[5] + day_totals[6]) / grand_total * 100, 1) if grand_total else 0.0,
    }
