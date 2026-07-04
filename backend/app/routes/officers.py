"""Officer CRUD + performance routes."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, require_roles
from app.database.postgres import get_db
from app.models.fir import FIR
from app.models.officer import Officer
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.officer import OfficerCreate, OfficerOut, OfficerPerformance, OfficerUpdate
from app.services import audit_service
from app.services.base_service import BaseCRUDService

router = APIRouter(prefix="/officers", tags=["Officers"])
officer_crud = BaseCRUDService(Officer)


@router.get("", response_model=PaginatedResponse[OfficerOut])
def list_officers(
    district: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return officer_crud.list(db, page=page, page_size=page_size, filters={"district": district})


@router.get("/{officer_id}", response_model=OfficerOut)
def get_officer(officer_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return officer_crud.get(db, officer_id)


@router.get("/{officer_id}/performance", response_model=OfficerPerformance)
def officer_performance(officer_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    officer_crud.get(db, officer_id)
    firs = db.query(FIR).filter(FIR.investigating_officer_id == officer_id).all()
    closed = sum(1 for f in firs if f.status == "closed")
    return OfficerPerformance(
        officer_id=officer_id,
        total_firs_handled=len(firs),
        cases_closed=closed,
        cases_open=len(firs) - closed,
        avg_resolution_days=None,
    )


@router.post("", response_model=OfficerOut, dependencies=[Depends(require_roles(ROLE_ADMIN))])
def create_officer(payload: OfficerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    officer = officer_crud.create(db, payload.model_dump())
    audit_service.log_action(db, current_user, "CREATE", "Officer", str(officer.id))
    return officer


@router.put("/{officer_id}", response_model=OfficerOut, dependencies=[Depends(require_roles(ROLE_ADMIN))])
def update_officer(officer_id: uuid.UUID, payload: OfficerUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    officer = officer_crud.update(db, officer_id, payload.model_dump(exclude_unset=True))
    audit_service.log_action(db, current_user, "UPDATE", "Officer", str(officer_id))
    return officer
