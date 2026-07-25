"""Crime search + CRUD routes."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, require_roles
from app.database.postgres import get_db
from app.models.crime import CrimeCase
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.crime import CrimeCaseCreate, CrimeCaseOut, CrimeCaseUpdate, CrimeTimelineEvent
from app.services import audit_service
from app.services.crime_service import crime_crud, get_crime_timeline

router = APIRouter(prefix="/crimes", tags=["Crimes"], dependencies=[Depends(require_roles(*ALL_ROLES))])


@router.get("", response_model=PaginatedResponse[CrimeCaseOut])
def list_crimes(
    q: str | None = None,
    status: str | None = None,
    category_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "occurred_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(CrimeCase)
    if status:
        query = query.filter(CrimeCase.status == status)
    if category_id:
        query = query.filter(CrimeCase.category_id == category_id)
    if location_id:
        query = query.filter(CrimeCase.location_id == location_id)
    if date_from:
        query = query.filter(CrimeCase.occurred_at >= date_from)
    if date_to:
        query = query.filter(CrimeCase.occurred_at <= date_to)
    if q:
        query = query.filter(CrimeCase.description.ilike(f"%{q}%"))

    total = query.count()
    from sqlalchemy import asc, desc as sa_desc
    column = getattr(CrimeCase, sort_by, CrimeCase.occurred_at)
    query = query.order_by(sa_desc(column) if sort_order == "desc" else asc(column))

    results = query.offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=results)


@router.get("/{crime_id}", response_model=CrimeCaseOut)
def get_crime(crime_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return crime_crud.get(db, crime_id)


@router.get("/{crime_id}/timeline", response_model=list[CrimeTimelineEvent])
def crime_timeline(crime_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_crime_timeline(db, crime_id)


@router.post("", response_model=CrimeCaseOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_CRIME_ANALYST))])
def create_crime(payload: CrimeCaseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    crime = crime_crud.create(db, payload.model_dump())
    audit_service.log_action(db, current_user, "CREATE", "CrimeCase", str(crime.id))
    return crime


@router.put("/{crime_id}", response_model=CrimeCaseOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_CRIME_ANALYST))])
def update_crime(crime_id: uuid.UUID, payload: CrimeCaseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    crime = crime_crud.update(db, crime_id, payload.model_dump(exclude_unset=True))
    audit_service.log_action(db, current_user, "UPDATE", "CrimeCase", str(crime_id))
    return crime


@router.delete("/{crime_id}", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def delete_crime(crime_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    crime_crud.delete(db, crime_id)
    audit_service.log_action(db, current_user, "DELETE", "CrimeCase", str(crime_id))
    return {"message": "Crime case deleted"}
