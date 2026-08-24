"""Tests for victimology analytics (issue #139 M5)."""
import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.fir import FIR, FIRVictimLink
from app.models.location import Location
from app.models.role import Role
from app.models.user import User
from app.models.victim import Victim
from datetime import datetime, timezone

VICTIMOLOGY = "/api/v2/victimology"


@pytest.fixture
def analyst_client(client, db_session):
    role = db_session.query(Role).filter_by(name="crime_analyst").first()
    if role is None:
        role = Role(name="crime_analyst", description="Crime Analyst")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="victimology-analyst",
        email="victimology-analyst@example.com",
        full_name="Victimology Analyst",
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
def repeat_victim_data(db_session):
    """One repeat victim (2 FIRs incl. heinous section) + one single-incident adult."""
    category = CrimeCategory(name="Assault", section_code="IPC 351", severity="high")
    location = Location(district="Bengaluru Urban", station="KR Puram", latitude=13.0, longitude=77.7)
    repeat_victim = Victim(full_name="Repeat Ravi", gender="Male", age=70, address="Bengaluru")
    other_victim = Victim(full_name="Single Sunita", gender="Female", age=28, address="Hassan")
    db_session.add_all([category, location, repeat_victim, other_victim])
    db_session.flush()

    case_one = CrimeCase(
        case_number="CR-VIC-0001", category_id=category.id, location_id=location.id,
        occurred_at=datetime(2026, 1, 10, tzinfo=timezone.utc), status="open",
    )
    case_two = CrimeCase(
        case_number="CR-VIC-0002", category_id=category.id, location_id=location.id,
        occurred_at=datetime(2026, 3, 15, tzinfo=timezone.utc), status="open",
    )
    case_three = CrimeCase(
        case_number="CR-VIC-0003", category_id=category.id, location_id=location.id,
        occurred_at=datetime(2026, 4, 2, tzinfo=timezone.utc), status="closed",
    )
    db_session.add_all([case_one, case_two, case_three])
    db_session.flush()

    fir_one = FIR(fir_number="FIR-VIC-0001", crime_case_id=case_one.id,
                  complainant_name="Repeat Ravi", sections="307", filed_at=datetime(2026, 1, 11, tzinfo=timezone.utc))
    fir_two = FIR(fir_number="FIR-VIC-0002", crime_case_id=case_two.id,
                  complainant_name="Repeat Ravi", sections="323", filed_at=datetime(2026, 3, 16, tzinfo=timezone.utc))
    fir_three = FIR(fir_number="FIR-VIC-0003", crime_case_id=case_three.id,
                    complainant_name="Single Sunita", sections="323", filed_at=datetime(2026, 4, 3, tzinfo=timezone.utc))
    db_session.add_all([fir_one, fir_two, fir_three])
    db_session.flush()

    db_session.add_all([
        FIRVictimLink(fir_id=fir_one.id, victim_id=repeat_victim.id),
        FIRVictimLink(fir_id=fir_two.id, victim_id=repeat_victim.id),
        FIRVictimLink(fir_id=fir_three.id, victim_id=other_victim.id),
    ])
    db_session.commit()
    return {"repeat": repeat_victim, "other": other_victim}


def test_overview_flags_repeat_victimization(analyst_client, repeat_victim_data):
    c, _ = analyst_client
    r = c.get(f"{VICTIMOLOGY}/overview")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_victims"] == 2
    assert body["repeat_victims"] == 1
    assert body["repeat_victimization_rate"] == 50.0
    assert body["age_band_distribution"]["elderly_60p"] == 1
    assert len(body["criminological_frame"]) >= 2


def test_repeat_victims_endpoint(analyst_client, repeat_victim_data):
    c, _ = analyst_client
    r = c.get(f"{VICTIMOLOGY}/repeat-victims")
    body = r.json()
    assert body["repeat_victims"] == 1
    flagged = body["results"][0]
    assert flagged["full_name"] == "Repeat Ravi"
    assert flagged["fir_count"] == 2
    factors = [f["factor"] for f in flagged["vulnerability"]["factors"]]
    assert "repeat_victimization" in factors


def test_vulnerability_index_ranking(analyst_client, repeat_victim_data):
    c, _ = analyst_client
    r = c.get(f"{VICTIMOLOGY}/vulnerability-index")
    body = r.json()
    ranked = body["results"]
    assert len(ranked) == 2
    # Elderly + repeat + heinous-section + open cases must outrank the single adult.
    assert ranked[0]["full_name"] == "Repeat Ravi"
    assert ranked[0]["vulnerability_score"] > ranked[1]["vulnerability_score"]
    assert ranked[0]["vulnerability_band"] in ("critical", "high")
    assert "methodology" in body
