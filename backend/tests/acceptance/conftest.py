"""Shared fixtures for the end-to-end acceptance suite (issue 8).

Design rules:
- Tests run against the REAL FastAPI app with a real (in-memory SQLite)
  database. Only the DB session is injected; authentication always goes
  through the actual /auth/login endpoint and JWT validation path.
- The dataset is deterministic: fixed names, dates, districts, counts.
- No production credentials, no external services.
"""
from datetime import datetime, timezone

import pytest

from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.location import Location
from app.models.officer import Officer
from app.models.role import Role
from app.models.user import User
from app.models.victim import Victim

TEST_PASSWORD = "Acceptance#2026"


def get_or_create_role(db_session, name: str) -> Role:
    role = db_session.query(Role).filter_by(name=name).first()
    if role is None:
        role = Role(name=name, description=f"{name} acceptance role")
        db_session.add(role)
        db_session.flush()
    return role


def create_user(db_session, username: str, role_name: str) -> User:
    user = User(
        username=username,
        email=f"{username}@acceptance.invalid",
        full_name=username.replace("-", " ").title(),
        hashed_password=hash_password(TEST_PASSWORD),
        role_id=get_or_create_role(db_session, role_name).id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


def login(client, username: str, password: str):
    """Authenticate through the real login endpoint."""
    response = client.post(
        "/api/v2/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, f"login failed for {username}: {response.text}"
    body = response.json()
    return {
        "access_token": body["access_token"],
        "refresh_token": body["refresh_token"],
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
    }


def auth_headers(client, db_session, username: str, role_name: str) -> dict:
    """Create a user and return live Authorization headers from a real login."""
    create_user(db_session, username, role_name)
    session = login(client, username, TEST_PASSWORD)
    return session["headers"]


@pytest.fixture
def analyst_headers(client, db_session):
    return auth_headers(client, db_session, "acc-analyst", "crime_analyst")


@pytest.fixture
def admin_headers(client, db_session):
    return auth_headers(client, db_session, "acc-admin", "admin")


@pytest.fixture
def viewer_headers(client, db_session):
    return auth_headers(client, db_session, "acc-viewer", "viewer")


@pytest.fixture
def investigator_headers(client, db_session):
    return auth_headers(client, db_session, "acc-io", "investigator")


def seed_crime_dataset(db_session) -> dict:
    """Deterministic mini-world used by dashboard/network/hotspot/prediction flows.

    Contents:
      - 2 categories, 2 districts (Bengaluru Urban, Mysuru)
      - 3 criminals (2 in one gang), 1 victim, 1 officer
      - 3 cases (2 Bengaluru + 1 Mysuru; one DEMO-provenance record)
      - 2 FIRs linking criminals + victim to cases
    """
    cat_theft = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="high")
    cat_assault = CrimeCategory(name="Assault", section_code="IPC 354", severity="medium")
    loc_blr = Location(district="Bengaluru Urban", station="Whitefield", latitude=12.96, longitude=77.72)
    loc_mys = Location(district="Mysuru", station="Devaraja", latitude=12.30, longitude=76.65)
    db_session.add_all([cat_theft, cat_assault, loc_blr, loc_mys])
    db_session.flush()

    crook_a = Criminal(
        full_name="Accused Alpha", status="at_large", gang_affiliation="Acc-Gang",
        mo_summary="Breaks into homes at night using an iron rod.",
    )
    crook_b = Criminal(
        full_name="Accused Beta", status="arrested", gang_affiliation="Acc-Gang",
        mo_summary="Drives getaway vehicle KA-05-AC-1111 during burglaries.",
    )
    crook_c = Criminal(full_name="Lone Offender Gamma", status="at_large")
    victim_one = Victim(
        full_name="Victim Vega", gender="F", age=34,
        address="12 Acceptance Street, Bengaluru Urban", contact_number="9000000001",
    )
    officer_one = Officer(
        badge_number="ACC-IO-1", name="Inspector Acceptance", rank="Inspector",
        station="Whitefield", district="Bengaluru Urban", status="active",
    )
    db_session.add_all([crook_a, crook_b, crook_c, victim_one, officer_one])
    db_session.flush()

    case_blr_1 = CrimeCase(
        case_number="CR-ACC-0001", category_id=cat_theft.id, location_id=loc_blr.id,
        occurred_at=datetime(2026, 6, 10, 22, 30, tzinfo=timezone.utc),
        description="Night house break-in; ornaments stolen.", mo_tags="night_break_in",
        status="open", priority="high",
    )
    case_blr_2 = CrimeCase(
        case_number="CR-ACC-0002", category_id=cat_assault.id, location_id=loc_blr.id,
        occurred_at=datetime(2026, 7, 2, 15, 0, tzinfo=timezone.utc),
        description="Assault near market.", status="closed", priority="medium",
    )
    # DEMO-provenance record: migrated from a legacy/demo dataset.
    case_demo = CrimeCase(
        case_number="CR-ACC-DEMO-0003", category_id=cat_theft.id, location_id=loc_mys.id,
        occurred_at=datetime(2026, 5, 18, 21, 0, tzinfo=timezone.utc),
        description="Demo-seeded chain snatching in Mysuru.", status="open",
        dataset_provenance="demo",
    )
    db_session.add_all([case_blr_1, case_blr_2, case_demo])
    db_session.flush()

    fir_one = FIR(
        fir_number="FIR-ACC-0001", crime_case_id=case_blr_1.id,
        investigating_officer_id=officer_one.id,
        complainant_name="Victim Vega", sections="379, 457",
        narrative="Two men arrived on KA-05-AC-1111; one carried an iron rod.",
        filed_at=datetime(2026, 6, 11, 23, 30, tzinfo=timezone.utc),
    )
    fir_two = FIR(
        fir_number="FIR-ACC-0002", crime_case_id=case_demo.id,
        complainant_name="Mysuru Shopkeeper", sections="379",
        filed_at=datetime(2026, 5, 19, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([fir_one, fir_two])
    db_session.flush()

    db_session.add_all([
        FIRCriminalLink(fir_id=fir_one.id, criminal_id=crook_a.id, role="accused"),
        FIRCriminalLink(fir_id=fir_one.id, criminal_id=crook_b.id, role="accused"),
        FIRCriminalLink(fir_id=fir_two.id, criminal_id=crook_c.id, role="suspect"),
        FIRVictimLink(fir_id=fir_one.id, victim_id=victim_one.id),
    ])
    db_session.commit()

    return {
        "categories": {"theft": cat_theft, "assault": cat_assault},
        "locations": {"blr": loc_blr, "mys": loc_mys},
        "criminals": {"alpha": crook_a, "beta": crook_b, "gamma": crook_c},
        "victim": victim_one,
        "officer": officer_one,
        "cases": {"blr_1": case_blr_1, "blr_2": case_blr_2, "demo": case_demo},
        "firs": {"one": fir_one, "two": fir_two},
    }


@pytest.fixture
def crime_dataset(db_session):
    return seed_crime_dataset(db_session)
