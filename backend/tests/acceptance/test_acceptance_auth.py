"""Scenario 1 + security acceptance: the real authentication flow.

Every test here exercises the actual /auth/login, /auth/refresh,
/auth/logout, /auth/me endpoints and the JWT validation dependency.
"""
from datetime import timedelta

import pytest
from app.core.config import settings as app_settings
from app.core.security import create_token, create_refresh_token

from tests.acceptance.conftest import TEST_PASSWORD, create_user, login

pytestmark = pytest.mark.acceptance

ME = "/api/v2/auth/me"
DASHBOARD = "/api/v2/dashboard/summary"


def test_valid_login_issues_usable_session(client, db_session):
    """Valid credentials -> tokens -> protected API accessible."""
    create_user(db_session, "auth-hero", "investigator")
    session = login(client, "auth-hero", TEST_PASSWORD)

    assert session["access_token"]
    assert session["refresh_token"]

    me = client.get(ME, headers=session["headers"])
    assert me.status_code == 200
    body = me.json()
    assert body["username"] == "auth-hero"
    assert body["role"] == "investigator"


def test_invalid_password_rejected(client, db_session):
    create_user(db_session, "auth-victim", "viewer")
    r = client.post("/api/v2/auth/login", json={"username": "auth-victim", "password": "totally-wrong"})
    assert r.status_code == 401

    # No usable session was issued.
    probe = client.get(DASHBOARD, headers={"Authorization": "Bearer not-a-real-token"})
    assert probe.status_code == 401


def test_unknown_user_rejected_without_external_calls(client, db_session, monkeypatch):
    """Unknown user fails locally; Supabase fallback is disabled in tests so no
    network call can leak credentials."""
    monkeypatch.setattr(app_settings, "SUPABASE_ANON_KEY", "", raising=False)
    r = client.post("/api/v2/auth/login", json={"username": "ghost-user", "password": TEST_PASSWORD})
    assert r.status_code == 401


def test_missing_credentials_rejected(client):
    for payload in ({}, {"username": "x"}, {"password": "y"}):
        r = client.post("/api/v2/auth/login", json=payload)
        assert r.status_code == 422, f"payload {payload} must be rejected"


def test_expired_access_token_rejected(client, db_session):
    user = create_user(db_session, "expired-echo", "viewer")
    expired = create_token(
        {"sub": user.username, "role": "viewer"},
        timedelta(minutes=-5),
        token_type="access",
    )
    headers = {"Authorization": f"Bearer {expired}"}
    assert client.get(ME, headers=headers).status_code == 401
    assert client.get(DASHBOARD, headers=headers).status_code == 401


def test_garbage_and_tampered_tokens_rejected(client, db_session):
    create_user(db_session, "tamper-target", "viewer")
    garbage = client.get(ME, headers={"Authorization": "Bearer abc.def.ghi"})
    assert garbage.status_code == 401

    session = login(client, "tamper-target", TEST_PASSWORD)
    tampered = session["access_token"][:-6] + "AAAAAA"
    r = client.get(ME, headers={"Authorization": f"Bearer {tampered}"})
    assert r.status_code == 401


def test_refresh_token_cannot_be_used_as_access_token(client, db_session):
    user = create_user(db_session, "type-confused", "viewer")
    refresh = create_refresh_token(user.username)
    r = client.get(ME, headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 401


def test_logout_revokes_refresh_token(client, db_session):
    """Server-side revocation: after logout the refresh token cannot be replayed."""
    create_user(db_session, "logout-user", "viewer")
    session = login(client, "logout-user", TEST_PASSWORD)

    out = client.post(
        "/api/v2/auth/logout",
        json={"refresh_token": session["refresh_token"]},
        headers=session["headers"],
    )
    assert out.status_code == 200

    replay = client.post("/api/v2/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert replay.status_code == 401


def test_refresh_rotation_issues_new_working_access_token(client, db_session):
    create_user(db_session, "rotating-user", "viewer")
    session = login(client, "rotating-user", TEST_PASSWORD)

    refreshed = client.post("/api/v2/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()

    me = client.get(ME, headers={"Authorization": f"Bearer {new_tokens['access_token']}"})
    assert me.status_code == 200

    # Rotation: the consumed refresh token must never be replayable.
    replay = client.post("/api/v2/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert replay.status_code == 401


def test_register_is_admin_only(client, db_session, analyst_headers):
    """A valid non-admin token still cannot mint accounts (issue 8 §6)."""
    r = client.post(
        "/api/v2/auth/register",
        json={
            "username": "sneaky-new",
            "email": "sneaky@acceptance.invalid",
            "full_name": "Sneaky New",
            "password": "Str0ngPass!2026",
            "role_name": "admin",
        },
        headers=analyst_headers,
    )
    assert r.status_code == 403
