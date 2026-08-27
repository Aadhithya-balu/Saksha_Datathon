"""Business logic for authentication: login, token refresh, password change.

Round-2 security hardening:
- Account lockout after repeated failed logins (brute-force protection).
- Transparent password-hash migration from legacy SHA-256 to Argon2id on
  successful login.
- Refresh-token rotation with a server-side revocation list (jti denylist):
  every refresh invalidates the previous refresh token, and logout revokes
  outstanding tokens until their natural expiry.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.password_hashing import hash_password, needs_rehash, verify_password
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.revoked_token import RevokedToken
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserCreate


# ---------------------------------------------------------------------------
# Password policy
# ---------------------------------------------------------------------------

def is_numeric_pin(password: str) -> bool:
    """True when the value is a 6-digit numeric badge PIN (e.g. '564738')."""
    return len(password) == 6 and password.isdigit()


def validate_password_strength(password: str) -> None:
    """KSP accounts protect sensitive records; enforce a baseline policy.

    Accepts either a strong password (>= 8 chars with lower/upper/digit) or a
    6-digit numeric badge PIN, matching the platform's badge-ID login flow.

    Raises ConflictException with an actionable message when violated. Kept in
    the service layer so admin routes and self-service changes share one rule.
    """
    if is_numeric_pin(password):
        return
    if len(password) < 8 or len(password) > 128:
        raise ConflictException("Password must be between 8 and 128 characters")
    if not any(c.islower() for c in password):
        raise ConflictException("Password must contain a lowercase letter")
    if not any(c.isupper() for c in password):
        raise ConflictException("Password must contain an uppercase letter")
    if not any(c.isdigit() for c in password):
        raise ConflictException("Password must contain a digit")


# ---------------------------------------------------------------------------
# Brute-force protection
# ---------------------------------------------------------------------------

def _is_locked(user: User) -> bool:
    if not user.locked_until:
        return False
    locked_until = user.locked_until
    # SQLite returns naive datetimes; normalize to UTC-aware for comparison.
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < locked_until


def _register_failed_login(db: Session, user: User) -> None:
    """Increment the failure counter and lock the account past the threshold."""
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
        user.failed_login_attempts = 0  # counter resets once lock engages
    db.add(user)


def _clear_failed_logins(db: Session, user: User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def authenticate_user(db: Session, username: str, password: str) -> User:
    """
    Authenticate a user by checking:
      1. Local auth (username or officer badge number + hashed password).
      2. Fallback to Supabase Auth REST API if local user not found.

    Raises UnauthorizedException on all failure paths (generic message so we
    never reveal whether an account exists).
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        from app.models.officer import Officer
        officer = db.query(Officer).filter(Officer.badge_number == username).first()
        if officer and officer.user:
            user = officer.user

    if user:
        # Account lockout check happens before password verification so a
        # locked account is rejected even with correct credentials.
        if _is_locked(user):
            raise ForbiddenException(
                f"Account temporarily locked due to repeated failed logins. "
                f"Try again in {settings.LOGIN_LOCKOUT_MINUTES} minutes."
            )
        if not verify_password(password, user.hashed_password):
            _register_failed_login(db, user)
            db.commit()
            raise UnauthorizedException("Incorrect username or password")
        if not user.is_active:
            raise UnauthorizedException("Account is deactivated")

        # Successful login: reset counters and migrate legacy hashes.
        changed = False
        if user.failed_login_attempts or user.locked_until:
            _clear_failed_logins(db, user)
            changed = True
        if needs_rehash(user.hashed_password):
            user.hashed_password = hash_password(password)  # upgrade SHA-256 → Argon2id
            changed = True
        if changed:
            db.add(user)
            db.commit()
        return user

    # Local user not found — try Supabase Auth fallback
    from app.services.supabase_auth import supabase_authenticate
    return supabase_authenticate(db, username, password)


def issue_tokens(user: User) -> dict:
    access_token = create_access_token(subject=user.username, role=user.role.name)
    refresh_token = create_refresh_token(subject=user.username)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


def _revoke_jti(db: Session, jti: str | None, expires_at) -> None:
    if not jti:
        return
    expiry = None
    if isinstance(expires_at, (int, float)):
        expiry = datetime.fromtimestamp(expires_at, tz=timezone.utc)
    elif isinstance(expires_at, datetime):
        expiry = expires_at
    if expiry is None or expiry < datetime.now(timezone.utc):
        expiry = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    existing = db.get(RevokedToken, jti)
    if not existing:
        db.add(RevokedToken(jti=jti, expires_at=expiry))


def is_jti_revoked(db: Session, jti: str | None) -> bool:
    if not jti:
        return False
    return db.get(RevokedToken, jti) is not None


def prune_revoked_tokens(db: Session) -> None:
    """Delete denylist rows whose tokens have already expired."""
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < datetime.now(timezone.utc)))


def refresh_access_token(db: Session, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise UnauthorizedException("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Provided token is not a refresh token")

    # Rotation: a consumed refresh token must never be replayed.
    if is_jti_revoked(db, payload.get("jti")):
        raise UnauthorizedException("Refresh token has been revoked")

    user = db.query(User).filter(User.username == payload.get("sub")).first()
    if not user or not user.is_active:
        raise UnauthorizedException("User not found or inactive")

    # Revoke the presented refresh token before issuing its replacement.
    _revoke_jti(db, payload.get("jti"), payload.get("exp"))
    prune_revoked_tokens(db)
    db.commit()

    return issue_tokens(user)


def revoke_token(db: Session, token: str | None) -> None:
    """Denylist one valid JWT until its natural expiry.

    This is used for both the current access token and an optional refresh
    token at logout, so a stolen bearer token cannot continue to call APIs
    after the account holder signs out.
    """
    if token:
        try:
            payload = decode_token(token)
            _revoke_jti(db, payload.get("jti"), payload.get("exp"))
            db.commit()
        except ValueError:
            pass  # already-expired/malformed tokens need no revocation


def revoke_all_user_tokens(db: Session, refresh_token: str | None = None) -> None:
    """Backward-compatible logout helper for callers with a refresh token."""
    revoke_token(db, refresh_token)


def register_user(db: Session, payload: UserCreate) -> User:
    validate_password_strength(payload.password)
    if db.query(User).filter(User.username == payload.username).first():
        raise ConflictException("Username already exists")
    if db.query(User).filter(User.email == payload.email).first():
        raise ConflictException("Email already registered")

    role = db.query(Role).filter(Role.name == payload.role_name).first()
    if not role:
        raise ConflictException(f"Role '{payload.role_name}' does not exist")

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        district=payload.district,
        station=payload.station,
        role_id=role.id,
    )
    db.add(user)
    db.flush()
    return user


def change_password(db: Session, user: User, old_password: str, new_password: str) -> None:
    validate_password_strength(new_password)
    if not verify_password(old_password, user.hashed_password):
        raise UnauthorizedException("Old password is incorrect")
    user.hashed_password = hash_password(new_password)
    db.add(user)
