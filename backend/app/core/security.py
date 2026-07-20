"""
Password hashing and JWT token creation / verification utilities.

Uses SHA-256 (via Python's built-in hashlib) for password hashing —
no external C dependencies, no 72-byte truncation limit (bcrypt issue).
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256 with a random salt.
    Returns a string in the format: sha256$<salt>$<hex_digest>
    """
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"sha256${salt}${digest}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored hash (format: sha256$<salt>$<hex_digest>).
    """
    try:
        _, salt, stored_digest = hashed_password.split("$", 2)
    except ValueError:
        return False
    computed_digest = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
    return computed_digest == stored_digest


def create_token(data: dict, expires_delta: timedelta, token_type: str = "access") -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, role: str, extra: Optional[dict] = None) -> str:
    payload = {"sub": subject, "role": role}
    if extra:
        payload.update(extra)
    return create_token(
        payload,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(subject: str) -> str:
    return create_token(
        {"sub": subject},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
