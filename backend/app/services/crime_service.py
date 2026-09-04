"""Crime-case-specific business logic on top of the generic CRUD service."""
import json

from sqlalchemy.orm import Session

from app.models.crime import CrimeCase
from app.models.user import User
from app.schemas.crime import CrimeTimelineEvent
from app.services.base_service import BaseCRUDService
from app.services import audit_service
from app.services.case_status import (
    InvalidStatusTransitionError,
    is_immutable,
    status_display_label,
    validate_transition,
)

crime_crud = BaseCRUDService(CrimeCase)


def apply_status_transition(
    db: Session,
    case: CrimeCase,
    new_status: str,
    actor: User,
    ip_address: str | None = None,
) -> str:
    """Validate and apply a status transition on *case*.

    Calls ``validate_transition`` (raises ``InvalidStatusTransitionError`` on
    violation), persists the canonical new status, and writes an audit entry
    that records the previous and new status.

    Returns the canonical new status string.
    """
    canonical = validate_transition(case.status, new_status)
    prev_status = case.status
    case.status = canonical
    db.add(case)
    db.flush()

    audit_service.log_action(
        db,
        actor,
        "STATUS_TRANSITION",
        "CrimeCase",
        str(case.id),
        details=f"{status_display_label(prev_status)} → {status_display_label(canonical)}",
        ip_address=ip_address,
        metadata_json=json.dumps({
            "previous_status": prev_status,
            "new_status": canonical,
            "case_number": case.case_number,
        }),
    )
    return canonical


def get_crime_timeline(db: Session, crime_id) -> list[CrimeTimelineEvent]:
    """
    Builds a simple timeline from linked FIR + status changes.
    (Extend with full status-history table if deeper audit trail is required.)
    """
    crime = crime_crud.get(db, crime_id)
    timeline = [CrimeTimelineEvent(timestamp=crime.reported_at, event="Crime reported", actor=None)]
    for fir in crime.firs:
        timeline.append(
            CrimeTimelineEvent(timestamp=fir.filed_at, event=f"FIR {fir.fir_number} registered", actor=fir.complainant_name)
        )
    timeline.append(CrimeTimelineEvent(timestamp=crime.updated_at, event=f"Status: {crime.status}", actor=None))
    return sorted(timeline, key=lambda e: e.timestamp)
