"""Tests for semantic MO search + NER extraction (issue #139 M6)."""
from datetime import datetime, timezone
from urllib.parse import quote

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR
from app.models.location import Location
from app.models.role import Role
from app.models.user import User

MO = "/api/v2/ai/mo"


@pytest.fixture
def analyst_client(client, db_session):
    role = db_session.query(Role).filter_by(name="crime_analyst").first()
    if role is None:
        role = Role(name="crime_analyst", description="Crime Analyst")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="mo-analyst",
        email="mo-analyst@example.com",
        full_name="MO Analyst",
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
def mo_corpus(db_session):
    category = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="medium")
    location = Location(district="Bengaluru Urban", station="KR Puram", latitude=13.0, longitude=77.7)
    crook_one = Criminal(
        full_name="Two-Wheel Thief",
        status="at_large",
        mo_summary="Steals parked scooters and motorcycles at night using a duplicate key; escapes on the stolen two-wheeler.",
    )
    crook_two = Criminal(
        full_name="Cyber Fraudster",
        status="wanted",
        mo_summary="Calls victims posing as bank officials and tricks them into sharing OTP codes for digital fraud.",
    )
    db_session.add_all([category, location, crook_one, crook_two])
    db_session.flush()

    case = CrimeCase(
        case_number="CR-MO-0001", category_id=category.id, location_id=location.id,
        occurred_at=datetime(2026, 5, 1, tzinfo=timezone.utc), status="open",
        description="Unknown men took an unattended motorcycle near the bus stand; vehicle was KA-05-AB-1234. Witness Mr Ramesh Gowda reported at 21:30; Rs 40,000 loss.",
        mo_tags="vehicle_theft,night",
    )
    db_session.add(case)
    db_session.flush()
    fir = FIR(fir_number="FIR-MO-0001", crime_case_id=case.id,
              complainant_name="Ramesh Gowda", sections="379",
              narrative="Complainant Mr Ramesh Gowda stated his black scooter KA 12 CD 5678 was taken between 21:00 and 22:00 near KR Puram.")
    db_session.add(fir)
    db_session.commit()
    return {"case": case}


def test_semantic_search_finds_paraphrase(analyst_client, mo_corpus):
    """The query shares no keywords with 'scooter'/'motorcycle' but should still match."""
    c, _ = analyst_client
    r = c.get(f"{MO}/search?q={quote('stolen bike taken during darkness')}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["corpus_size"] >= 3
    titles = [res["title"] for res in body["results"]]
    assert "Two-Wheel Thief" in titles or "CR-MO-0001" in titles


def test_search_kind_filter(analyst_client, mo_corpus):
    c, _ = analyst_client
    r = c.get(f"{MO}/search?q=fraud%20otp%20bank&kinds=criminal")
    body = r.json()
    kinds = {res["kind"] for res in body["results"]}
    assert kinds <= {"criminal"}
    assert any(res["title"] == "Cyber Fraudster" for res in body["results"])


def test_extract_entities_from_narrative(analyst_client):
    c, _ = analyst_client
    payload = {
        "text": "Accused Mr Mahesh used country-made pistol near Whitefield. "
                "Bike KA-01-JH-4821 stolen at 22:15 on 2026-03-14. Contact 9880012345. Loss Rs 2 lakh."
    }
    r = c.post(f"{MO}/extract-entities", json=payload)
    assert r.status_code == 200, r.text
    entities = r.json()["entities"]
    assert "KA-01-JH-4821" in entities["vehicle_plates"]
    assert "9880012345" in entities["phone_numbers"]
    assert any("pistol" in w for w in entities["weapons"])
    assert "Whitefield" in entities["places"]
    assert "Mahesh" in entities["person_names"]
    assert r.json()["entity_count"] >= 4


def test_extract_case_entities_endpoint(analyst_client, mo_corpus):
    c, _ = analyst_client
    r = c.get(f"{MO}/extract-case/{mo_corpus['case'].id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["case_number"] == "CR-MO-0001"
    plates = body["entities"]["vehicle_plates"]
    assert any("KA" in p for p in plates)


def test_extract_case_unknown_id(analyst_client):
    c, _ = analyst_client
    r = c.get(f"{MO}/extract-case/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 200, r.text
    assert r.json() == {"error": "Case not found"}
