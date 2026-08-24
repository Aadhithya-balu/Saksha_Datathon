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


def _coerce_indicator_entry(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize one indicator row (CSV or DB) into the module's entry shape."""
    urban_type = row.get("urbanization_type")
    if not isinstance(urban_type, str) or not urban_type.strip():
        urban_type = "rural"
    entry: dict[str, Any] = {"type": urban_type.strip(), "unemployment_rate": None}
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
    # Back-compat defaults used across this module.
    for key in ("population_lakhs", "area_sq_km", "literacy_rate", "sex_ratio", "avg_income_lakhs"):
        entry[key] = entry.get(key) or 0
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
    return {
        "source": source,
        "file": "backend/data/socioeconomic/karnataka_socioeconomic_indicators.csv",
        "table": _INDICATOR_TABLE if (source or "").startswith("supabase_") else None,
        "version": _DATASET_VERSION,
        "demo_data": True,
        "data_years": years,
        "districts": sorted(reference.keys()),
        "district_count": len(reference),
        "indicators": [
            "population_lakhs", "area_sq_km", "literacy_rate", "sex_ratio",
            "avg_income_lakhs", "unemployment_rate", "urbanization_share_pct",
        ],
        "approximations": ["avg_income_lakhs", "unemployment_rate"],
        "notes": [
            "Census 2011 base figures; income and unemployment are documented approximations.",
            f"Updatable in Supabase via backend/scripts/socioeconomic_indicators.sql ({_INDICATOR_TABLE} table).",
        ],
    }

# Karnataka urbanization reference (for classification)
URBANIZATION_TIERS = {
    "urban": {"label": "Urban", "crime_multiplier": 1.35, "color": "#C94A2A"},
    "semi_urban": {"label": "Semi-Urban", "crime_multiplier": 1.0, "color": "#D4820A"},
    "rural": {"label": "Rural", "crime_multiplier": 0.75, "color": "#1E6FD9"},
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
    """Crime distribution by urban vs rural classification."""
    rows = (
        db.query(Location.district, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .group_by(Location.district)
        .all()
    )

    reference = district_reference()
    urban_rural_buckets = {"urban": 0, "semi_urban": 0, "rural": 0}
    district_crimes = {}
    for district, count in rows:
        district_crimes[district] = count
        ref = reference.get(district, {})
        dtype = ref.get("type", "rural")
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
            }
            for k, v in urban_rural_buckets.items()
        ],
        "district_crime_density": _compute_district_density(district_crimes),
        "total_crimes": total,
    }


def get_socioeconomic_overlay(db: Session) -> dict[str, Any]:
    """Crime correlation with socio-economic indicators by district."""
    rows = (
        db.query(Location.district, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .group_by(Location.district)
        .all()
    )

    district_crimes = {d: c for d, c in rows}
    reference = district_reference()
    overlays = []

    for district, ref in reference.items():
        crime_count = district_crimes.get(district, 0)
        pop = ref["population_lakhs"]
        area = ref["area_sq_km"]
        density = round(pop * 100000 / area, 0) if area else 0
        crime_per_lakh = round(crime_count / pop, 1) if pop else 0
        crime_per_sqkm = round(crime_count / area, 4) if area else 0
        # Normalize crime rate to a 0-100 risk index (top district == 100) so it can be
        # plotted against socio-economic indicators on a common scale.
        unemployment_rate = ref.get("unemployment_rate")

        overlays.append({
            "district": district,
            "crime_count": crime_count,
            "population_lakhs": pop,
            "area_sq_km": area,
            "population_density": density,
            "crime_per_lakh": crime_per_lakh,
            "crime_per_sqkm": crime_per_sqkm,
            "urbanization_type": ref["type"],
            "literacy_rate": ref["literacy_rate"],
            "sex_ratio": ref["sex_ratio"],
            "avg_income_lakhs": ref["avg_income_lakhs"],
            "unemployment_rate": unemployment_rate,
            "urbanization_share_pct": ref.get("urbanization_share_pct"),
            "correlation_flags": _compute_correlation_flags(crime_per_lakh, ref),
        })

    overlays.sort(key=lambda x: x["crime_per_lakh"], reverse=True)

    max_crime_per_lakh = max((o["crime_per_lakh"] for o in overlays), default=0)
    for overlay in overlays:
        overlay["risk_index"] = (
            round(overlay["crime_per_lakh"] / max_crime_per_lakh * 100, 1) if max_crime_per_lakh else 0.0
        )

    literacy_correlation = _compute_correlation(
        [o["literacy_rate"] for o in overlays],
        [o["crime_per_lakh"] for o in overlays],
    )
    income_correlation = _compute_correlation(
        [o["avg_income_lakhs"] for o in overlays],
        [o["crime_per_lakh"] for o in overlays],
    )
    unemployment_pairs = [
        (o["unemployment_rate"], o["crime_per_lakh"]) for o in overlays if o["unemployment_rate"] is not None
    ]
    unemployment_correlation = _compute_correlation(
        [pair[0] for pair in unemployment_pairs],
        [pair[1] for pair in unemployment_pairs],
    )

    return {
        "districts": overlays,
        "correlations": {
            "literacy_vs_crime": literacy_correlation,
            "income_vs_crime": income_correlation,
            "unemployment_vs_crime": unemployment_correlation,
        },
        "insights": _generate_socio_insights(overlays),
        "dataset": dataset_info(),
    }


def get_population_crime_correlation(db: Session) -> dict[str, Any]:
    """Crime rate vs population density scatter data."""
    rows = (
        db.query(Location.district, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .group_by(Location.district)
        .all()
    )

    scatter_data = []
    reference = district_reference()
    for district, count in rows:
        ref = reference.get(district)
        if ref:
            pop = ref["population_lakhs"]
            area = ref["area_sq_km"]
            density = pop * 100000 / area
            scatter_data.append({
                "district": district,
                "crime_count": count,
                "crime_per_lakh": round(count / pop, 1) if pop else 0,
                "population_density": round(density, 0),
                "urbanization_type": ref["type"],
                "color": URBANIZATION_TIERS[ref["type"]]["color"],
            })

    return {"scatter": scatter_data, "total_districts": len(scatter_data)}


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
    result = []
    reference = district_reference()
    for district, count in district_crimes.items():
        ref = reference.get(district)
        if ref:
            pop = ref["population_lakhs"]
            area = ref["area_sq_km"]
            result.append({
                "district": district,
                "crime_count": count,
                "crime_per_lakh": round(count / pop, 1) if pop else 0,
                "crime_per_sqkm": round(count / area, 4) if area else 0,
                "population_lakhs": pop,
                "area_sq_km": area,
                "type": ref["type"],
            })
    result.sort(key=lambda x: x["crime_per_lakh"], reverse=True)
    return result


def _compute_correlation_flags(crime_per_lakh: float, ref: dict) -> list[str]:
    flags = []
    if crime_per_lakh > 30:
        flags.append("HIGH_CRIME_RATE")
    if ref["literacy_rate"] < 75:
        flags.append("LOW_LITERACY")
    if ref["avg_income_lakhs"] < 2.0:
        flags.append("LOW_INCOME")
    if ref["type"] == "urban" and crime_per_lakh > 25:
        flags.append("URBAN_HOTSPOT")
    return flags


def _compute_correlation(x: list[float], y: list[float]) -> float:
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
    insights = []
    if not overlays:
        return insights

    top = overlays[0]
    insights.append({
        "type": "high_risk_district",
        "title": f"Highest Crime Rate: {top['district']}",
        "description": f"{top['crime_per_lakh']} crimes per lakh population. {top['urbanization_type'].title()} area with {top['literacy_rate']}% literacy.",
    })

    low_income = [o for o in overlays if o["avg_income_lakhs"] < 2.0]
    if low_income:
        names = ", ".join(o["district"] for o in low_income[:3])
        insights.append({
            "type": "economic_correlation",
            "title": "Low-Income Districts with Elevated Crime",
            "description": f"Districts with avg income below Rs. 2 lakh: {names}. Higher crime rates correlate with lower economic indicators.",
        })

    urban_hotspots = [o for o in overlays if o["urbanization_type"] == "urban" and o["crime_per_lakh"] > 20]
    if urban_hotspots:
        names = ", ".join(o["district"] for o in urban_hotspots)
        insights.append({
            "type": "urban_crime",
            "title": "Urban Crime Concentration",
            "description": f"Urban districts ({names}) show disproportionately high crime rates, consistent with population density effects.",
        })

    rural_high = [o for o in overlays if o["urbanization_type"] == "rural" and o["crime_per_lakh"] > 15]
    if rural_high:
        names = ", ".join(o["district"] for o in rural_high)
        insights.append({
            "type": "rural_emerging",
            "title": "Emerging Rural Crime Patterns",
            "description": f"Rural districts ({names}) showing elevated crime rates. May indicate emerging criminal activity in underserved areas.",
        })

    return insights
