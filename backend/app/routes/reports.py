"""Report generation routes (async job pattern: queued -> processing -> ready)."""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, ROLE_CRIME_ANALYST, require_roles
from app.database.postgres import SessionLocal, get_db
from app.models.report import Report
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.report import ReportGenerateRequest, ReportOut
from app.services import audit_service
from app.services.base_service import BaseCRUDService

router = APIRouter(prefix="/reports", tags=["Reports"])
report_crud = BaseCRUDService(Report)


def _run_report_job(report_id: uuid.UUID) -> None:
    """
    Background job simulating report generation.
    Replace the body with real PDF/Excel rendering (e.g. WeasyPrint / openpyxl).
    """
    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return
        report.status = "processing"
        db.add(report)
        db.commit()

        # --- placeholder generation step ---
        report.file_url = f"/generated-reports/{report_id}.{report.format}"
        report.status = "ready"
        db.add(report)
        db.commit()
    finally:
        db.close()


@router.get("", response_model=PaginatedResponse[ReportOut])
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return report_crud.list(db, page=page, page_size=page_size)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return report_crud.get(db, report_id)


@router.post("/generate", response_model=ReportOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST))])
def generate_report(
    payload: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = report_crud.create(db, {**payload.model_dump(), "requested_by_id": current_user.id, "status": "queued"})
    audit_service.log_action(db, current_user, "CREATE", "Report", str(report.id))
    background_tasks.add_task(_run_report_job, report.id)
    return report
