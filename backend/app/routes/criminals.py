"""Criminal search + CRUD + MO-profile routes."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, ROLE_INVESTIGATOR, require_roles
from app.database.postgres import get_db
from app.models.criminal import Criminal
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.criminal import CriminalCreate, CriminalOut, CriminalUpdate, MOProfile
from app.services import audit_service
from app.services.base_service import BaseCRUDService

router = APIRouter(prefix="/criminals", tags=["Criminals"])
criminal_crud = BaseCRUDService(Criminal)


@router.get("", response_model=PaginatedResponse[CriminalOut])
def list_criminals(
    q: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {"status": status}
    if q:
        filters["full_name"] = q
    return criminal_crud.list(db, page=page, page_size=page_size, filters=filters)


@router.get("/repeat-offenders", response_model=list[CriminalOut])
def repeat_offenders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Flags criminals linked to 3+ FIRs. Simple SQL heuristic for the datathon;
    swap for the ML-scored repeat-offender output once that model is ready.
    """
    from sqlalchemy import func
    from app.models.fir import FIRCriminalLink

    rows = (
        db.query(Criminal)
        .join(FIRCriminalLink, FIRCriminalLink.criminal_id == Criminal.id)
        .group_by(Criminal.id)
        .having(func.count(FIRCriminalLink.id) >= 3)
        .all()
    )
    return rows


@router.get("/{criminal_id}", response_model=CriminalOut)
def get_criminal(criminal_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return criminal_crud.get(db, criminal_id)


@router.get("/{criminal_id}/mo-profile", response_model=MOProfile)
def mo_profile(criminal_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    criminal = criminal_crud.get(db, criminal_id)
    return MOProfile(
        criminal_id=criminal.id,
        preferred_crime_types=[],
        common_time_window=None,
        common_tools=[],
        jurisdictions_active=[],
        linked_incidents_count=len(criminal.fir_links),
    )


@router.post("", response_model=CriminalOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def create_criminal(payload: CriminalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    criminal = criminal_crud.create(db, payload.model_dump())
    audit_service.log_action(db, current_user, "CREATE", "Criminal", str(criminal.id))
    return criminal


@router.put("/{criminal_id}", response_model=CriminalOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def update_criminal(criminal_id: uuid.UUID, payload: CriminalUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    criminal = criminal_crud.update(db, criminal_id, payload.model_dump(exclude_unset=True))
    audit_service.log_action(db, current_user, "UPDATE", "Criminal", str(criminal_id))
    return criminal
