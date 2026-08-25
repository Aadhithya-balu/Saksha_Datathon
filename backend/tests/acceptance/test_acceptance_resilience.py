"""Scenario 9 acceptance: database failure handling + performance sanity.

DB failure is simulated with a REAL broken database session (an in-memory
SQLite engine whose schema was never created), not by mocking the service
layer — so actual exception propagation through the app is verified.
"""
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

pytestmark = pytest.mark.acceptance


@pytest.fixture
def broken_db_client(db_session):
    """TestClient wired to a real DB session whose tables do not exist."""
    from fastapi.testclient import TestClient

    from app.database.postgres import get_db, Base
    from app.main import app

    # Create schema then drop it: a live connection to a DB with no tables.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Base.metadata.drop_all(bind=engine)
    BrokenSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = BrokenSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def test_login_failure_is_controlled_503(broken_db_client):
    """DB down -> auth service reports a controlled 503, never leaks internals."""
    r = broken_db_client.post(
        "/api/v2/auth/login",
        json={"username": "whoever", "password": "whatever"},
    )
    assert r.status_code == 503
    text = r.text.lower()
    assert "traceback" not in text
    assert "sqlite" not in text
    assert "password" not in text


def test_dashboard_failure_is_controlled_error(broken_db_client):
    r = broken_db_client.get("/api/v2/dashboard/summary")
    # Either auth fails first (401) or the query failure is handled (5xx);
    # either way it must be a controlled JSON error.
    assert r.status_code >= 400
    assert "Traceback" not in r.text


def test_network_failure_is_controlled_error(broken_db_client):
    r = broken_db_client.get("/api/v2/network/graph")
    assert r.status_code >= 400
    body = r.json()
    # Controlled error schema — either the auth layer or the unhandled
    # exception handler answered; never a raw traceback.
    assert "error" in body and {"code", "message", "status"} <= set(body["error"])
    assert "Traceback" not in r.text


# ---------------------------------------------------------------------------
# Performance sanity (issue 8 §23): catastrophic-regression guard only.
# ---------------------------------------------------------------------------

SLOW_TEST_SECONDS = 30.0


def _timed(fn):
    start = time.perf_counter()
    response = fn()
    elapsed = time.perf_counter() - start
    return response, elapsed


def test_login_and_dashboard_complete_within_threshold(client, db_session):
    from tests.acceptance.conftest import TEST_PASSWORD, create_user, login

    create_user(db_session, "perf-user", "crime_analyst")

    _, login_elapsed = _timed(lambda: login(client, "perf-user", TEST_PASSWORD))
    assert login_elapsed < SLOW_TEST_SECONDS, f"login took {login_elapsed:.1f}s"

    headers = login(client, "perf-user", TEST_PASSWORD)["headers"]
    dash, dash_elapsed = _timed(lambda: client.get("/api/v2/dashboard/summary", headers=headers))
    assert dash.status_code == 200
    assert dash_elapsed < SLOW_TEST_SECONDS, f"dashboard took {dash_elapsed:.1f}s"


def test_intel_endpoints_complete_within_threshold(client, crime_dataset, analyst_headers):
    checks = [
        ("network", lambda: client.get("/api/v2/network/graph", headers=analyst_headers)),
        ("hotspot", lambda: client.post(
            "/api/v2/ai/hotspot/predict",
            json={"records": [{
                "CaseMasterID": "PERF-1", "IncidentFromDate": "2026-06-10T22:30:00",
                "latitude": 12.96, "longitude": 77.72, "PoliceStationID": "PS-1",
                "GravityOffenceID": 1, "CrimeMajorHeadID": "THEFT",
            }]},
            headers=analyst_headers,
        )),
        ("prediction", lambda: client.get("/api/v2/ai/predictions/risk-scores", headers=analyst_headers)),
    ]
    for name, call in checks:
        response, elapsed = _timed(call)
        assert response.status_code == 200, f"{name} failed: {response.status_code}"
        assert elapsed < SLOW_TEST_SECONDS, f"{name} took {elapsed:.1f}s"
