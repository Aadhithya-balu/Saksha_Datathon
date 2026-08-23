"""Regression tests for /api/v2/reports endpoints (mapper must return dicts)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.evidence import Evidence
from app.models.location import Location
from app.models.officer import Officer
from app.models.role import Role
from app.models.user import User

REPORTS = "/api/v2/reports"


@pytest.fixture
def analyst_client(client, db_session):
    role = db_session.query(Role).filter_by(name="crime_analyst").first()
    if role is None:
        role = Role(name="crime_analyst", description="Crime Analyst")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="reports-analyst",
        email="reports-analyst@example.com",
        full_name="Reports Analyst",
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
def seeded_records(db_session):
    """One record per reportable type so mappers are actually exercised."""
    category = CrimeCategory(name="Theft", section_code="IPC 379", severity="medium")
    location = Location(
        district="Bengaluru Urban",
        station="Whitefield",
        latitude=12.9716,
        longitude=77.5946,
    )
    officer = Officer(badge_number="IO-TEST-1", name="Test Officer", rank="Inspector", station="Whitefield")
    criminal = Criminal(full_name="Test Crook", status="wanted")
    db_session.add_all([category, location, officer, criminal])
    db_session.flush()

    case = CrimeCase(
        case_number="CR-TEST-0001",
        category_id=category.id,
        location_id=location.id,
        occurred_at=datetime.now(timezone.utc) - timedelta(days=1),
        status="open",
        priority="high",
        progress=25,
    )
    db_session.add(case)
    db_session.flush()
    evidence = Evidence(
        title="Seized laptop",
        evidence_type="digital",
        status="collected",
        case_id=case.id,
        created_by="reports-analyst",
    )
    db_session.add(evidence)
    db_session.commit()
    return {"case": case}


@pytest.mark.parametrize("report_type", ["cases", "officers", "criminals", "evidence"])
def test_preview_report_rows_are_dicts(analyst_client, seeded_records, report_type):
    c, _ = analyst_client
    r = c.get(f"{REPORTS}/{report_type}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1, f"seed data missing for {report_type}"
    assert isinstance(body["headers"], list) and body["headers"]
    for row in body["results"]:
        assert isinstance(row, dict), (
            f"report mapper returned {type(row).__name__} instead of dict - "
            "row data is lost and exports/preview will crash"
        )
        assert set(row.keys()) == set(body["headers"])


@pytest.mark.parametrize("export_format", ["csv", "pdf", "txt"])
def test_export_report_with_data(analyst_client, seeded_records, export_format):
    c, _ = analyst_client
    r = c.get(f"{REPORTS}/cases/export/{export_format}")
    assert r.status_code == 200, r.text
    assert len(r.content) > 100


def test_statistics_summary(analyst_client, seeded_records):
    c, _ = analyst_client
    r = c.get(f"{REPORTS}/statistics/summary")
    assert r.status_code == 200, r.text

