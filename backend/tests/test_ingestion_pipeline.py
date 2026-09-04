"""Issue 5 (P1) tests: full ingestion pipeline — validation, dedup, reconciliation,
provenance, quality grading, partial failure, authorization."""
import io
import json
from datetime import datetime

import pytest
from openpyxl import Workbook

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.import_job import ImportJob, ImportStagedRecord
from app.models.location import Location
from app.models.role import Role
from app.models.user import User
from app.models.victim import Victim
from app.services.ingest_service import (
    IngestError,
    ImportSecurityError,
    compute_quality_grade,
    promote_import,
    rollback_import,
    run_import_pipeline,
    validate_file,
)

IMPORTS = "/api/v2/data-import"


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _csv(rows: list[str]) -> bytes:
    return ("\ufeff" + "\n".join(rows)).encode("utf-8")


@pytest.fixture
def analyst(client, db_session):
    role = db_session.query(Role).filter_by(name="crime_analyst").first()
    if role is None:
        role = Role(name="crime_analyst", description="Crime Analyst")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="pipeline-analyst",
        email="pipeline-analyst@example.com",
        full_name="Pipeline Analyst",
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
def admin_user(db_session):
    role = db_session.query(Role).filter_by(name="admin").first()
    if role is None:
        role = Role(name="admin", description="Administrator")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="pipeline-admin",
        email="pipeline-admin@example.com",
        full_name="Pipeline Admin",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def reference(db_session):
    category = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="medium")
    location = Location(district="Bengaluru Urban", station="KR Puram", latitude=13.0, longitude=77.7)
    db_session.add_all([category, location])
    db_session.commit()
    return {"category": category, "location": location}


def _run_cases_csv(db_session, user, rows: list[str], profile: str = "standard"):
    return run_import_pipeline(
        db_session, _csv(rows), "cases.csv", "crime_cases", profile, user.id
    )


def _staged(db_session, job):
    return (
        db_session.query(ImportStagedRecord)
        .filter(ImportStagedRecord.job_id == job.id)
        .order_by(ImportStagedRecord.row_number)
        .all()
    )


# ---------------------------------------------------------------------------
# File validation (§24) + security (§25)
# ---------------------------------------------------------------------------

def test_rejects_non_csv_extension():
    with pytest.raises(ImportSecurityError):
        validate_file(b"whatever", "payload.exe")


def test_rejects_fake_xlsx():
    with pytest.raises(ImportSecurityError):
        validate_file(b"<html><body>not excel</body></html>", "data.xlsx")


def test_rejects_oversized_csv():
    with pytest.raises(ImportSecurityError):
        validate_file(b"a,b\n" * (3 * 1024 * 1024), "huge.csv")


def test_accepts_real_xlsx():
    workbook = Workbook()
    workbook.active.append(["full_name"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    assert validate_file(buffer.getvalue(), "people.xlsx") == "xlsx"


# ---------------------------------------------------------------------------
# Row validation (§8/§9) and schema rejection (§31)
# ---------------------------------------------------------------------------

def test_missing_required_column_rejects_import(analyst, db_session):
    _, user = analyst
    with pytest.raises(IngestError):
        run_import_pipeline(
            db_session,
            _csv(["gender", "age", "occurred_at", "category_name", "district", "case_number"]),
            "bad.csv",
            "crime_cases",
            "standard",
            user.id,
        )
    job = db_session.query(ImportJob).order_by(ImportJob.created_at.desc()).first()
    assert job.status == "failed"


def test_malformed_row_flagged_with_coded_error(analyst, db_session, reference):
    _, user = analyst
    job = _run_cases_csv(db_session, user, [
        "case_number,category_name,district,station,occurred_at",
        "CR-PIPE-0001,Theft & Burglaries,Bengaluru Urban,KR Puram,not-a-date",
    ])
    row = _staged(db_session, job)[0]
    errors = json.loads(row.validation_errors)
    codes = {e["code"] for e in errors}
    assert "INVALID_DATETIME" in codes or "INVALID_DATE" in codes
    assert row.validation_status == "invalid"
    assert row.trust_level == "rejected"


def test_unknown_category_and_station_reported(analyst, db_session, reference):
    _, user = analyst
    job = _run_cases_csv(db_session, user, [
        "case_number,category_name,district,station,occurred_at",
        "CR-PIPE-0010,Ghost Crime,Bengaluru Urban,Atlantis PS,2026-07-01 10:00",
    ])
    row = _staged(db_session, job)[0]
    codes = {e["code"] for e in json.loads(row.validation_errors)}
    assert "UNKNOWN_CATEGORY" in codes
    assert "LOCATION_NOT_FOUND" in codes


# ---------------------------------------------------------------------------
# Duplicate detection (§10-§12)
# ---------------------------------------------------------------------------

def test_exact_duplicate_within_batch_detected(analyst, db_session, reference):
    _, user = analyst
    job = _run_cases_csv(db_session, user, [
        "case_number,category_name,district,station,occurred_at",
        "CR-PIPE-0020,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-01 10:00",
        "CR-PIPE-0020,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-01 10:00",
    ])
    rows = _staged(db_session, job)
    assert rows[1].duplicate_status == "exact_duplicate"
    assert rows[1].reconciliation_status == "duplicate"
    assert rows[0].reconciliation_status == "new_record"
    assert job.exact_duplicate_rows == 1


def test_existing_record_match_skipped_not_reinserted(analyst, db_session, reference):
    _, user = analyst
    first = _run_cases_csv(db_session, user, [
        "case_number,category_name,district,station,occurred_at,status,priority",
        "CR-PIPE-0030,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-01 10:00,active,high",
    ])
    outcome = promote_import(db_session, first, user.id)
    assert outcome["promoted_rows"] == 1
    db_session.commit()

    second = _run_cases_csv(db_session, user, [
        "case_number,category_name,district,station,occurred_at,status,priority",
        "CR-PIPE-0030,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-01 10:00,active,high",
    ])
    row = _staged(db_session, second)[0]
    assert row.reconciliation_status == "duplicate"
    assert row.duplicate_status == "existing_match"
    result = promote_import(db_session, second, user.id)
    assert result["promoted_rows"] == 0
    assert db_session.query(CrimeCase).filter(CrimeCase.case_number == "CR-PIPE-0030").count() == 1


def test_potential_person_duplicate_flagged_for_review(analyst, db_session):
    _, user = analyst
    job = run_import_pipeline(
        db_session,
        _csv([
            "full_name,gender,date_of_birth",
            "Mohan Kumar,Male,1988-02-11",
            "mohan kumar,Male,1975-09-30",
        ]),
        "criminals.csv",
        "criminals",
        "standard",
        user.id,
    )
    rows = _staged(db_session, job)
    assert rows[0].reconciliation_status == "new_record"
    assert rows[1].duplicate_status == "potential_duplicate"
    assert rows[1].trust_level == "review_required"
    assert job.potential_duplicate_rows == 1
    # Review rows are NOT auto-promoted without an explicit admin override;
    # the clean row still promotes.
    outcome = promote_import(db_session, job, user.id)
    assert outcome["promoted_rows"] == 1


def test_strong_person_duplicate_skipped(analyst, db_session):
    _, user = analyst
    job = run_import_pipeline(
        db_session,
        _csv([
            "full_name,gender,date_of_birth",
            "Deepak Rai,Male,1990-04-04",
            "deepak rai,Male,1990-04-04",
        ]),
        "criminals.csv",
        "criminals",
        "standard",
        user.id,
    )
    rows = _staged(db_session, job)
    assert rows[1].reconciliation_status == "duplicate"


# ---------------------------------------------------------------------------
# Reconciliation + conflict handling (§13/§14)
# ---------------------------------------------------------------------------

def test_conflict_preserves_trusted_record_and_records_both_values(analyst, db_session, reference):
    _, user = analyst
    job = _run_cases_csv(db_session, user, [
        "case_number,category_name,district,station,occurred_at,status,priority",
        "CR-PIPE-0040,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-01 10:00,active,high",
    ])
    assert promote_import(db_session, job, user.id)["promoted_rows"] == 1
    db_session.commit()

    conflict_job = _run_cases_csv(db_session, user, [
        "case_number,category_name,district,station,occurred_at,status,priority",
        "CR-PIPE-0040,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-01 10:00,closed,low",
    ])
    row = _staged(db_session, conflict_job)[0]
    assert row.reconciliation_status == "conflict"
    assert row.trust_level == "review_required"
    details = json.loads(row.reconciliation_details)
    assert details["field_conflicts"]["status"]["existing"] == "active"
    assert details["field_conflicts"]["status"]["imported"] == "closed"

    # Trusted record untouched; conflicts never promote, even with review override.
    trusted = db_session.query(CrimeCase).filter(CrimeCase.case_number == "CR-PIPE-0040").first()
    assert trusted.status == "active"
    result = promote_import(db_session, conflict_job, user.id, include_review=True)
    db_session.refresh(trusted)
    assert trusted.status == "active"
    assert result["skipped_conflicts"] == 1


# ---------------------------------------------------------------------------
# Provenance + lineage (§4/§26)
# ---------------------------------------------------------------------------

def test_promoted_record_carries_provenance(analyst, db_session, reference):
    _, user = analyst
    job = _run_cases_csv(db_session, user, [
        "case_number,category_name,district,station,occurred_at",
        "CR-PIPE-0050,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-05 21:15",
    ])
    promote_import(db_session, job, user.id)
    record = db_session.query(CrimeCase).filter(CrimeCase.case_number == "CR-PIPE-0050").first()
    assert record.dataset_provenance == "migrated"
    assert record.source_import_job_id == job.id
    assert record.source_file == "cases.csv"
    assert record.source_row_ref == "2"  # spreadsheet row including header offset


def test_lineage_roundtrip_via_service(analyst, db_session, reference):
    from app.services.ingest_service import record_lineage

    _, user = analyst
    job = _run_cases_csv(db_session, user, [
        "case_number,category_name,district,station,occurred_at",
        "CR-PIPE-0060,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-06 08:00",
    ])
    promote_import(db_session, job, user.id)
    case = db_session.query(CrimeCase).filter(CrimeCase.case_number == "CR-PIPE-0060").first()
    lineage = record_lineage(db_session, "crime_cases", str(case.id))
    assert lineage["dataset_provenance"] == "migrated"
    assert lineage["source_file"] == "cases.csv"
    assert lineage["import_job"]["id"] == str(job.id)
    assert lineage["import_job"]["quality_grade"] in ("A", "B")


def test_live_records_are_not_marked_migrated(reference, db_session):
    case = CrimeCase(
        case_number="CR-LIVE-1",
        category_id=reference["category"].id,
        location_id=reference["location"].id,
        occurred_at=datetime(2026, 1, 1, 12, 0),
    )
    db_session.add(case)
    db_session.commit()
    assert case.dataset_provenance == "live"
    assert case.source_import_job_id is None


# ---------------------------------------------------------------------------
# Quality grading (§16/§17)
# ---------------------------------------------------------------------------

def test_quality_grade_thresholds():
    assert compute_quality_grade({"total_rows": 100, "valid_rows": 100, "invalid_rows": 0, "conflict_rows": 0}) == "A"
    assert compute_quality_grade({"total_rows": 100, "valid_rows": 97, "invalid_rows": 3, "conflict_rows": 0}) == "B"
    assert compute_quality_grade({"total_rows": 100, "valid_rows": 85, "invalid_rows": 15, "conflict_rows": 0}) == "C"
    assert compute_quality_grade({"total_rows": 100, "valid_rows": 60, "invalid_rows": 40, "conflict_rows": 0}) == "D"
    assert compute_quality_grade({"total_rows": 100, "valid_rows": 30, "invalid_rows": 70, "conflict_rows": 0}) == "REJECTED"
    assert compute_quality_grade({"total_rows": 100, "valid_rows": 0, "invalid_rows": 100, "conflict_rows": 0}) == "REJECTED"
    assert compute_quality_grade({"total_rows": 0, "valid_rows": 0, "invalid_rows": 0, "conflict_rows": 0}) == "REJECTED"


def test_job_grade_computed_from_actual_results(analyst, db_session, reference):
    _, user = analyst
    rows = ["case_number,category_name,district,station,occurred_at"]
    for i in range(8):
        rows.append(f"CR-GRADE-{i:03d},Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-0{i + 1} 09:00")
    rows.append("CR-GRADE-BAD,Theft & Burglaries,Bengaluru Urban,KR Puram,garbage-date")
    job = _run_cases_csv(db_session, user, rows)
    assert job.total_rows == 9
    assert job.invalid_rows == 1
    expected = "A" if 1 / 9 <= 0.02 else ("B" if 1 / 9 <= 0.10 else "C")
    assert job.quality_grade == expected
    # Legacy aliases stay consistent for the admin panel.
    assert job.imported_rows == job.new_record_rows
    assert job.failed_rows == job.invalid_rows


# ---------------------------------------------------------------------------
# Promotion + rollback (§18/§20/§26)
# ---------------------------------------------------------------------------

def test_commit_does_not_write_production_tables(analyst, db_session, reference):
    c, _ = analyst
    r = c.post(
        f"{IMPORTS}/commit",
        files={"file": ("v.csv", _csv([
            "full_name,gender,age",
            "Staging Only Victim,Female,29",
        ]), "text/csv")},
        data={"entity_type": "victims", "profile": "standard"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["promoted_rows"] == 0  # staged only — promotion is a separate step
    assert db_session.query(Victim).filter(Victim.full_name == "Staging Only Victim").count() == 0


def test_rollback_removes_only_this_imports_records(analyst, db_session, reference):
    _, user = analyst
    job = _run_cases_csv(db_session, user, [
        "case_number,category_name,district,station,occurred_at",
        "CR-RB-0001,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-08 11:00",
        "CR-RB-0002,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-08 12:00",
    ])
    promote_import(db_session, job, user.id)
    db_session.commit()

    unrelated = CrimeCase(
        case_number="CR-RB-UNRELATED",
        category_id=reference["category"].id,
        location_id=reference["location"].id,
        occurred_at=datetime(2026, 7, 8, 13, 0),
    )
    db_session.add(unrelated)
    db_session.commit()

    removed = rollback_import(db_session, job)
    db_session.commit()
    assert removed == 2
    remaining = {c.case_number for c in db_session.query(CrimeCase).all()}
    assert "CR-RB-0001" not in remaining and "CR-RB-0002" not in remaining
    assert "CR-RB-UNRELATED" in remaining
    assert job.status == "cancelled"
    assert job.rolled_back_at is not None


def test_double_rollback_rejected(analyst, db_session):
    _, user = analyst
    job = run_import_pipeline(
        db_session,
        _csv(["full_name,gender", "Rollback Person,Male"]),
        "c.csv",
        "criminals",
        "standard",
        user.id,
    )
    rollback_import(db_session, job)
    with pytest.raises(IngestError):
        rollback_import(db_session, job)


# ---------------------------------------------------------------------------
# API surface + authorization (§21/§23/§31)
# ---------------------------------------------------------------------------

def test_commit_then_admin_promote_via_api(analyst, db_session, admin_user, reference):
    c, analyst_user = analyst
    r = c.post(
        f"{IMPORTS}/commit",
        files={"file": ("api.csv", _csv([
            "case_number,category_name,district,station,occurred_at",
            "CR-API-0001,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-09 14:30",
        ]), "text/csv")},
        data={"entity_type": "crime_cases", "profile": "standard"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["quality_grade"] in ("A", "B", "C", "D")
    assert body["new_record_rows"] == 1

    quality = c.get(f"{IMPORTS}/jobs/{body['job_id']}/quality").json()
    assert quality["quality_grade"] == body["quality_grade"]
    assert quality["metrics"]["total_rows"] == 1

    records = c.get(f"{IMPORTS}/jobs/{body['job_id']}/records").json()
    assert records["results"][0]["validation_errors"] == []

    # Promotion is admin-only: analyst attempt is rejected first.
    denied = c.post(f"{IMPORTS}/jobs/{body['job_id']}/promote")
    assert denied.status_code == 403

    c.app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        promote = c.post(f"{IMPORTS}/jobs/{body['job_id']}/promote")
        assert promote.status_code == 200, promote.text
    finally:
        c.app.dependency_overrides[get_current_user] = lambda: analyst_user
    assert promote.json()["promoted_rows"] == 1

    job_detail = c.get(f"{IMPORTS}/jobs/{body['job_id']}").json()
    assert job_detail["promoted_rows"] == 1


def test_unauthorized_role_cannot_access_import_api(client, db_session):
    role = db_session.query(Role).filter_by(name="viewer").first()
    if role is None:
        role = Role(name="viewer", description="Viewer")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="pipeline-viewer",
        email="pipeline-viewer@example.com",
        full_name="Pipeline Viewer",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.post(
            f"{IMPORTS}/commit",
            files={"file": ("v.csv", _csv(["full_name", "X"]), "text/csv")},
            data={"entity_type": "victims"},
        )
        assert r.status_code == 403
        assert client.get(f"{IMPORTS}/jobs").status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)


def test_partial_failure_reported_accurately(analyst, client, reference):
    c, _ = analyst
    rows = ["case_number,category_name,district,station,occurred_at"]
    rows.append("CR-PART-0001,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-10 09:00")
    rows.append("CR-PART-0002,Bad Category,Bengaluru Urban,KR Puram,2026-07-10 09:00")  # invalid
    rows.append("CR-PART-0001,Theft & Burglaries,Bengaluru Urban,KR Puram,2026-07-10 09:00")  # dup of row 1
    rows.append("CR-PART-0003,Theft & Burglaries,Nowhere District,,2026-07-10 09:00")  # district warning, no station
    r = c.post(
        f"{IMPORTS}/commit",
        files={"file": ("p.csv", _csv(rows), "text/csv")},
        data={"entity_type": "crime_cases", "profile": "standard"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_rows"] == 4
    assert body["invalid_rows"] >= 1
    assert body["new_record_rows"] == 2  # row 1 + row 4 (warning but usable)
    assert body["status"] == "completed_with_warnings"
    report_rows = body["validation_report"]
    all_codes = [e["code"] for item in report_rows for e in item.get("error_details", [])]
    assert "UNKNOWN_CATEGORY" in all_codes


def test_cctns_pipeline_end_to_end(analyst, db_session, admin_user, reference):
    c, analyst_user = analyst
    csv_file = _csv([
        "FIR_NO,CRIME_HEAD,DISTRICT_NAME,POLICE_STATION,INCIDENT_DATE,CASE_STATUS,GENERAL_REMARKS,SOME_UNKNOWN_COL",
        "FIR-CCTNS-777,theft and burglaries,bangalore,KR Puram,2026-06-10,Open,Housebreak at night,ignored-value",
    ])
    r = c.post(
        f"{IMPORTS}/commit",
        files={"file": ("extract.csv", csv_file, "text/csv")},
        data={"entity_type": "crime_cases", "profile": "cctns", "source_system": "CCTNS-KA"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source_system"] == "CCTNS-KA"
    assert body["new_record_rows"] == 1
    staged = c.get(f"{IMPORTS}/jobs/{body['job_id']}/records").json()["results"][0]
    assert staged["raw_data"]["SOME_UNKNOWN_COL"] == "ignored-value"  # nothing silently dropped (§6)

    c.app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        promote = c.post(f"{IMPORTS}/jobs/{body['job_id']}/promote")
        assert promote.status_code == 200, promote.text
    finally:
        c.app.dependency_overrides[get_current_user] = lambda: analyst_user
    case = db_session.query(CrimeCase).filter(CrimeCase.case_number == "FIR-CCTNS-777").first()
    assert case is not None
    assert case.dataset_provenance == "migrated"

