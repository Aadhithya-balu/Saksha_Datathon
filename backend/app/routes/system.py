"""System-level endpoints: data mode, provenance summary, health metadata.

Issue #162 / #190: Provides a single source of truth for the runtime data mode
(production / demo / test) and dataset provenance statistics so the
frontend can display an authoritative global data-status indicator.

Issue #190 §3: the data mode is validated at configuration load time and this
endpoint reports the validated value via :func:`app.core.data_mode`.  It never
accepts an invalid mode at runtime.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import data_mode as data_mode_helper
from app.database.postgres import SessionLocal
from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.fir import FIR
from app.models.location import Location
from app.models.officer import Officer
from app.models.victim import Victim

router = APIRouter(prefix="/system", tags=["System"])

_PROVENANCE_TABLES = [
    ("crime_cases", CrimeCase),
    ("criminals", Criminal),
    ("firs", FIR),
    ("locations", Location),
    ("officers", Officer),
    ("victims", Victim),
]


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/data-mode")
def get_data_mode(db: Session = Depends(_get_db)):
    """Return the runtime data mode and dataset provenance summary.

    The frontend uses this endpoint to display a global data-mode badge
    and to decide whether to show DEMO / FALLBACK / LIVE indicators.

    Response fields:
      - mode: 'production' | 'demo' | 'test'
      - allow_demo_fallback: bool — whether fallback to demo data is permitted
      - show_demo_badges: bool — whether DEMO badges should be shown
      - provenance: per-table provenance counts
      - seed_record_count: total records with dataset_provenance='demo'
      - live_record_count: total records with dataset_provenance='live'
    """
    data_mode = data_mode_helper.get_data_mode()
    if data_mode not in data_mode_helper.VALID_MODES:
        # Defensive fail-safe (Issue #190 §3): never start ambiguity from an
        # unexpected mode value; refuse rather than silently presenting
        # demo data as live in an unlabelled context.
        raise HTTPException(status_code=503, detail="Invalid or missing data mode configuration.")
    allow_fallback = data_mode_helper.allows_demo_fallback()
    show_badges = data_mode_helper.show_demo_badges()  # always show badges so users know data provenance

    provenance: dict[str, dict[str, int]] = {}
    total_demo = 0
    total_live = 0

    for table_name, model_cls in _PROVENANCE_TABLES:
        try:
            counts = (
                db.query(
                    func.coalesce(model_cls.dataset_provenance, "unknown"),
                    func.count(),
                )
                .group_by(func.coalesce(model_cls.dataset_provenance, "unknown"))
                .all()
            )
            table_counts = {prov: cnt for prov, cnt in counts}
            provenance[table_name] = table_counts
            total_demo += table_counts.get("demo", 0)
            total_live += table_counts.get("live", 0)
        except Exception:
            provenance[table_name] = {"error": -1}

    return {
        "mode": data_mode,
        "allow_demo_fallback": allow_fallback,
        "show_demo_badges": show_badges,
        "provenance": provenance,
        "seed_record_count": total_demo,
        "live_record_count": total_live,
    }
