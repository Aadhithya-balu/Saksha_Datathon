"""Location CRUD routes."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, require_roles
from app.database.postgres import get_db
from app.models.location import Location
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.location import LocationCreate, LocationOut, LocationUpdate
from app.services import audit_service
from app.services.base_service import BaseCRUDService

router = APIRouter(prefix="/locations", tags=["Locations"])
location_crud = BaseCRUDService(Location)


@router.get("", response_model=PaginatedResponse[LocationOut])
def list_locations(
    district: str | None = None,
    station: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return location_crud.list(db, page=page, page_size=page_size, filters={"district": district, "station": station})


@router.get("/{location_id}", response_model=LocationOut)
def get_location(location_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return location_crud.get(db, location_id)


@router.post("", response_model=LocationOut, dependencies=[Depends(require_roles(ROLE_ADMIN))])
def create_location(payload: LocationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    location = location_crud.create(db, payload.model_dump())
    audit_service.log_action(db, current_user, "CREATE", "Location", str(location.id))
    return location


@router.put("/{location_id}", response_model=LocationOut, dependencies=[Depends(require_roles(ROLE_ADMIN))])
def update_location(location_id: uuid.UUID, payload: LocationUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    location = location_crud.update(db, location_id, payload.model_dump(exclude_unset=True))
    audit_service.log_action(db, current_user, "UPDATE", "Location", str(location_id))
    return location
