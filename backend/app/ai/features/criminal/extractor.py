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
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink
from app.models.location import Location

# ── stable feature column order ──────────────────────────────────────────────
FEATURE_NAMES: list[str] = [
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
        ],
        dtype=np.float64,
    )

    raw = {
        "name": criminal.full_name,
        "status": criminal.status,
        "fir_count": int(fir_count),
        "districts": sorted(districts),
        "categories": sorted(categories),
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
