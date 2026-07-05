"""Crime-case-specific business logic on top of the generic CRUD service."""
from sqlalchemy.orm import Session

from app.models.crime import CrimeCase
from app.schemas.crime import CrimeTimelineEvent
from app.services.base_service import BaseCRUDService

crime_crud = BaseCRUDService(CrimeCase)


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
