"""Legacy data ingestion routes — bulk CSV/XLSX import with validation reports.

Closes M1 (legacy Excel/CSV ingestion) and M2 (CCTNS interoperability) of the
gap-closure issue. The ``cctns`` mapping profile lets state CCTNS extracts be
imported directly; see CCTNS_ICJS_INTEROP.md at the repo root.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, require_roles
from app.database.postgres import get_db
from app.models.import_job import ImportJob
from app.models.user import User
from app.services import audit_service
from app.services.ingest_service import (
    IngestError,
    VALID_IMPORT_ENTITIES,
    VALID_PROFILES,
    analyze_upload,
    build_template,
    commit_import,
)

router = APIRouter(
    prefix="/data-import",
    tags=["Data Import"],
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))],
)


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
        result = analyze_upload(db, content, file.filename or "upload.csv", entity_type, profile)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Validate then persist all valid rows; returns the full row-level validation report."""
    if entity_type not in VALID_IMPORT_ENTITIES:
        return Response(status_code=404, content="Unknown entity type")
    if profile not in VALID_PROFILES:
        return Response(status_code=400, content="Unknown mapping profile")
    try:
        content = await file.read()
        if dry_run:
            result = analyze_upload(db, content, file.filename or "upload.csv", entity_type, profile)
            result.pop("_diagnostic_error_sample_count", None)
            result["dry_run"] = True
            return result
        outcome = commit_import(db, content, file.filename or "upload.csv", entity_type, profile, current_user.id)
    except IngestError as exc:
        return Response(status_code=400, content=str(exc))
    except UnicodeDecodeError:
        return Response(status_code=400, content="File must be UTF-8 text (CSV) or an Excel workbook")

    job_record = outcome["job"]
    job = ImportJob(**job_record)
    db.add(job)
    audit_service.log_action(
        db,
        current_user,
        "DATA_IMPORT",
        "ImportJob",
        str(job.id),
        details=json.dumps({k: job_record[k] for k in ("entity_type", "imported_rows", "failed_rows", "status")}),
    )
    db.commit()
    report = outcome["report"]
    return {
        "job_id": str(job.id),
        "status": job.status,
        "entity_type": job.entity_type,
        "profile": job.mapping_profile,
        "filename": job.filename,
        "total_rows": job.total_rows,
        "imported_rows": job.imported_rows,
        "failed_rows": job.failed_rows,
        "validation_report": report,
    }


@router.get("/jobs")
def list_import_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ImportJob).order_by(ImportJob.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [
            {
                "id": str(job.id),
                "entity_type": job.entity_type,
                "source_format": job.source_format,
                "mapping_profile": job.mapping_profile,
                "filename": job.filename,
                "status": job.status,
                "total_rows": job.total_rows,
                "imported_rows": job.imported_rows,
                "failed_rows": job.failed_rows,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "created_by": job.created_by.full_name if job.created_by else None,
            }
            for job in rows
        ],
    }


@router.get("/jobs/{job_id}")
def get_import_job(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    import uuid as uuid_mod

    try:
        job_uuid = uuid_mod.UUID(job_id)
    except ValueError:
        return Response(status_code=400, content="Invalid job id")
    job = db.query(ImportJob).filter(ImportJob.id == job_uuid).first()
    if job is None:
        return Response(status_code=404, content="Import job not found")
    try:
        parsed_report = json.loads(job.validation_report) if job.validation_report else []
    except json.JSONDecodeError:
        parsed_report = []
    return {
        "id": str(job.id),
        "entity_type": job.entity_type,
        "mapping_profile": job.mapping_profile,
        "source_format": job.source_format,
        "filename": job.filename,
        "status": job.status,
        "total_rows": job.total_rows,
        "imported_rows": job.imported_rows,
        "failed_rows": job.failed_rows,
        "validation_report": parsed_report,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }
