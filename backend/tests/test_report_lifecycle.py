"""Issue #176 — production-ready reporting & audit lifecycle tests.

Covers the 15 scenarios in §37 using a real isolated SQLite DB (not mocked
models): creation, authorization, source/evidence linking, provenance,
versioning, finalization, audit trail, download audit, failure state,
source-change traceability, AI report validation, and audit authorization.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.evidence import Evidence
from app.models.location import Location
from app.models.officer import Officer
from app.models.report import Report, ReportEvidenceLink, ReportSourceLink, ReportVersion
from app.models.role import Role
from app.models.user import User

REPORTS = "/api/v2/reports"


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


def _seed_case_with_evidence(db_session):
    category = CrimeCategory(name="Theft", section_code="IPC 379", severity="medium")
    location = Location(district="Bengaluru Urban", station="Whitefield", latitude=12.9716, longitude=77.5946)
    officer = Officer(badge_number="IO-RPT-1", name="Rpt Officer", rank="Inspector", station="Whitefield")
    criminal = Criminal(full_name="Rpt Crook", status="wanted")
    db_session.add_all([category, location, officer, criminal])
    db_session.flush()
    case = CrimeCase(
        case_number="CR-RPT-0001",
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
        created_by="rpt-analyst",
    )
    db_session.add(evidence)
    db_session.commit()
    return {"case": case, "criminal": criminal, "evidence": evidence}


@pytest.fixture
def analyst_client(client, db_session):
    user = _make_user(db_session, "rpt-analyst", "crime_analyst")
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def other_analyst_client(client, db_session):
    """Creates a second analyst user; the test sets the active user explicitly."""
    user = _make_user(db_session, "rpt-analyst-2", "crime_analyst")
    db_session.commit()
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def admin_client(client, db_session):
    """Creates an admin user; the test sets the active user explicitly."""
    user = _make_user(db_session, "rpt-admin", "admin")
    db_session.commit()
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def viewer_client(client, db_session):
    user = _make_user(db_session, "rpt-viewer", "viewer")
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


def _create_report(client, report_type="cases", title="Ops Report"):
    return client.post(REPORTS, json={"report_type": report_type, "title": title})


# Test 1 — Create Report with correct user + timestamp
def test_create_report(analyst_client, db_session):
    c, user = analyst_client
    r = c.post(REPORTS, json={"report_type": "cases", "title": "Q1 Intelligence"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "draft"
    assert body["requested_by"] == user.full_name
    assert body["version"] == 1
    assert body["report_type"] == "cases"
    assert body["created_at"] is not None
    saved = db_session.query(Report).filter(Report.id == uuid.UUID(body["id"])).first()
    assert saved is not None
    assert saved.requested_by_id == user.id
    assert saved.created_at is not None


# Test 2 — Unauthorized Report access
def test_unauthorized_report_access(viewer_client, db_session):
    role = _make_role(db_session, "crime_analyst")
    owner = User(
        username="rpt-owner", email="rpt-owner@example.com", full_name="Owner",
        hashed_password=hash_password("Password123!"), role_id=role.id, is_active=True,
    )
    db_session.add(owner)
    db_session.flush()
    report = Report(template="cases_report", report_type="cases", requested_by_id=owner.id, status="draft", title="Private")
    db_session.add(report)
    db_session.commit()

    c, _ = viewer_client
    r = c.get(f"{REPORTS}/{report.id}")
    assert r.status_code == 403, r.text
    # Viewer cannot hit admin audit endpoint either
    r2 = c.get(f"{REPORTS}/{report.id}/audit")
    assert r2.status_code == 403, r2.text


# Test 3 — Source linking
def test_source_linking(analyst_client, db_session):
    seeded = _seed_case_with_evidence(db_session)
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    r = c.post(
        f"{REPORTS}/{rid}/generate",
        json={
            "content": {"headers": ["case_number"], "rows": [[seeded["case"].case_number]]},
            "sources": [{"source_type": "crime_case", "source_id": str(seeded["case"].id)}],
            "evidence_ids": [],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source_record_count"] >= 1
    links = db_session.query(ReportSourceLink).filter(ReportSourceLink.report_id == uuid.UUID(rid)).all()
    assert any(l.source_type == "crime_case" for l in links)


# Test 4 — Evidence linking
def test_evidence_linking(analyst_client, db_session):
    seeded = _seed_case_with_evidence(db_session)
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    r = c.post(
        f"{REPORTS}/{rid}/generate",
        json={
            "content": {"headers": ["evidence"], "rows": [["laptop"]]},
            "sources": [],
            "evidence_ids": [str(seeded["evidence"].id)],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["evidence_count"] >= 1
    links = db_session.query(ReportEvidenceLink).filter(ReportEvidenceLink.report_id == uuid.UUID(rid)).all()
    assert any(l.evidence_id == seeded["evidence"].id for l in links)


# Test 5 — Provenance identifies DEMO
def test_provenance_demo(analyst_client, db_session):
    seeded = _seed_case_with_evidence(db_session)
    seeded["case"].dataset_provenance = "demo"
    db_session.commit()
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    r = c.post(
        f"{REPORTS}/{rid}/generate",
        json={
            "content": {"headers": ["case_number"], "rows": [["x"]]},
            "sources": [{"source_type": "crime_case", "source_id": str(seeded["case"].id)}],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["provenance"] == "demo"


# Test 6 — Versioning
def test_versioning(analyst_client, db_session):
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    c.post(f"{REPORTS}/{rid}/generate", json={
        "content": {"headers": ["a"], "rows": [["1"]]}, "sources": []
    })
    r = c.post(f"{REPORTS}/{rid}/versions", json={"reason": "update totals"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["version"] == 2
    assert len(body["versions"]) == 2
    # previous version retained
    assert body["versions"][0]["version_number"] == 1


# Test 7 — Finalization immutability
def test_finalization_immutability(analyst_client, db_session):
    seeded = _seed_case_with_evidence(db_session)
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    c.post(f"{REPORTS}/{rid}/generate", json={
        "content": {"headers": ["case_number"], "rows": [[seeded["case"].case_number]]},
        "sources": [{"source_type": "crime_case", "source_id": str(seeded["case"].id)}],
    })
    r = c.post(f"{REPORTS}/{rid}/finalize")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "final"
    assert r.json()["integrity_hash"] is not None

    # Normal user cannot silently regenerate a finalized report
    r2 = c.post(f"{REPORTS}/{rid}/generate", json={
        "content": {"headers": ["case_number"], "rows": [["changed"]]}, "sources": []
    })
    assert r2.status_code == 409, r2.text
    saved = db_session.query(Report).filter(Report.id == uuid.UUID(rid)).first()
    assert saved.status == "final"
    assert saved.content_snapshot is not None
    assert "changed" not in saved.content_snapshot


# Test 8 — Audit trail
def test_audit_trail(analyst_client, db_session):
    seeded = _seed_case_with_evidence(db_session)
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    c.post(f"{REPORTS}/{rid}/generate", json={
        "content": {"headers": ["case_number"], "rows": [[seeded["case"].case_number]]},
        "sources": [{"source_type": "crime_case", "source_id": str(seeded["case"].id)}],
    })
    c.post(f"{REPORTS}/{rid}/finalize")
    actions = {a[0] for a in db_session.query(AuditLog.action).all()}
    assert "REPORT_CREATE" in actions
    assert "REPORT_GENERATE" in actions
    assert "REPORT_FINALIZE" in actions


# Test 9 — Download audit
def test_download_audit(analyst_client, db_session):
    seeded = _seed_case_with_evidence(db_session)
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    c.post(f"{REPORTS}/{rid}/generate", json={
        "content": {"headers": ["case_number"], "rows": [[seeded["case"].case_number]]},
        "sources": [],
    })
    r = c.get(f"{REPORTS}/{rid}/download?export_format=txt")
    assert r.status_code == 200, r.text
    seen = db_session.query(AuditLog).filter(
        AuditLog.resource_id == rid, AuditLog.action == "REPORT_DOWNLOAD"
    ).count()
    assert seen >= 1


# Test 10 — Invalid report failure state
def test_failed_generation(analyst_client, db_session):
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    r = c.post(f"{REPORTS}/{rid}/generate", json={
        "content": {"headers": ["case"], "rows": [["1"]]},
        "sources": [{"source_type": "crime_case", "source_id": str(uuid.uuid4())}],
    })
    assert r.status_code in (409,), r.text
    saved = db_session.query(Report).filter(Report.id == uuid.UUID(rid)).first()
    assert saved.status == "failed", "failed generation must mark report FAILED, never FINAL"
    assert saved.failure_reason is not None


# Test 11 — Source record changes after finalization remain traceable
def test_source_change_traceability(analyst_client, db_session):
    seeded = _seed_case_with_evidence(db_session)
    original_number = seeded["case"].case_number
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    c.post(f"{REPORTS}/{rid}/generate", json={
        "content": {"headers": ["case_number"], "rows": [[original_number]]},
        "sources": [{"source_type": "crime_case", "source_id": str(seeded["case"].id)}],
    })
    c.post(f"{REPORTS}/{rid}/finalize")
    # underlying record changes after finalization
    seeded["case"].case_number = "CR-CHANGED-9999"
    db_session.commit()
    r = c.get(f"{REPORTS}/{rid}")
    assert r.status_code == 200, r.text
    body = r.json()
    # the report still references the original source record
    assert body["source_record_count"] >= 1
    assert any(s["source_id"] == str(seeded["case"].id) for s in body["sources"])
    # and the FINAL report snapshot still holds the ORIGINAL value used at
    # generation — it did not silently change when the DB record changed.
    ver = db_session.query(ReportVersion).filter(
        ReportVersion.report_id == uuid.UUID(rid), ReportVersion.version_number == 1
    ).first()
    assert ver is not None
    assert original_number in ver.content_snapshot


# Test 12 — AI report references real records
def test_ai_report_real_records(analyst_client, db_session):
    seeded = _seed_case_with_evidence(db_session)
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    r = c.post(f"{REPORTS}/{rid}/generate", json={
        "content": {"headers": ["case_number"], "rows": [[seeded["case"].case_number]]},
        "sources": [{"source_type": "crime_case", "source_id": str(seeded["case"].id)}],
        "ai_metadata": {"provider": "test-llm", "model": "test-model", "prompt_version": "p1"},
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ai_reported"] is True
    assert body["generation_method"] == "ai_assisted"
    assert body["ai_metadata"]["provider"] == "test-llm"
    assert body["provenance"] != "unknown"


# Test 13 — AI hallucinated source cannot be finalized
def test_ai_hallucinated_source(analyst_client, db_session):
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    r = c.post(f"{REPORTS}/{rid}/generate", json={
        "content": {"headers": ["case_number"], "rows": [["x"]]},
        "sources": [{"source_type": "crime_case", "source_id": str(uuid.uuid4())}],
        "ai_metadata": {"provider": "test-llm"},
    })
    assert r.status_code == 409, r.text
    saved = db_session.query(Report).filter(Report.id == uuid.UUID(rid)).first()
    assert saved.status == "failed"
    # Cannot finalize a failed report
    r2 = c.post(f"{REPORTS}/{rid}/finalize")
    assert r2.status_code == 403 or r2.status_code != 200
    assert saved.status != "final"


# Test 14 — Audit authorization (admin only)
def test_audit_authorization(analyst_client, admin_client, db_session, client):
    seeded = _seed_case_with_evidence(db_session)
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    c.post(f"{REPORTS}/{rid}/generate", json={
        "content": {"headers": ["case_number"], "rows": [[seeded["case"].case_number]]}, "sources": []
    })

    # Analyst cannot read audit logs (still analyst override active here)
    r = c.get(f"{REPORTS}/{rid}/audit")
    assert r.status_code == 403, r.text

    # Admin CAN — switch the shared test client's active user to admin
    client.app.dependency_overrides[get_current_user] = lambda: admin_client[1]
    r = client.get(f"{REPORTS}/{rid}/audit")
    assert r.status_code == 200, r.text
    assert r.json()["total"] >= 1
    client.app.dependency_overrides[get_current_user] = lambda: analyst_client[1]


# Test 15 — Report download security (unauthorized user)
def test_download_security(analyst_client, other_analyst_client, client):
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    c.post(f"{REPORTS}/{rid}/generate", json={
        "content": {"headers": ["case_number"], "rows": [["x"]]}, "sources": []
    })
    # Different user tries to download the first user's report
    client.app.dependency_overrides[get_current_user] = lambda: other_analyst_client[1]
    r = client.get(f"{REPORTS}/{rid}/download?export_format=txt")
    assert r.status_code == 403, r.text
    client.app.dependency_overrides[get_current_user] = lambda: analyst_client[1]


# Test extra — lifetime flow draft -> generated -> under_review -> final -> archived
def test_full_lifecycle(analyst_client, db_session):
    seeded = _seed_case_with_evidence(db_session)
    c, _ = analyst_client
    rid = _create_report(c).json()["id"]
    assert c.get(f"{REPORTS}/{rid}").json()["status"] == "draft"
    c.post(f"{REPORTS}/{rid}/generate", json={
        "content": {"headers": ["case_number"], "rows": [[seeded["case"].case_number]]},
        "sources": [{"source_type": "crime_case", "source_id": str(seeded["case"].id)}],
    })
    r = c.post(f"{REPORTS}/{rid}/review")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "under_review"
    r = c.post(f"{REPORTS}/{rid}/finalize")
    assert r.json()["status"] == "final"
    r = c.post(f"{REPORTS}/{rid}/archive")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "archived"
