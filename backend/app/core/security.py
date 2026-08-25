"""
Password hashing and JWT token creation / verification utilities.

Security hardening (Round 2):
- Passwords use Argon2id (see app.core.password_hashing). Legacy SHA-256
  hashes remain verifiable for backward compatibility and are upgraded on
  next successful login.
- JWTs carry ``iss`` / ``aud`` claims that are validated on every decode,
  include a per-token ``jti`` for revocation support, and are decoded with an
  explicit algorithm allow-list (prevents algorithm-confusion attacks).
- Token type (access vs refresh) is enforced by callers via the ``type`` claim.
"""
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt

from app.core.config import settings
from app.core.password_hashing import (  # noqa: F401 — re-exported for callers
    hash_password,
    is_legacy_hash,
    needs_rehash,
    verify_password,
)

JWT_ISSUER = "saksha-backend"
JWT_AUDIENCE = "saksha-clients"


def create_token(data: dict, expires_delta: timedelta, token_type: str = "access") -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "type": token_type,
            # Unique token id — used by the revocation list on logout/rotation.
            "jti": str(_uuid.uuid4()),
        }
    )
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
    """
    Decode and validate a JWT.

    Rejects: malformed tokens, tampered signatures, expired tokens, tokens
    signed with an unexpected algorithm, and tokens missing/wrong issuer or
    audience. Raises ValueError with a generic message only (no internals).
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],  # explicit allow-list
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require": ["exp", "sub", "type"]},
        )
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
