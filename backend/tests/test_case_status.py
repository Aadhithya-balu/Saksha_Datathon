"""Tests for Issue #252 — Immutable Crime/Case Status.

Covers:
  - Canonical status module (unit)
  - Valid transitions
  - Invalid transitions (ARRESTED → ACTIVE, ARRESTED → ARRESTED, etc.)
  - Creation with immutable status rejected
  - API create / update endpoints
  - Direct API bypass attempts
  - Audit log creation on transition
  - Existing records with missing / valid status (migration safety)
  - UI-locked state reflected in API response (is_locked field)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.location import Location
from app.models.role import Role
from app.models.user import User
from app.models.audit_log import AuditLog
from app.services.case_status import (
    STATUS_ACTIVE,
    STATUS_ARRESTED,
    STATUS_CHARGESHEETED,
    STATUS_CLOSED,
    STATUS_CONVICTED,
    STATUS_UNDER_INVESTIGATION,
    InvalidStatusTransitionError,
    is_immutable,
    validate_transition,
    _canonical,
)

CRIMES_URL = "/api/v2/crimes"
CASES_URL = "/api/v2/crime-cases"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(db, role_name: str = "admin") -> User:
    role = db.query(Role).filter_by(name=role_name).first()
    if not role:
        role = Role(name=role_name, description=role_name)
        db.add(role)
        db.flush()
    user = User(
        username=f"test-{role_name}-{uuid.uuid4().hex[:6]}",
        email=f"test-{uuid.uuid4().hex[:6]}@example.com",
        full_name="Test User",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _seed_case(db, status: str = STATUS_ACTIVE) -> tuple[CrimeCase, CrimeCategory, Location]:
    cat = CrimeCategory(name=f"Cat-{uuid.uuid4().hex[:4]}", section_code="BNS 302", severity="high")
    loc = Location(district="Bengaluru Urban", station="Test PS", latitude=12.97, longitude=77.59)
    db.add_all([cat, loc])
    db.flush()
    case = CrimeCase(
        case_number=f"CR-2026-TEST-{uuid.uuid4().hex[:6].upper()}",
        category_id=cat.id,
        location_id=loc.id,
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status=status,
    )
    db.add(case)
    db.flush()
    return case, cat, loc


@pytest.fixture
def admin_client(client, db_session):
    user = _make_user(db_session, "admin")
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def investigator_client(client, db_session):
    user = _make_user(db_session, "investigator")
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client
    client.app.dependency_overrides.pop(get_current_user, None)


# ===========================================================================
# Unit tests — case_status module
# ===========================================================================

class TestCanonicalMapping:
    def test_legacy_open_maps_to_active(self):
        assert _canonical("open") == STATUS_ACTIVE

    def test_legacy_assigned_maps_to_active(self):
        assert _canonical("assigned") == STATUS_ACTIVE

    def test_legacy_investigating_maps_to_under_investigation(self):
        assert _canonical("investigating") == STATUS_UNDER_INVESTIGATION

    def test_legacy_evidence_collected_maps_to_under_investigation(self):
        assert _canonical("evidence collected") == STATUS_UNDER_INVESTIGATION

    def test_legacy_charge_sheet_filed_maps_to_chargesheeted(self):
        assert _canonical("charge sheet filed") == STATUS_CHARGESHEETED

    def test_canonical_values_map_to_themselves(self):
        for s in (STATUS_ACTIVE, STATUS_UNDER_INVESTIGATION, STATUS_ARRESTED,
                  STATUS_CHARGESHEETED, STATUS_CONVICTED, STATUS_CLOSED):
            assert _canonical(s) == s

    def test_none_maps_to_active(self):
        assert _canonical(None) == STATUS_ACTIVE


class TestIsImmutable:
    def test_arrested_is_immutable(self):
        assert is_immutable(STATUS_ARRESTED) is True

    def test_convicted_is_immutable(self):
        assert is_immutable(STATUS_CONVICTED) is True

    def test_active_is_not_immutable(self):
        assert is_immutable(STATUS_ACTIVE) is False

    def test_under_investigation_is_not_immutable(self):
        assert is_immutable(STATUS_UNDER_INVESTIGATION) is False

    def test_chargesheeted_is_not_immutable(self):
        assert is_immutable(STATUS_CHARGESHEETED) is False

    def test_closed_is_not_immutable(self):
        assert is_immutable(STATUS_CLOSED) is False

    def test_none_is_not_immutable(self):
        assert is_immutable(None) is False


class TestValidTransitions:
    def test_active_to_under_investigation(self):
        assert validate_transition(STATUS_ACTIVE, STATUS_UNDER_INVESTIGATION) == STATUS_UNDER_INVESTIGATION

    def test_active_to_arrested(self):
        assert validate_transition(STATUS_ACTIVE, STATUS_ARRESTED) == STATUS_ARRESTED

    def test_active_to_closed(self):
        assert validate_transition(STATUS_ACTIVE, STATUS_CLOSED) == STATUS_CLOSED

    def test_under_investigation_to_arrested(self):
        assert validate_transition(STATUS_UNDER_INVESTIGATION, STATUS_ARRESTED) == STATUS_ARRESTED

    def test_under_investigation_to_chargesheeted(self):
        assert validate_transition(STATUS_UNDER_INVESTIGATION, STATUS_CHARGESHEETED) == STATUS_CHARGESHEETED

    def test_arrested_to_chargesheeted(self):
        assert validate_transition(STATUS_ARRESTED, STATUS_CHARGESHEETED) == STATUS_CHARGESHEETED

    def test_chargesheeted_to_convicted(self):
        assert validate_transition(STATUS_CHARGESHEETED, STATUS_CONVICTED) == STATUS_CONVICTED

    def test_chargesheeted_to_closed(self):
        assert validate_transition(STATUS_CHARGESHEETED, STATUS_CLOSED) == STATUS_CLOSED

    def test_convicted_to_closed(self):
        assert validate_transition(STATUS_CONVICTED, STATUS_CLOSED) == STATUS_CLOSED

    def test_legacy_open_to_arrested(self):
        """Legacy 'open' status should be treated as 'active' for transition purposes."""
        assert validate_transition("open", STATUS_ARRESTED) == STATUS_ARRESTED

    def test_legacy_investigating_to_arrested(self):
        assert validate_transition("investigating", STATUS_ARRESTED) == STATUS_ARRESTED

    def test_creation_with_active(self):
        """None current_status = creation path."""
        assert validate_transition(None, STATUS_ACTIVE) == STATUS_ACTIVE

    def test_creation_with_under_investigation(self):
        assert validate_transition(None, STATUS_UNDER_INVESTIGATION) == STATUS_UNDER_INVESTIGATION


class TestInvalidTransitions:
    def test_arrested_to_active_rejected(self):
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            validate_transition(STATUS_ARRESTED, STATUS_ACTIVE)
        assert "locked" in exc_info.value.message.lower()

    def test_arrested_to_arrested_rejected(self):
        """No-op transition must be rejected."""
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            validate_transition(STATUS_ARRESTED, STATUS_ARRESTED)
        assert "already" in exc_info.value.message.lower()

    def test_arrested_to_under_investigation_rejected(self):
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(STATUS_ARRESTED, STATUS_UNDER_INVESTIGATION)

    def test_arrested_to_closed_rejected(self):
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(STATUS_ARRESTED, STATUS_CLOSED)

    def test_convicted_to_active_rejected(self):
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(STATUS_CONVICTED, STATUS_ACTIVE)

    def test_convicted_to_arrested_rejected(self):
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(STATUS_CONVICTED, STATUS_ARRESTED)

    def test_closed_to_active_rejected(self):
        """Closed is terminal."""
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(STATUS_CLOSED, STATUS_ACTIVE)

    def test_active_to_convicted_rejected(self):
        """Cannot skip steps."""
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(STATUS_ACTIVE, STATUS_CONVICTED)

    def test_active_to_chargesheeted_rejected(self):
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(STATUS_ACTIVE, STATUS_CHARGESHEETED)

    def test_creation_with_arrested_rejected(self):
        """Cannot create a case already in ARRESTED state."""
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            validate_transition(None, STATUS_ARRESTED)
        assert "create" in exc_info.value.message.lower()

    def test_creation_with_convicted_rejected(self):
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(None, STATUS_CONVICTED)

    def test_unknown_status_rejected(self):
        with pytest.raises(InvalidStatusTransitionError):
            validate_transition(STATUS_ACTIVE, "banana")

    def test_same_status_noop_rejected(self):
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            validate_transition(STATUS_ACTIVE, STATUS_ACTIVE)
        assert "already" in exc_info.value.message.lower()


# ===========================================================================
# API integration tests
# ===========================================================================

class TestCrimeCreateAPI:
    def test_create_with_active_status(self, admin_client, db_session):
        cat = CrimeCategory(name=f"Cat-{uuid.uuid4().hex[:4]}", section_code="X", severity="low")
        loc = Location(district="Mysuru", station="PS1", latitude=12.0, longitude=76.0)
        db_session.add_all([cat, loc])
        db_session.commit()

        r = admin_client.post(CRIMES_URL, json={
            "case_number": f"CR-2026-API-{uuid.uuid4().hex[:6].upper()}",
            "category_id": str(cat.id),
            "location_id": str(loc.id),
            "occurred_at": "2026-01-01T10:00:00",
            "status": "active",
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "active"
        assert body["is_locked"] is False

    def test_create_with_arrested_status_rejected(self, admin_client, db_session):
        cat = CrimeCategory(name=f"Cat-{uuid.uuid4().hex[:4]}", section_code="X", severity="low")
        loc = Location(district="Mysuru", station="PS2", latitude=12.0, longitude=76.0)
        db_session.add_all([cat, loc])
        db_session.commit()

        r = admin_client.post(CRIMES_URL, json={
            "case_number": f"CR-2026-API-{uuid.uuid4().hex[:6].upper()}",
            "category_id": str(cat.id),
            "location_id": str(loc.id),
            "occurred_at": "2026-01-01T10:00:00",
            "status": "arrested",
        })
        assert r.status_code == 422, r.text

    def test_create_with_convicted_status_rejected(self, admin_client, db_session):
        cat = CrimeCategory(name=f"Cat-{uuid.uuid4().hex[:4]}", section_code="X", severity="low")
        loc = Location(district="Mysuru", station="PS3", latitude=12.0, longitude=76.0)
        db_session.add_all([cat, loc])
        db_session.commit()

        r = admin_client.post(CRIMES_URL, json={
            "case_number": f"CR-2026-API-{uuid.uuid4().hex[:6].upper()}",
            "category_id": str(cat.id),
            "location_id": str(loc.id),
            "occurred_at": "2026-01-01T10:00:00",
            "status": "convicted",
        })
        assert r.status_code == 422, r.text


class TestCrimeUpdateAPI:
    def test_valid_transition_active_to_arrested(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_ACTIVE)
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "arrested"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == STATUS_ARRESTED
        assert r.json()["is_locked"] is True

    def test_valid_transition_arrested_to_chargesheeted(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_ARRESTED)
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "chargesheeted"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == STATUS_CHARGESHEETED

    def test_invalid_transition_arrested_to_active_rejected(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_ARRESTED)
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "active"})
        assert r.status_code == 422, r.text
        body = r.json()
        # Error message may be in 'detail' (HTTPException) or nested under 'error.message' (AppException handler)
        detail = body.get("detail") or body.get("error", {}).get("message", "")
        assert "locked" in detail.lower() or "transition" in detail.lower() or "not permitted" in detail.lower()

    def test_invalid_transition_arrested_to_arrested_rejected(self, admin_client, db_session):
        """No-op update must be rejected."""
        case, _, _ = _seed_case(db_session, STATUS_ARRESTED)
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "arrested"})
        assert r.status_code == 422, r.text

    def test_invalid_transition_active_to_convicted_rejected(self, admin_client, db_session):
        """Cannot skip steps."""
        case, _, _ = _seed_case(db_session, STATUS_ACTIVE)
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "convicted"})
        assert r.status_code == 422, r.text

    def test_field_edit_on_locked_case_rejected(self, admin_client, db_session):
        """Non-status field edits on a locked case must be rejected."""
        case, _, _ = _seed_case(db_session, STATUS_ARRESTED)
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"description": "tampered"})
        assert r.status_code == 422, r.text
        body = r.json()
        detail = body.get("detail") or body.get("error", {}).get("message", "")
        assert "locked" in detail.lower()

    def test_direct_api_bypass_arrested_to_open_rejected(self, admin_client, db_session):
        """Simulates a direct API call attempting to bypass the UI."""
        case, _, _ = _seed_case(db_session, STATUS_ARRESTED)
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "open"})
        assert r.status_code == 422, r.text

    def test_direct_api_bypass_convicted_to_active_rejected(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_CONVICTED)
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "active"})
        assert r.status_code == 422, r.text

    def test_unknown_status_rejected(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_ACTIVE)
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "banana"})
        assert r.status_code == 422, r.text


class TestCrimeCasesUpdateAPI:
    """Same transition rules must hold on the /crime-cases endpoint."""

    def test_valid_transition_via_crime_cases(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_ACTIVE)
        db_session.commit()

        r = admin_client.put(f"{CASES_URL}/{case.id}", json={"status": "under_investigation"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == STATUS_UNDER_INVESTIGATION

    def test_arrested_to_active_rejected_via_crime_cases(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_ARRESTED)
        db_session.commit()

        r = admin_client.put(f"{CASES_URL}/{case.id}", json={"status": "active"})
        assert r.status_code == 422, r.text

    def test_arrested_to_arrested_rejected_via_crime_cases(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_ARRESTED)
        db_session.commit()

        r = admin_client.put(f"{CASES_URL}/{case.id}", json={"status": "arrested"})
        assert r.status_code == 422, r.text


class TestIsLockedField:
    def test_legacy_unsolved_case_can_be_listed(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, "unsolved")
        db_session.commit()

        r = admin_client.get(f"{CASES_URL}?page_size=100")

        assert r.status_code == 200, r.text
        listed_case = next(item for item in r.json()["results"] if item["id"] == str(case.id))
        assert listed_case["status"] == "unsolved"
        assert listed_case["is_locked"] is False

    def test_active_case_not_locked(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_ACTIVE)
        db_session.commit()

        r = admin_client.get(f"{CRIMES_URL}/{case.id}")
        assert r.status_code == 200
        assert r.json()["is_locked"] is False

    def test_arrested_case_is_locked(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_ARRESTED)
        db_session.commit()

        r = admin_client.get(f"{CRIMES_URL}/{case.id}")
        assert r.status_code == 200
        assert r.json()["is_locked"] is True

    def test_convicted_case_is_locked(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_CONVICTED)
        db_session.commit()

        r = admin_client.get(f"{CRIMES_URL}/{case.id}")
        assert r.status_code == 200
        assert r.json()["is_locked"] is True


class TestAuditLogging:
    def test_status_transition_creates_audit_entry(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_ACTIVE)
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "arrested"})
        assert r.status_code == 200, r.text

        # Verify audit log entry was created
        log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.resource_type == "CrimeCase",
                AuditLog.resource_id == str(case.id),
                AuditLog.action == "STATUS_TRANSITION",
            )
            .first()
        )
        assert log is not None, "Audit log entry for STATUS_TRANSITION not found"
        assert "Active" in log.details or "active" in log.details
        assert "Arrested" in log.details or "arrested" in log.details

    def test_failed_transition_does_not_create_audit_entry(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, STATUS_ARRESTED)
        db_session.commit()

        before_count = db_session.query(AuditLog).filter(
            AuditLog.resource_id == str(case.id),
            AuditLog.action == "STATUS_TRANSITION",
        ).count()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "active"})
        assert r.status_code == 422

        after_count = db_session.query(AuditLog).filter(
            AuditLog.resource_id == str(case.id),
            AuditLog.action == "STATUS_TRANSITION",
        ).count()
        assert after_count == before_count, "Audit entry must not be created for rejected transitions"


class TestExistingRecordsMigrationSafety:
    def test_existing_record_with_valid_canonical_status_unchanged(self, db_session):
        """Records already using canonical status values must not be touched."""
        case, _, _ = _seed_case(db_session, STATUS_UNDER_INVESTIGATION)
        db_session.commit()

        db_session.refresh(case)
        assert case.status == STATUS_UNDER_INVESTIGATION

    def test_existing_record_with_legacy_open_status_readable(self, admin_client, db_session):
        """Legacy 'open' records must still be readable and usable."""
        case, _, _ = _seed_case(db_session, "open")
        db_session.commit()

        r = admin_client.get(f"{CRIMES_URL}/{case.id}")
        assert r.status_code == 200
        # is_locked must be False for legacy 'open' (maps to active)
        assert r.json()["is_locked"] is False

    def test_existing_record_with_legacy_status_can_transition(self, admin_client, db_session):
        """Legacy 'open' record should accept a valid forward transition."""
        case, _, _ = _seed_case(db_session, "open")
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "arrested"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == STATUS_ARRESTED

    def test_existing_record_with_legacy_investigating_can_transition(self, admin_client, db_session):
        case, _, _ = _seed_case(db_session, "investigating")
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "arrested"})
        assert r.status_code == 200, r.text

    def test_existing_arrested_record_cannot_be_downgraded(self, admin_client, db_session):
        """Pre-existing ARRESTED records must be protected even if set before this issue."""
        case, _, _ = _seed_case(db_session, STATUS_ARRESTED)
        db_session.commit()

        r = admin_client.put(f"{CRIMES_URL}/{case.id}", json={"status": "open"})
        assert r.status_code == 422, r.text
