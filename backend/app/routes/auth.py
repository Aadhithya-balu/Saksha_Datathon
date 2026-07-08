"""Authentication routes."""
from sqlalchemy.exc import SQLAlchemyError
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.core.exceptions import AppException
from app.database.postgres import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.services import auth_service
from app.services.auth_service import EmployeeSession

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        session = auth_service.authenticate_user(db, payload.username, payload.password)
        tokens = auth_service.issue_tokens(session)
        return TokenResponse(**tokens, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    except AppException:
        raise
    except SQLAlchemyError as exc:
        raise AppException(
            "Authentication service is temporarily unavailable.",
            code="AUTH_SERVICE_UNAVAILABLE",
            status_code=503,
        ) from exc


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    tokens = auth_service.refresh_access_token(db, payload.refresh_token)
    return TokenResponse(**tokens, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/logout")
def logout(current_user: EmployeeSession = Depends(get_current_user)):
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_me(current_user: EmployeeSession = Depends(get_current_user)):
    return {
        "id": current_user.username,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": f"{current_user.username.lower()}@ksp.gov.in",
        "district": current_user.district,
        "station": current_user.station,
        "is_active": True,
        "role": current_user.role_name,
        "created_at": None,
    }
