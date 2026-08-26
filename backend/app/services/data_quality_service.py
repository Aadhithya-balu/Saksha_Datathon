"""
Issue #164: Data Quality & Provenance Reporting Service.

Provides admin-level visibility into dataset provenance across all core tables,
distinguishing LIVE, MIGRATED, DEMO, and UNKNOWN records.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Canonical provenance values
PROVENANCE_LIVE = "live"
PROVENANCE_MIGRATED = "migrated"
PROVENANCE_DEMO = "demo"
PROVENANCE_UNKNOWN = "unknown"

ALL_PROVENANCE_VALUES = [PROVENANCE_LIVE, PROVENANCE_MIGRATED, PROVENANCE_DEMO, PROVENANCE_UNKNOWN]

# Core tables that carry dataset_provenance
_PROVENANCE_TABLES: list[tuple[str, type]] = []


def _get_provenance_tables() -> list[tuple[str, type]]:
    """Lazily resolve model classes to avoid import-time circular dependencies."""
    if _PROVENANCE_TABLES:
        return _PROVENANCE_TABLES

    from app.models.crime import CrimeCase
    from app.models.criminal import Criminal
    from app.models.victim import Victim
    from app.models.location import Location
    from app.models.fir import FIR
    from app.models.evidence import Evidence
    from app.models.officer import Officer

    _PROVENANCE_TABLES.extend([
        ("crime_cases", CrimeCase),
        ("criminals", Criminal),
        ("victims", Victim),
        ("locations", Location),
        ("firs", FIR),
        ("evidence", Evidence),
        ("officers", Officer),
    ])
    return _PROVENANCE_TABLES


def get_provenance_summary(db: Session) -> dict[str, Any]:
    """Return overall provenance counts across all core tables."""
    tables = _get_provenance_tables()
    totals: dict[str, int] = defaultdict(int)

    for table_name, model_cls in tables:
        try:
            counts = (
                db.query(model_cls.dataset_provenance, func.count())
                .group_by(model_cls.dataset_provenance)
                .all()
            )
            for provenance, count in counts:
                p = (provenance or "unknown").lower()
                totals[p] += count
        except Exception as exc:
            logger.warning(f"Could not query provenance for {table_name}: {exc}")
            totals["unknown"] += 0

    return {
        "total_records": sum(totals.values()),
        "by_provenance": {
            p: totals.get(p, 0) for p in ALL_PROVENANCE_VALUES
        },
    }


def get_provenance_by_entity(db: Session) -> dict[str, Any]:
    """Return per-entity-type provenance breakdown."""
    tables = _get_provenance_tables()
    breakdown: dict[str, dict[str, int]] = {}

    for table_name, model_cls in tables:
        try:
            counts = (
                db.query(model_cls.dataset_provenance, func.count())
                .group_by(model_cls.dataset_provenance)
                .all()
            )
            entity_counts: dict[str, int] = {}
            for provenance, count in counts:
                p = (provenance or "unknown").lower()
                entity_counts[p] = count
            breakdown[table_name] = {
                p: entity_counts.get(p, 0) for p in ALL_PROVENANCE_VALUES
            }
        except Exception as exc:
            logger.warning(f"Could not query entity provenance for {table_name}: {exc}")
            breakdown[table_name] = {p: 0 for p in ALL_PROVENANCE_VALUES}

    return breakdown


def get_data_quality_warnings(db: Session) -> list[dict[str, Any]]:
    """Identify potential data quality issues related to provenance."""
    warnings: list[dict[str, Any]] = []
    tables = _get_provenance_tables()

    for table_name, model_cls in tables:
        try:
            # Check for UNKNOWN provenance records
            unknown_count = (
                db.query(func.count())
                .filter(
                    func.lower(model_cls.dataset_provenance).in_(["unknown", ""])
                )
                .scalar()
            )
            if unknown_count and unknown_count > 0:
                warnings.append({
                    "type": "unknown_provenance",
                    "table": table_name,
                    "count": unknown_count,
                    "message": f"{unknown_count} record(s) in {table_name} have unknown provenance and should be reviewed.",
                    "severity": "medium",
                })

            # Check for NULL provenance
            null_count = (
                db.query(func.count())
                .filter(model_cls.dataset_provenance.is_(None))
                .scalar()
            )
            if null_count and null_count > 0:
                warnings.append({
                    "type": "null_provenance",
                    "table": table_name,
                    "count": null_count,
                    "message": f"{null_count} record(s) in {table_name} have NULL provenance.",
                    "severity": "high",
                })

            # Check for empty string provenance
            empty_count = (
                db.query(func.count())
                .filter(model_cls.dataset_provenance == "")
                .scalar()
            )
            if empty_count and empty_count > 0:
                warnings.append({
                    "type": "empty_provenance",
                    "table": table_name,
                    "count": empty_count,
                    "message": f"{empty_count} record(s) in {table_name} have empty string provenance.",
                    "severity": "high",
                })
        except Exception as exc:
            warnings.append({
                "type": "query_error",
                "table": table_name,
                "count": 0,
                "message": f"Could not audit provenance for {table_name}: {exc}",
                "severity": "low",
            })

    # Check for mixed demo+live in related records (e.g., a case with DEMO
    # provenance linked to officers or evidence with different provenance)
    try:
        from app.models.fir import FIR, FIRCriminalLink
        from app.models.crime import CrimeCase

        mixed = (
            db.query(FIR.id)
            .join(CrimeCase, FIR.crime_case_id == CrimeCase.id)
            .filter(
                func.lower(CrimeCase.dataset_provenance) == "demo",
                func.lower(FIR.dataset_provenance) != "demo",
            )
            .count()
        )
        if mixed > 0:
            warnings.append({
                "type": "mixed_provenance",
                "table": "firs->crime_cases",
                "count": mixed,
                "message": f"{mixed} FIR(s) are linked to DEMO cases but have non-DEMO provenance.",
                "severity": "medium",
            })
    except Exception:
        pass

    return warnings


def get_admin_data_quality_report(db: Session) -> dict[str, Any]:
    """Complete admin data quality report with provenance summary,
    entity breakdown, and warnings.
    """
    summary = get_provenance_summary(db)
    entity_breakdown = get_provenance_by_entity(db)
    warnings = get_data_quality_warnings(db)

    return {
        "summary": summary,
        "entity_breakdown": entity_breakdown,
        "warnings": warnings,
        "provenance_values": ALL_PROVENANCE_VALUES,
    }
