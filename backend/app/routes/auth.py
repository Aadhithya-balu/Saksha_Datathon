"""Authentication routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, require_roles
from app.core.config import settings
from app.database.postgres import get_db
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserCreate, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, payload.username, payload.password)
    tokens = auth_service.issue_tokens(user)
    return TokenResponse(**tokens, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    tokens = auth_service.refresh_access_token(db, payload.refresh_token)
    return TokenResponse(**tokens, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    # Stateless JWT: logout is enforced client-side by discarding tokens.
    # For server-side revocation, add a token blacklist (e.g. Redis) here.
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        district=current_user.district,
        station=current_user.station,
        is_active=current_user.is_active,
        role=current_user.role.name,
        created_at=current_user.created_at,
    )


@router.post("/register", response_model=UserOut, dependencies=[Depends(require_roles(ROLE_ADMIN))])
def register(payload: UserCreate, db: Session = Depends(get_db)):
    user = auth_service.register_user(db, payload)
    return UserOut(
        id=user.id, username=user.username, email=user.email, full_name=user.full_name,
        district=user.district, station=user.station, is_active=user.is_active,
        role=payload.role_name, created_at=user.created_at,
    )


@router.put("/change-password")
def change_password(payload: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_service.change_password(db, current_user, payload.old_password, payload.new_password)
    return {"message": "Password updated successfully"}
