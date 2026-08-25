"""Round-2 security hardening tests.

Covers: token validation (malformed/tampered/expired/wrong-type), refresh
rotation + revocation, logout revocation, account lockout, password policy,
security headers, rate limiting middleware, and upload content sniffing.
"""
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt as jose_jwt

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.role import Role
from app.models.user import User

TEST_PASSWORD = "Password123!"


def _seed_user(db_session, username="secuser", role_name="investigator", password=TEST_PASSWORD):
    from app.core.security import hash_password

    role = db_session.query(Role).filter(Role.name == role_name).first()
    if not role:
        role = Role(name=role_name, description=role_name)
        db_session.add(role)
        db_session.flush()
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name="Security Test",
        hashed_password=hash_password(password),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _login(client, username="secuser", password=TEST_PASSWORD):
    return client.post("/api/v2/auth/login", json={"username": username, "password": password})


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

def test_malformed_token_rejected(client):
    r = client.get("/api/v2/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_tampered_token_rejected(client, db_session):
    _seed_user(db_session)
    body = _login(client).json()
    token = body["access_token"]
    tampered = token[:-6] + ("aaaaaa" if token[-6:] != "aaaaaa" else "bbbbbb")
    r = client.get("/api/v2/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert r.status_code == 401


def test_expired_token_rejected(client):
    expired = jose_jwt.encode(
        {
            "sub": "secuser",
            "role": "investigator",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "iss": "saksha-backend",
            "aud": "saksha-clients",
            "jti": "expired-jti",
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    r = client.get("/api/v2/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_token_with_wrong_audience_rejected(client):
    bad = jose_jwt.encode(
        {
            "sub": "secuser",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "iss": "saksha-backend",
            "aud": "wrong-audience",
            "jti": "bad-aud-jti",
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    r = client.get("/api/v2/auth/me", headers={"Authorization": f"Bearer {bad}"})
    assert r.status_code == 401


def test_refresh_token_cannot_access_protected_routes(client, db_session):
    _seed_user(db_session)
    refresh = _login(client).json()["refresh_token"]
    r = client.get("/api/v2/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Refresh rotation + revocation
# ---------------------------------------------------------------------------

def test_refresh_rotation_invalidates_previous_token(client, db_session):
    _seed_user(db_session)
    tokens = _login(client).json()
    first = client.post("/api/v2/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200

    # Replay of the already-rotated refresh token must be rejected.
    replay = client.post("/api/v2/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401


def test_logout_revokes_refresh_token(client, db_session):
    _seed_user(db_session)
    tokens = _login(client).json()
    access = tokens["access_token"]

    r = client.post(
        "/api/v2/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 200

    replay = client.post("/api/v2/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401


# ---------------------------------------------------------------------------
# Account lockout (brute-force protection)
# ---------------------------------------------------------------------------

def test_account_locks_after_repeated_failures(client, db_session):
    _seed_user(db_session)
    for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS):
        r = _login(client, password="wrong-password")
        assert r.status_code in (401, 429)

    # Even the CORRECT password is now rejected while locked.
    r = _login(client)
    assert r.status_code == 403
    assert "locked" in r.json()["error"]["message"].lower()


def test_failed_counter_resets_on_success(client, db_session):
    _seed_user(db_session)
    for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS - 1):
        _login(client, password="wrong-password")
    r = _login(client)
    assert r.status_code == 200
    user = db_session.query(User).filter(User.username == "secuser").first()
    assert (user.failed_login_attempts or 0) == 0


# ---------------------------------------------------------------------------
# Password policy
# ---------------------------------------------------------------------------

def test_weak_password_rejected_on_register(client, db_session):
    _seed_user(db_session, username="secadmin", role_name="admin")
    if not db_session.query(Role).filter(Role.name == "viewer").first():
        db_session.add(Role(name="viewer", description="Read-only"))
        db_session.commit()
    login = _login(client, username="secadmin")
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    for weak in ("Sh0rt", "alllowercase1", "ALLUPPERCASE1", "NoDigitsHere!"):
        r = client.post("/api/v2/auth/register", headers=admin_headers, json={
            "username": "newbie", "email": "newbie@example.com",
            "full_name": "New User", "password": weak, "role_name": "viewer",
        })
        assert r.status_code in (400, 409, 422), f"weak password accepted: {weak}"

    strong = client.post("/api/v2/auth/register", headers=admin_headers, json={
        "username": "newbie", "email": "newbie@example.com",
        "full_name": "New User", "password": "Str0ngPassw0rd", "role_name": "viewer",
    })
    assert strong.status_code in (200, 201)


def test_change_password_enforces_policy(client, db_session):
    _seed_user(db_session)
    access = _login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {access}"}
    r = client.put("/api/v2/auth/change-password", headers=headers, json={
        "old_password": TEST_PASSWORD, "new_password": "short",
    })
    assert r.status_code in (400, 409, 422)


# ---------------------------------------------------------------------------
# Security headers / middleware behavior
# ---------------------------------------------------------------------------

def test_security_headers_present_on_api_responses(client):
    r = client.get("/health/live")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in r.headers
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]


def test_public_upload_mount_removed(client):
    # Evidence files must never be served unauthenticated via a static mount.
    r = client.get("/uploads/some-file.png")
    assert r.status_code in (401, 404)


def test_health_liveness_has_no_infrastructure_detail(client):
    r = client.get("/health/live")
    assert r.status_code == 200
    assert set(r.json().keys()) <= {"status"}


def test_oversized_json_body_rejected(client):
    big = "x" * (settings.MAX_REQUEST_BODY_BYTES + 1024)
    r = client.post(
        "/api/v2/auth/login",
        content=big,
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 413


# ---------------------------------------------------------------------------
# Rate limiting middleware
# ---------------------------------------------------------------------------

def test_rate_limit_returns_429(monkeypatch, client):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "RATE_LIMIT_MAX_REQUESTS", 3)

    statuses = [client.get("/api/v2/dashboard/summary").status_code for _ in range(5)]
    # The endpoint itself may 401 without auth, but the limiter must kick in.
    assert statuses.count(429) >= 1
    monkeypatch.setattr(settings, "APP_ENV", "test")


# ---------------------------------------------------------------------------
# Upload content sniffing (service level)
# ---------------------------------------------------------------------------

def test_sniff_detects_mime_spoofing():
    from fastapi import UploadFile

    from app.services.evidence_service import validate_upload_file

    class FakeFile:
        def __init__(self, filename, content_type):
            self.filename = filename
            self.content_type = content_type

    # Declared PNG but .txt extension mismatch is caught by extension allow-list.
    with pytest.raises(Exception):
        validate_upload_file(FakeFile("evil.exe", "application/pdf"))
    with pytest.raises(Exception):
        validate_upload_file(FakeFile("traversal/../name.png", "image/png"))
    with pytest.raises(Exception):
        validate_upload_file(FakeFile("script.svg", "image/svg+xml"))  # SVG never allowed
    with pytest.raises(Exception):
        validate_upload_file(FakeFile("noext", "text/plain"))


def test_magic_byte_detection():
    from app.services.evidence_service import sniff_content_type

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 32
    pdf = b"%PDF-1.7 ..." + b"\x00" * 32
    html_as_text_ok = b"<html>hello</html>"  # text/plain allows markup text? no: NUL check only
    assert sniff_content_type(png) == "image/png"
    assert sniff_content_type(jpeg) == "image/jpeg"
    assert sniff_content_type(pdf) == "application/pdf"
    assert sniff_content_type(html_as_text_ok) is None


def test_text_upload_with_binary_payload_rejected(tmp_path, monkeypatch):
    """A file declared as .txt but containing binary garbage must be rejected."""
    from fastapi import HTTPException
    from fastapi import UploadFile
    from io import BytesIO

    from app.services import evidence_service
    from starlette.datastructures import Headers

    payload = b"PK\x03\x04\x00\x00binary-zip-content\x00\x00"
    upload = UploadFile(
        file=BytesIO(payload),
        size=len(payload),
        filename="notes.txt",
        headers=Headers({"content-type": "text/plain"}),
    )
    evidence_service.UPLOAD_DIR = tmp_path
    import uuid as _uuid

    with pytest.raises(HTTPException) as exc_info:
        evidence_service.save_upload_file(upload, _uuid.uuid4())
    assert exc_info.value.status_code == 400
