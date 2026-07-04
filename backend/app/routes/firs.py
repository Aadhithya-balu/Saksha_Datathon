"""FIR search + CRUD routes."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, ROLE_INVESTIGATOR, require_roles
from app.database.postgres import get_db
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.fir import FIRCreate, FIROut, FIRUpdate
from app.services import audit_service
from app.services.base_service import BaseCRUDService

router = APIRouter(prefix="/firs", tags=["FIRs"])
fir_crud = BaseCRUDService(FIR)


@router.get("", response_model=PaginatedResponse[FIROut])
def list_firs(
    status: str | None = None,
    section: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return fir_crud.list(db, page=page, page_size=page_size, filters={"status": status, "sections": section})


@router.get("/{fir_id}", response_model=FIROut)
def get_fir(fir_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return fir_crud.get(db, fir_id)


@router.get("/{fir_id}/linked-crimes")
def linked_crimes(fir_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    fir = fir_crud.get(db, fir_id)
    return {"crime_case_id": fir.crime_case_id}


@router.post("", response_model=FIROut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def create_fir(payload: FIRCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = payload.model_dump(exclude={"criminal_ids", "victim_ids"})
    fir = fir_crud.create(db, data)

    for criminal_id in payload.criminal_ids:
        db.add(FIRCriminalLink(fir_id=fir.id, criminal_id=criminal_id))
    for victim_id in payload.victim_ids:
        db.add(FIRVictimLink(fir_id=fir.id, victim_id=victim_id))
    db.flush()

    audit_service.log_action(db, current_user, "CREATE", "FIR", str(fir.id))
    return fir


@router.put("/{fir_id}", response_model=FIROut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def update_fir(fir_id: uuid.UUID, payload: FIRUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    fir = fir_crud.update(db, fir_id, payload.model_dump(exclude_unset=True))
    audit_service.log_action(db, current_user, "UPDATE", "FIR", str(fir_id))
    return fir
