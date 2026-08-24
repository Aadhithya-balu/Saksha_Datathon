"""Criminal feature extraction.

Reads Criminal + FIR + CrimeCase + Location rows from the shared SQLAlchemy
session and produces typed, numeric feature vectors consumed by every criminal
AI model.  No preprocessing logic is duplicated from other modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink

# ── stable feature column order ──────────────────────────────────────────────
# Issue #144 gap 132.3 appended four MO-derived features after the legacy ten.
# Inference loaders retrain automatically when a stored artifact predates them.
LEGACY_FEATURE_NAMES: list[str] = [
    "fir_count",           # total FIRs linked
    "open_fir_count",      # FIRs whose case is still open
    "distinct_districts",  # number of unique districts active in
    "distinct_categories", # number of distinct crime categories
    "high_severity_count", # FIRs in high-severity categories
    "age_years",           # age derived from date_of_birth (0 if unknown)
    "status_encoded",      # at_large=2, arrested=1, convicted/deceased=0
    "recency_days",        # days since most recent FIR (0 if none)
    "avg_case_age_days",   # mean age of linked cases in days
    "multi_district_flag", # 1 if active in >1 district
]

MO_FEATURE_NAMES: list[str] = [
    "mo_tag_count",        # canonical MO tags across summary + linked cases
    "mo_night_flag",       # 1 if night-operation signature present
    "mo_weapon_flag",      # 1 if tool/weapon usage signature present
    "mo_vehicle_flag",     # 1 if vehicle-based crime signature present
]

FEATURE_NAMES: list[str] = LEGACY_FEATURE_NAMES + MO_FEATURE_NAMES


@dataclass(frozen=True)
class CriminalFeatureVector:
    criminal_id: str
    feature_names: list[str]
    values: np.ndarray                    # shape (len(FEATURE_NAMES),)
    raw: dict[str, Any] = field(default_factory=dict)  # human-readable extras


def _age(dob: date | None) -> float:
    if dob is None:
        return 0.0
    today = date.today()
    return float(today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)))


def _status_encode(status: str) -> float:
    return {"at_large": 2.0, "arrested": 1.0, "convicted": 0.0, "deceased": 0.0}.get(status, 1.0)


def _days_since(dt: datetime | None) -> float:
    if dt is None:
        return 0.0
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    return max(0.0, (now - dt).total_seconds() / 86400.0)


def _mo_tags_for_criminal(criminal: Criminal, firs: list[FIR]) -> set[str]:
    """Canonical + slug MO tags from the offender's summary and linked cases
    (issue #144 gap 132.3). Lazy import keeps the AI layer decoupled at module
    load time."""
    from app.services.mo_pattern_service import slugify_phrase, tags_for_text

    tags = set(tags_for_text(criminal.mo_summary))
    for fir in firs:
        case = fir.crime_case
        if case is None or not case.mo_tags:
            continue
        for phrase in case.mo_tags.split(","):
            phrase = phrase.strip()
            if not phrase:
                continue
            matched = tags_for_text(phrase)
            if matched:
                tags.update(matched)
            else:
                slug = slugify_phrase(phrase)
                if slug:
                    tags.add(slug)
    return tags


def extract_for_criminal(db: Session, criminal: Criminal) -> CriminalFeatureVector:
    """Build a feature vector for a single Criminal ORM object."""
    links: list[FIRCriminalLink] = criminal.fir_links or []
    firs: list[FIR] = [lnk.fir for lnk in links if lnk.fir]

    fir_count = float(len(firs))
    open_fir_count = 0.0
    districts: set[str] = set()
    categories: set[str] = set()
    high_severity_count = 0.0
    case_ages: list[float] = []
    most_recent_filed: datetime | None = None

    for fir in firs:
        case: CrimeCase | None = fir.crime_case
        if case is None:
            continue
        if case.status == "open":
            open_fir_count += 1.0
        if case.location:
            districts.add(case.location.district)
        if case.category:
            categories.add(case.category.name)
            if case.category.severity == "high":
                high_severity_count += 1.0
        case_ages.append(_days_since(case.occurred_at))
        if most_recent_filed is None or fir.filed_at > most_recent_filed:
            most_recent_filed = fir.filed_at

    distinct_districts = float(len(districts))
    distinct_categories = float(len(categories))
    avg_case_age = float(np.mean(case_ages)) if case_ages else 0.0
    recency_days = _days_since(most_recent_filed)
    multi_district_flag = 1.0 if distinct_districts > 1 else 0.0

    from app.services.mo_pattern_service import (
        NIGHT_TAG_NAMES,
        VEHICLE_TAG_NAMES,
        WEAPON_TAG_NAMES,
    )

    mo_tags = _mo_tags_for_criminal(criminal, firs)

    values = np.array(
        [
            fir_count,
            open_fir_count,
            distinct_districts,
            distinct_categories,
            high_severity_count,
            _age(criminal.date_of_birth),
            _status_encode(criminal.status),
            recency_days,
            avg_case_age,
            multi_district_flag,
            float(len(mo_tags)),
            1.0 if mo_tags & NIGHT_TAG_NAMES else 0.0,
            1.0 if mo_tags & WEAPON_TAG_NAMES else 0.0,
            1.0 if mo_tags & VEHICLE_TAG_NAMES else 0.0,
        ],
        dtype=np.float64,
    )

    raw = {
        "name": criminal.full_name,
        "status": criminal.status,
        "fir_count": int(fir_count),
        "districts": sorted(districts),
        "categories": sorted(categories),
        "mo_tags": sorted(mo_tags),
    }

    return CriminalFeatureVector(
        criminal_id=str(criminal.id),
        feature_names=list(FEATURE_NAMES),
        values=values,
        raw=raw,
    )


def extract_all(db: Session) -> list[CriminalFeatureVector]:
    """Extract feature vectors for every criminal in the database."""
    from sqlalchemy.orm import joinedload

    criminals = (
        db.query(Criminal)
        .options(
            joinedload(Criminal.fir_links)
            .joinedload(FIRCriminalLink.fir)
            .joinedload(FIR.crime_case)
            .joinedload(CrimeCase.category),
            joinedload(Criminal.fir_links)
            .joinedload(FIRCriminalLink.fir)
            .joinedload(FIR.crime_case)
            .joinedload(CrimeCase.location),
        )
        .all()
    )
    return [extract_for_criminal(db, c) for c in criminals]
