"""
Supabase Auth integration — fallback authentication when a user is not found
in the local demo-users table.

Uses the Supabase Auth REST API (go_true) to verify credentials, then looks
up the user profile in the local PostgreSQL users table.

Dependency: httpx (already in requirements.txt)
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.models.user import User

SUPABASE_AUTH_TIMEOUT = 3  # seconds — reduced from 10 to avoid blocking the event loop


@dataclass
class SupabaseAuthResult:
    """Result from a successful Supabase Auth sign-in."""
    email: str
    user_id: str


def verify_with_supabase(username: str, password: str) -> SupabaseAuthResult | None:
    """
    Attempt to authenticate against the Supabase Auth REST API.

    Returns None if Supabase Auth is not configured (missing anon key) or
    if the credentials are rejected.

    Uses the go_true token endpoint:
      POST {SUPABASE_URL}/auth/v1/token?grant_type=password
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        return None

    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/token"
    # The username field could be an email address for Supabase users
    params = {"grant_type": "password"}
    payload = {"email": username, "password": password}

    try:
        with httpx.Client(timeout=SUPABASE_AUTH_TIMEOUT) as client:
            resp = client.post(
                url,
                params=params,
                json=payload,
                headers={
                    "apikey": settings.SUPABASE_ANON_KEY,
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return SupabaseAuthResult(
                email=data.get("user", {}).get("email", username),
                user_id=data.get("user", {}).get("id", ""),
            )
    except httpx.RequestError:
        # Supabase is unreachable — silently return None so the caller
        # can decide how to handle it (we re-raise the original error).
        return None


def find_user_by_email(db: Session, email: str) -> User | None:
    """Look up a local user record by email address."""
    return db.query(User).filter(User.email == email).first()


def supabase_authenticate(db: Session, username: str, password: str) -> User:
    """
    Fallback authentication path:
      1. Verify credentials with Supabase Auth REST API.
      2. Look up the user in the local `users` table by email.
      3. Return the User ORM object so existing issue_tokens() can be reused.

    Raises UnauthorizedException on failure.
    """
    result = verify_with_supabase(username, password)
    if result is None:
        raise UnauthorizedException("Incorrect username or password")

    user = find_user_by_email(db, result.email)
    if user is None:
        raise UnauthorizedException(
            "Supabase authentication succeeded but no local user profile was found. "
            "Contact an administrator to create your account."
        )
    if not user.is_active:
        raise UnauthorizedException("Account is deactivated")
    return user
