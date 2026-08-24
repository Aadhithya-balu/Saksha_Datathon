"""Tests for intervention effectiveness loop (issue #139 M7)."""
from datetime import datetime, timezone

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.location import Location
from app.models.role import Role
from app.models.user import User

INTERVENTIONS = "/api/v2/interventions"


@pytest.fixture
def io_client(client, db_session):
    role = db_session.query(Role).filter_by(name="investigator").first()
    if role is None:
        role = Role(name="investigator", description="Investigator")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="intervention-io",
        email="intervention-io@example.com",
        full_name="Intervention IO",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def crime_series(db_session):
    """Crimes in Bengaluru Urban: 6 before the intervention, 2 after (effective)."""
    category = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="medium")
    location = Location(district="Bengaluru Urban", station="KR Puram", latitude=13.0, longitude=77.7)
    db_session.add_all([category, location])
    db_session.flush()

    cases = []
    # Six biweekly crimes before the intervention start (2026-04-01).
    from datetime import timedelta

    base = datetime(2026, 1, 7, tzinfo=timezone.utc)
    for week in range(6):
        cases.append(CrimeCase(
            case_number=f"CR-INT-PRE-{week:02d}", category_id=category.id, location_id=location.id,
            occurred_at=base + timedelta(days=14 * week), status="open",
        ))
    # Only two after — intervention appears effective.
    for index, day in enumerate((10, 28)):
        cases.append(CrimeCase(
            case_number=f"CR-INT-POST-{index:02d}", category_id=category.id, location_id=location.id,
            occurred_at=datetime(2026, 4, day, tzinfo=timezone.utc), status="open",
        ))
    db_session.add_all(cases)
    db_session.commit()


def test_create_and_list_intervention(io_client):
    c, _ = io_client
    created = c.post(f"{INTERVENTIONS}", json={
        "district": "Bengaluru Urban",
        "intervention_type": "patrol_surge",
        "title": "Night patrol surge KR Puram",
        "description": "Double patrols between 20:00-02:00 for Q2.",
        "started_at": "2026-04-01T00:00:00Z",
        "status": "completed",
    })
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["id"]
    assert body["status"] == "completed"

    listing = c.get(f"{INTERVENTIONS}?district=Bengaluru").json()
    assert listing["total"] == 1


def test_effectiveness_pre_post_comparison(io_client, crime_series):
    c, _ = io_client
    created = c.post(f"{INTERVENTIONS}", json={
        "district": "Bengaluru Urban",
        "intervention_type": "cctv_deployment",
        "title": "CCTV corridor",
        "started_at": "2026-04-01T00:00:00Z",
        "status": "active",
    }).json()

    r = c.get(f"{INTERVENTIONS}/{created['id']}/effectiveness?window_days=90")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pre_window"]["crime_count"] > body["post_window"]["crime_count"]
    assert body["change_pct"] < 0
    assert body["verdict"] in ("effective", "partially_effective")
    assert len(body["monthly_series"]) >= 3


def test_update_intervention(io_client):
    c, _ = io_client
    created = c.post(f"{INTERVENTIONS}", json={
        "district": "Hassan",
        "intervention_type": "awareness_drive",
        "title": "Cyber awareness drive",
        "started_at": "2026-05-10T00:00:00Z",
        "status": "planned",
    }).json()
    updated = c.put(f"{INTERVENTIONS}/{created['id']}", json={"status": "active"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "active"
