"""Data ingestion routes — bulk CSV/XLSX import through the full pipeline.

Closes M1 (legacy Excel/CSV ingestion) and M2 (CCTNS interoperability) of the
gap-closure issue, plus issue 5 (P1): every upload passes through an import
job, row-level staging, validation, deduplication, reconciliation and quality
grading. Nothing reaches trusted Saksha tables until an administrator promotes
the staged records; promoted rows carry full source provenance and can be
traced (and rolled back) from the API.

See INGESTION_PIPELINE.md at the repo root for the complete workflow.
"""
from __future__ import annotations

import json
import uuid as uuid_mod

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import (
    ROLE_ADMIN,
    ROLE_CRIME_ANALYST,
    ROLE_INVESTIGATOR,
    require_roles,
)
from app.database.postgres import get_db
from app.models.import_job import ImportJob, ImportStagedRecord
from app.models.user import User
from app.services import audit_service
from app.services.ingest_service import (
    IngestError,
    ImportSecurityError,
    VALID_IMPORT_ENTITIES,
    VALID_PROFILES,
    analyze_upload,
    build_template,
    promote_import,
    record_lineage,
    rollback_import,
    run_import_pipeline,
    serialize_job,
    serialize_staged_record,
    validate_file,
)

router = APIRouter(
    prefix="/data-import",
    tags=["Data Import"],
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))],
)

# Administrative operations gated behind a stricter role set (issue 5 §23).
admin_required = Depends(require_roles(ROLE_ADMIN))
import_operators = Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST))


def _load_report(job: ImportJob) -> list:
    try:
        return json.loads(job.validation_report) if job.validation_report else []
    except json.JSONDecodeError:
        return []


def _get_job(db: Session, job_id: str) -> ImportJob | Response:
    try:
        job_uuid = uuid_mod.UUID(job_id)
    except ValueError:
        return Response(status_code=400, content="Invalid job id")
    job = db.query(ImportJob).filter(ImportJob.id == job_uuid).first()
    if job is None:
        return Response(status_code=404, content="Import job not found")
    return job


@router.get("/entities")
def list_import_entities(current_user: User = Depends(get_current_user)):
    """Supported import entities, their expected columns, and available profiles."""
    from app.services.ingest_service import CCTNS_COLUMN_MAPS, ENTITY_SPECS

    return {
        "entities": [
            {
                "entity_type": entity,
                "columns": [
                    {"name": col, "required": rules["required"], "type": rules["type"], "choices": rules.get("choices")}
                    for col, rules in specs.items()
                ],
            }
            for entity, specs in ENTITY_SPECS.items()
        ],
        "profiles": [
            {"profile": "standard", "description": "Saksha-native column templates"},
            {
                "profile": "cctns",
                "description": "Maps CCTNS/ICJS extract headers onto Saksha columns",
                "sample_mappings": {k: v for k, v in list(CCTNS_COLUMN_MAPS["crime_cases"].items())[:6]},
            },
        ],
        "max_rows": 5000,
        "pipeline": [
            "upload", "import_job", "staging", "schema_mapping", "normalization",
            "validation", "deduplication", "reconciliation", "quality_grading",
            "approval", "promotion", "trusted_records",
        ],
    }


@router.get("/template/{entity_type}")
def download_template(
    entity_type: str,
    export_format: str = Query("csv", pattern="^(csv|xlsx)$"),
    current_user: User = Depends(get_current_user),
):
    if entity_type not in VALID_IMPORT_ENTITIES:
        return Response(status_code=404, content="Unknown entity type")
    content, media_type, extension = build_template(entity_type, export_format)
    filename = f"saksha_{entity_type}_import_template.{extension}"
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/preview")
async def preview_import(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    profile: str = Form("standard"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Parse + validate an upload and return the column mapping and validation report without writing anything."""
    if entity_type not in VALID_IMPORT_ENTITIES:
        return Response(status_code=404, content="Unknown entity type")
    if profile not in VALID_PROFILES:
        return Response(status_code=400, content="Unknown mapping profile")
    try:
        content = await file.read()
        validate_file(content, file.filename or "upload.csv")  # §24 file-level gate
        result = analyze_upload(db, content, file.filename or "upload.csv", entity_type, profile)
    except ImportSecurityError as exc:
        return Response(status_code=415, content=str(exc))
    except IngestError as exc:
        return Response(status_code=400, content=str(exc))
    except UnicodeDecodeError:
        return Response(status_code=400, content="File must be UTF-8 text (CSV) or an Excel workbook")
    result.pop("_diagnostic_error_sample_count", None)
    audit_service.log_action(db, current_user, "IMPORT_PREVIEW", "DataImport", f"{entity_type}:{file.filename}", details=f"profile={profile}")
    db.commit()
    return result


@router.post("/commit")
async def commit_data_import(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    profile: str = Form("standard"),
    dry_run: bool = Form(False),
    source_system: str = Form("manual_upload"),
    db: Session = Depends(get_db),
    _operator_ok: None = import_operators,
    current_user: User = Depends(get_current_user),
):
    """Run the full ingestion pipeline: stage + validate + dedup + reconcile.

    Rows are NOT written to production tables here — they land in staging with
    per-row outcomes and the job receives metrics + a quality grade. An admin
    promotes eligible records afterwards via ``POST /jobs/{id}/promote``.
    """
    if entity_type not in VALID_IMPORT_ENTITIES:
        return Response(status_code=404, content="Unknown entity type")
    if profile not in VALID_PROFILES:
        return Response(status_code=400, content="Unknown mapping profile")
    try:
        content = await file.read()
        filename = file.filename or "upload.csv"
        if dry_run:
            validate_file(content, filename)
            result = analyze_upload(db, content, filename, entity_type, profile)
            result.pop("_diagnostic_error_sample_count", None)
            result["dry_run"] = True
            return result
        job = run_import_pipeline(db, content, filename, entity_type, profile, current_user.id, source_system=source_system)
    except ImportSecurityError as exc:
        return Response(status_code=415, content=str(exc))
    except IngestError as exc:
        # Persist the failed job for traceability before surfacing the error.
        db.commit()
        return Response(status_code=400, content=str(exc))
    except UnicodeDecodeError:
        db.commit()
        return Response(status_code=400, content="File must be UTF-8 text (CSV) or an Excel workbook")

    audit_service.log_action(
        db,
        current_user,
        "DATA_IMPORT",
        "ImportJob",
        str(job.id),
        details=json.dumps({
            "entity_type": job.entity_type,
            "total_rows": job.total_rows,
            "new_record_rows": job.new_record_rows,
            "invalid_rows": job.invalid_rows,
            "conflict_rows": job.conflict_rows,
            "quality_grade": job.quality_grade,
            "status": job.status,
        }),
    )
    db.commit()
    report = _load_report(job)
    payload = serialize_job(job, validation_report=report)
    payload["job_id"] = str(job.id)  # legacy field used by the admin panel
    return payload


@router.get("/jobs")
def list_import_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ImportJob).order_by(ImportJob.created_at.desc())
    if status:
        query = query.filter(ImportJob.status == status)
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [serialize_job(job) for job in rows],
    }


@router.get("/jobs/{job_id}")
def get_import_job(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    found = _get_job(db, job_id)
    if isinstance(found, Response):
        return found
    return serialize_job(found, validation_report=_load_report(found))


@router.get("/jobs/{job_id}/quality")
def get_job_quality(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Dataset-level quality report computed from the actual job metrics (§16/§17)."""
    found = _get_job(db, job_id)
    if isinstance(found, Response):
        return found
    from app.services.ingest_service import GRADE_THRESHOLDS, compute_quality_grade

    metrics = {k: getattr(found, k, 0) or 0 for k in (
        "total_rows", "valid_rows", "invalid_rows", "warning_rows",
        "exact_duplicate_rows", "potential_duplicate_rows", "conflict_rows",
        "new_record_rows", "matched_record_rows", "updated_record_rows",
        "rejected_rows", "review_rows", "error_count", "promoted_rows",
    )}
    problems = metrics["invalid_rows"] + metrics["conflict_rows"]
    return {
        "job_id": str(found.id),
        "quality_grade": found.quality_grade,
        "recomputed_grade": compute_quality_grade(metrics),  # integrity cross-check
        "problem_ratio": round(problems / metrics["total_rows"], 4) if metrics["total_rows"] else None,
        "grade_thresholds": GRADE_THRESHOLDS,
        "metrics": metrics,
        "trust_summary": {
            "promotable_now": metrics["new_record_rows"] - metrics["promoted_rows"],
            "requires_review": metrics["review_rows"] + metrics["conflict_rows"],
            "rejected_or_duplicated": metrics["rejected_rows"] + metrics["invalid_rows"],
            "promoted": metrics["promoted_rows"],
        },
    }


@router.get("/jobs/{job_id}/records")
def get_job_records(
    job_id: str,
    validation_status: str | None = Query(None, pattern="^(valid|invalid|warning)$"),
    reconciliation_status: str | None = Query(None),
    duplicate_status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Row-level staging detail: validation errors, duplicates, conflicts (§9-§14)."""
    found = _get_job(db, job_id)
    if isinstance(found, Response):
        return found
    query = db.query(ImportStagedRecord).filter(ImportStagedRecord.job_id == found.id)
    if validation_status:
        query = query.filter(ImportStagedRecord.validation_status == validation_status)
    if reconciliation_status:
        query = query.filter(ImportStagedRecord.reconciliation_status == reconciliation_status)
    if duplicate_status:
        query = query.filter(ImportStagedRecord.duplicate_status == duplicate_status)
    total = query.count()
    rows = query.order_by(ImportStagedRecord.row_number).offset(offset).limit(limit).all()
    return {"total": total, "limit": limit, "offset": offset, "results": [serialize_staged_record(r) for r in rows]}


@router.post("/jobs/{job_id}/promote")
def promote_job_records(
    job_id: str,
    include_review: bool = Form(False),
    db: Session = Depends(get_db),
    _admin_ok: None = admin_required,
    current_user: User = Depends(get_current_user),
):
    """ADMIN ONLY: promote eligible staged records into trusted Saksha tables."""
    found = _get_job(db, job_id)
    if isinstance(found, Response):
        return found
    try:
        outcome = promote_import(db, found, current_user.id, include_review=include_review)
    except IngestError as exc:
        return Response(status_code=409, content=str(exc))
    audit_service.log_action(
        db,
        current_user,
        "IMPORT_PROMOTED",
        "ImportJob",
        str(found.id),
        details=json.dumps({"promoted_rows": outcome["promoted_rows"], "include_review": include_review}),
    )
    db.commit()
    return {"job_id": str(found.id), **outcome}


@router.post("/jobs/{job_id}/rollback")
def rollback_job_records(
    job_id: str,
    db: Session = Depends(get_db),
    _admin_ok: None = admin_required,
    current_user: User = Depends(get_current_user),
):
    """ADMIN ONLY: undo a promotion by deleting ONLY this import's records."""
    found = _get_job(db, job_id)
    if isinstance(found, Response):
        return found
    try:
        removed = rollback_import(db, found)
    except IngestError as exc:
        return Response(status_code=409, content=str(exc))
    audit_service.log_action(
        db,
        current_user,
        "IMPORT_ROLLED_BACK",
        "ImportJob",
        str(found.id),
        details=json.dumps({"removed_records": removed}),
    )
    db.commit()
    return {"job_id": str(found.id), "removed_records": removed, "status": found.status}


@router.get("/lineage/{entity_type}/{record_id}")
def get_record_lineage(
    entity_type: str,
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trace any production record back to its source system/file/import (§26)."""
    if entity_type not in VALID_IMPORT_ENTITIES:
        return Response(status_code=404, content="Unknown entity type")
    lineage = record_lineage(db, entity_type, record_id)
    if lineage is None:
        return Response(status_code=404, content="Record not found")
    return lineage
