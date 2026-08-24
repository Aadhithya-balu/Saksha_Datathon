"""Authentication routes."""
import time
from collections import defaultdict
from sqlalchemy.exc import SQLAlchemyError
from fastapi import APIRouter, Depends, Request, UploadFile, File
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, require_roles
from app.core.config import settings
from app.core.exceptions import AppException
from app.database.postgres import get_db
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserCreate, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Simple in-memory rate limiter: {ip: [(timestamp, ...)]}
_login_attempts: dict[str, list[float]] = defaultdict(list)
_REFRESH_WINDOW = 60  # seconds
_MAX_LOGIN_ATTEMPTS = 10
_MAX_REFRESH_ATTEMPTS = 30


def _rate_limit(ip: str, max_attempts: int, window: int, store: dict) -> None:
    if settings.APP_ENV == "test" or settings.DATABASE_URL and settings.DATABASE_URL.startswith("sqlite"):
        return  # skip rate limiting in test/SQLite mode
    now = time.time()
    store[ip] = [t for t in store[ip] if now - t < window]
    if len(store[ip]) >= max_attempts:
        retry_after = int(store[ip][0] + window - now) + 1
        raise AppException(
            f"Too many requests. Try again in {retry_after}s.",
            code="RATE_LIMITED",
            status_code=429,
        )
    store[ip].append(now)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    _rate_limit(ip, _MAX_LOGIN_ATTEMPTS, _REFRESH_WINDOW, _login_attempts)
    try:
        user = auth_service.authenticate_user(db, payload.username, payload.password)
        tokens = auth_service.issue_tokens(user)
        return TokenResponse(**tokens, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    except AppException:
        raise
    except SQLAlchemyError as exc:
        raise AppException(
            "Authentication service is temporarily unavailable. Check the PostgreSQL backend.",
            code="AUTH_SERVICE_UNAVAILABLE",
            status_code=503,
        ) from exc


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    _rate_limit(ip, _MAX_REFRESH_ATTEMPTS, _REFRESH_WINDOW, _login_attempts)
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


# ---------------------------------------------------------------------------
# Issue #118 — Face ID authentication (server-side biometric verification)
# ---------------------------------------------------------------------------

from pydantic import BaseModel  # noqa: E402


class FaceVerifyRequest(BaseModel):
    image_b64: str  # base64-encoded JPEG frame from the browser webcam


class FaceEnrollRequest(BaseModel):
    officer_id: str
    image_b64: str


@router.post("/face-verify", response_model=TokenResponse)
def face_verify(payload: FaceVerifyRequest, request: Request, db: Session = Depends(get_db)):
    """Issue #118: Verify a webcam frame against enrolled KSP officer biometrics.

    The matching happens entirely server-side.  The embedding is never returned
    to the client.  On success, issues the same JWT tokens as /auth/login.
    """
    ip = request.client.host if request.client else "unknown"
    _rate_limit(ip, _MAX_LOGIN_ATTEMPTS, _REFRESH_WINDOW, _login_attempts)

    from app.services.face_service import verify_face_from_b64  # noqa: PLC0415

    result = verify_face_from_b64(db, payload.image_b64)

    if not result.success:
        error_messages = {
            "NO_FACE":      "No face detected. Please position your face in the frame.",
            "MULTI_FACE":   "Multiple faces detected. Please ensure only one person is visible.",
            "NO_MATCH":     "Identity could not be verified. Your face does not match any authorized KSP officer.",
            "INACTIVE":     "This officer account is inactive. Contact your administrator.",
            "NO_ENROLLMENT": "Face ID enrollment required. No biometric records are registered.",
            "BAD_IMAGE":    "Unable to process the image. Please try again.",
        }
        msg = error_messages.get(result.error_code, "Face verification failed.")
        raise AppException(msg, code=result.error_code or "FACE_VERIFY_FAILED", status_code=401)

    # Resolve the linked User account so we can issue standard JWT tokens
    from app.models.officer import Officer  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415
    officer = db.query(Officer).filter(Officer.id == _uuid.UUID(result.officer_id)).first()
    if not officer or not officer.user:
        raise AppException(
            "Officer account is not linked to a user login. Contact your administrator.",
            code="NO_USER_ACCOUNT",
            status_code=401,
        )
    if not officer.user.is_active:
        raise AppException("Account is deactivated.", code="INACTIVE", status_code=401)

    tokens = auth_service.issue_tokens(officer.user)
    return TokenResponse(**tokens, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/face-enroll", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def face_enroll(
    payload: FaceEnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Issue #118: Enroll (or re-enroll) a face embedding for a KSP officer.

    Admin-only.  The raw image is processed server-side; only the compact
    embedding is persisted.  The image itself is discarded after processing.
    """
    from app.services.face_service import enroll_face_from_b64  # noqa: PLC0415
    from app.services import audit_service  # noqa: PLC0415

    result = enroll_face_from_b64(db, payload.officer_id, payload.image_b64)
    if not result["success"]:
        raise AppException(result["error"], code="ENROLL_FAILED", status_code=400)

    audit_service.log_action(db, current_user, "FACE_ENROLL", "Officer", payload.officer_id)
    return {"message": "Face enrolled successfully", "officer_id": result["officer_id"], "badge_number": result["badge_number"]}


@router.delete("/face-enroll/{officer_id}", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def face_unenroll(
    officer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Issue #118: Remove face enrollment for an officer (admin only)."""
    import uuid as _uuid  # noqa: PLC0415
    from app.models.officer import Officer  # noqa: PLC0415
    from app.services import audit_service  # noqa: PLC0415

    officer = db.query(Officer).filter(Officer.id == _uuid.UUID(officer_id)).first()
    if not officer:
        raise AppException("Officer not found", code="NOT_FOUND", status_code=404)
    officer.face_embedding = None
    officer.face_enabled = False
    officer.face_enrolled_at = None
    db.add(officer)
    db.commit()
    audit_service.log_action(db, current_user, "FACE_UNENROLL", "Officer", officer_id)
    return {"message": "Face enrollment removed"}
