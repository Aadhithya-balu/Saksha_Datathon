"""Evidence CRUD routes."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, ROLE_INVESTIGATOR, require_roles
from app.database.postgres import get_db
from app.models.evidence import Evidence
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.evidence import EvidenceCreate, EvidenceOut
from app.services import audit_service
from app.services.base_service import BaseCRUDService

router = APIRouter(prefix="/evidence", tags=["Evidence"])
evidence_crud = BaseCRUDService(Evidence)


@router.get("", response_model=PaginatedResponse[EvidenceOut])
def list_evidence(
    crime_case_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return evidence_crud.list(db, page=page, page_size=page_size, filters={"crime_case_id": crime_case_id})


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(evidence_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return evidence_crud.get(db, evidence_id)


@router.post("", response_model=EvidenceOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def create_evidence(payload: EvidenceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = evidence_crud.create(db, payload.model_dump())
    audit_service.log_action(db, current_user, "CREATE", "Evidence", str(item.id))
    return item
