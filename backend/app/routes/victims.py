"""Victim CRUD routes."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, ROLE_INVESTIGATOR, require_roles
from app.database.postgres import get_db
from app.models.victim import Victim
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.victim import VictimCreate, VictimOut, VictimUpdate
from app.services import audit_service
from app.services.base_service import BaseCRUDService

router = APIRouter(prefix="/victims", tags=["Victims"])
victim_crud = BaseCRUDService(Victim)


@router.get("", response_model=PaginatedResponse[VictimOut])
def list_victims(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {"full_name": q} if q else {}
    return victim_crud.list(db, page=page, page_size=page_size, filters=filters)


@router.get("/{victim_id}", response_model=VictimOut)
def get_victim(victim_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return victim_crud.get(db, victim_id)


@router.post("", response_model=VictimOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def create_victim(payload: VictimCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    victim = victim_crud.create(db, payload.model_dump())
    audit_service.log_action(db, current_user, "CREATE", "Victim", str(victim.id))
    return victim


@router.put("/{victim_id}", response_model=VictimOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def update_victim(victim_id: uuid.UUID, payload: VictimUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    victim = victim_crud.update(db, victim_id, payload.model_dump(exclude_unset=True))
    audit_service.log_action(db, current_user, "UPDATE", "Victim", str(victim_id))
    return victim
