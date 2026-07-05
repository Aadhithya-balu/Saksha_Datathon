"""User management routes (admin only)."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, require_roles
from app.database.postgres import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserOut, UserUpdate
from app.services import audit_service
from app.services.base_service import BaseCRUDService

router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(require_roles(ROLE_ADMIN))])
user_crud = BaseCRUDService(User)


def _to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id, username=user.username, email=user.email, full_name=user.full_name,
        district=user.district, station=user.station, is_active=user.is_active,
        role=user.role.name, created_at=user.created_at,
    )


@router.get("", response_model=PaginatedResponse[UserOut])
def list_users(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    result = user_crud.list(db, page=page, page_size=page_size)
    result["results"] = [_to_out(u) for u in result["results"]]
    return result


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, payload: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = user_crud.update(db, user_id, payload.model_dump(exclude_unset=True))
    audit_service.log_action(db, current_user, "UPDATE", "User", str(user_id))
    return _to_out(user)
