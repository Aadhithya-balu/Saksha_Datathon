"""Regression: evidence assignment must store the resolved User UUID.

Assigning evidence to a badge string (e.g. SP-0088) used to pass the raw
string into UUID columns -> "invalid input syntax for type uuid". The endpoint
resolves the badge/name to a real User internally; that resolved id must be
written to Evidence, EvidenceAssignment and ChainOfCustody.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.chain_of_custody import ChainOfCustody
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.evidence import Evidence
from app.models.evidence_assignment import EvidenceAssignment
from app.models.location import Location
from app.models.officer import Officer
from app.models.role import Role
from app.models.user import User

ASSIGN = "/api/v2/evidence"


def _make_role(db_session, name):
    role = db_session.query(Role).filter_by(name=name).first()
    if role is None:
        role = Role(name=name, description=name)
        db_session.add(role)
        db_session.flush()
    return role


def _make_user(db_session, username, role_name):
    role = _make_role(db_session, role_name)
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username.title(),
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def assigner_client(client, db_session):
    user = _make_user(db_session, "evid-analyst", "crime_analyst")
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


def _seed_evidence_target(db_session):
    """Builds a case + evidence, plus an assignee User whose badge SP-0088 is
    linked to an Officer record (mirrors the seeded policymaker)."""
    assignee = _make_user(db_session, "SP-0088", "policymaker")
    officer = Officer(
        badge_number="SP-0088",
        name="SP Anil Kumble",
        rank="Superintendent of Police",
        station="KSP HQ",
        user_id=assignee.id,
    )
    db_session.add(officer)

    category = CrimeCategory(name="Theft", section_code="IPC 379", severity="medium")
    location = Location(district="Bengaluru Urban", station="Whitefield", latitude=12.9716, longitude=77.5946)
    db_session.add_all([category, location])
    db_session.flush()
    case = CrimeCase(
        case_number="CR-EVID-0001",
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
        created_by="evid-analyst",
    )
    db_session.add(evidence)
    db_session.commit()
    return assignee, evidence


def test_assign_with_badge_stores_resolved_user_uuid(assigner_client, db_session):
    client, _ = assigner_client
    assignee, evidence = _seed_evidence_target(db_session)

    resp = client.post(f"{ASSIGN}/{evidence.id}/assign", params={"assigned_to": "SP-0088"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["assigned_to"] == str(assignee.id)
    assert body["status"] == "Assigned"

    db_session.refresh(evidence)
    assert evidence.assigned_to == assignee.id
    assert evidence.status == "Assigned"

    assignment_row = (
        db_session.query(EvidenceAssignment)
        .filter(EvidenceAssignment.evidence_id == evidence.id)
        .first()
    )
    assert assignment_row is not None
    assert assignment_row.assigned_to == assignee.id

    custody = (
        db_session.query(ChainOfCustody)
        .filter(ChainOfCustody.evidence_id == evidence.id)
        .order_by(ChainOfCustody.timestamp.desc())
        .first()
    )
    assert custody is not None
    assert custody.to_user == assignee.id