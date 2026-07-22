"""Live reporting routes with paginated data, PDF export, and CSV export."""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Query as SQLAlchemyQuery
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INSPECTOR, ROLE_INVESTIGATOR, ROLE_POLICYMAKER, require_roles
from app.database.postgres import get_db
from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.evidence import Evidence
from app.models.fir import FIR
from app.models.officer import Officer
from app.models.report import Report
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.report import ReportOut
from app.services import audit_service

router = APIRouter(prefix="/reports", tags=["Reports"], dependencies=[Depends(require_roles(
    ROLE_ADMIN,
    ROLE_CRIME_ANALYST,
    ROLE_INVESTIGATOR,
    ROLE_INSPECTOR,
    ROLE_POLICYMAKER,
))])

REPORT_TYPES = {"cases", "officers", "criminals", "evidence"}
EXPORT_FORMATS = {"pdf", "csv"}
SORTABLE_COLUMNS: dict[str, dict[str, Any]] = {
    "cases": {
        "case_number": CrimeCase.case_number,
        "occurred_at": CrimeCase.occurred_at,
        "reported_at": CrimeCase.reported_at,
        "status": CrimeCase.status,
        "priority": CrimeCase.priority,
        "created_at": CrimeCase.created_at,
    },
    "officers": {
        "name": Officer.name,
        "badge_number": Officer.badge_number,
        "district": Officer.district,
        "station": Officer.station,
        "status": Officer.status,
        "created_at": Officer.created_at,
    },
    "criminals": {
        "full_name": Criminal.full_name,
        "status": Criminal.status,
        "gender": Criminal.gender,
        "created_at": Criminal.created_at,
    },
    "evidence": {
        "title": Evidence.title,
        "evidence_type": Evidence.evidence_type,
        "status": Evidence.status,
        "created_at": Evidence.created_at,
    },
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _serialize_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return _clean_text(value)


def _apply_date_range(query: SQLAlchemyQuery, column: Any, date_from: datetime | None, date_to: datetime | None):
    if date_from:
        query = query.filter(column >= date_from)
    if date_to:
        query = query.filter(column <= date_to)
    return query


def _apply_sort(query: SQLAlchemyQuery, report_type: str, sort_by: str, sort_order: str):
    column = SORTABLE_COLUMNS[report_type].get(sort_by)
    if column is None:
        column = SORTABLE_COLUMNS[report_type]["created_at"]
    direction = asc if sort_order == "asc" else desc
    return query.order_by(direction(column))


def _report_query(
    db: Session,
    report_type: str,
    search: str | None,
    status: str | None,
    district: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    sort_by: str,
    sort_order: str,
) -> tuple[SQLAlchemyQuery, list[str], Callable[[Any], dict[str, Any]]]:
    if report_type == "cases":
        query = db.query(CrimeCase).options(joinedload(CrimeCase.assigned_officer))
        if search:
            query = query.filter(or_(CrimeCase.case_number.ilike(f"%{search}%"), CrimeCase.description.ilike(f"%{search}%")))
        if status:
            query = query.filter(CrimeCase.status == status)
        if district:
            query = query.join(Officer, CrimeCase.assigned_officer_id == Officer.id, isouter=True).filter(Officer.district == district)
        query = _apply_date_range(query, CrimeCase.occurred_at, date_from, date_to)
        headers = ["case_number", "status", "priority", "occurred_at", "reported_at", "assigned_officer", "description"]
        mapper = lambda item: {
            "case_number": item.case_number,
            "status": item.status,
            "priority": item.priority,
            "occurred_at": _serialize_datetime(item.occurred_at),
            "reported_at": _serialize_datetime(item.reported_at),
            "assigned_officer": item.assigned_officer.name if item.assigned_officer else "",
            "description": item.description,
        }
    elif report_type == "officers":
        query = db.query(Officer)
        if search:
            query = query.filter(or_(Officer.name.ilike(f"%{search}%"), Officer.badge_number.ilike(f"%{search}%"), Officer.email.ilike(f"%{search}%")))
        if status:
            query = query.filter(Officer.status == status)
        if district:
            query = query.filter(Officer.district == district)
        headers = ["badge_number", "name", "rank", "designation", "district", "station", "status", "email"]
        mapper = lambda item: {
            "badge_number": item.badge_number,
            "name": item.name,
            "rank": item.rank,
            "designation": item.designation,
            "district": item.district,
            "station": item.station,
            "status": item.status,
            "email": item.email,
        }
    elif report_type == "criminals":
        query = db.query(Criminal)
        if search:
            query = query.filter(or_(Criminal.full_name.ilike(f"%{search}%"), Criminal.aliases.ilike(f"%{search}%"), Criminal.mo_summary.ilike(f"%{search}%")))
        if status:
            query = query.filter(Criminal.status == status)
        headers = ["full_name", "aliases", "gender", "date_of_birth", "status", "address", "mo_summary"]
        mapper = lambda item: {
            "full_name": item.full_name,
            "aliases": item.aliases,
            "gender": item.gender,
            "date_of_birth": _serialize_datetime(item.date_of_birth),
            "status": item.status,
            "address": item.address,
            "mo_summary": item.mo_summary,
        }
    else:
        query = db.query(Evidence).options(joinedload(Evidence.crime_case), joinedload(Evidence.assignee))
        if search:
            query = query.filter(or_(Evidence.title.ilike(f"%{search}%"), Evidence.description.ilike(f"%{search}%"), Evidence.evidence_type.ilike(f"%{search}%")))
        if status:
            query = query.filter(Evidence.status == status)
        query = _apply_date_range(query, Evidence.created_at, date_from, date_to)
        headers = ["title", "case_number", "evidence_type", "status", "assigned_to", "created_by", "created_at", "description"]
        mapper = lambda item: {
            "title": item.title,
            "case_number": item.crime_case.case_number if item.crime_case else "",
            "evidence_type": item.evidence_type,
            "status": item.status,
            "assigned_to": item.assignee.full_name if item.assignee else "",
            "created_by": item.created_by,
            "created_at": _serialize_datetime(item.created_at),
            "description": item.description,
        }
    return _apply_sort(query, report_type, sort_by, sort_order), headers, mapper


def _filters_dict(**filters: Any) -> dict[str, Any]:
    return {key: _serialize_datetime(value) for key, value in filters.items() if value not in (None, "")}


def _csv_response(filename: str, headers: list[str], rows: list[dict[str, Any]]) -> Response:
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({header: _clean_text(row.get(header)) for header in headers})
    return Response(
        content=buffer.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _simple_pdf(title: str, filters: dict[str, Any], headers: list[str], rows: list[dict[str, Any]]) -> bytes:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pages: list[list[str]] = []
    current = [
        "SAKSHA Police Investigation Platform",
        title,
        f"Generated: {generated}",
        "Applied filters: " + (", ".join(f"{k}={v}" for k, v in filters.items()) or "None"),
        "",
        " | ".join(headers),
    ]
    for row in rows:
        line = " | ".join(_clean_text(row.get(header))[:34] for header in headers)
        current.append(line)
        if len(current) >= 36:
            pages.append(current)
            current = ["SAKSHA Police Investigation Platform", title, f"Generated: {generated}", "", " | ".join(headers)]
    pages.append(current)

    objects: list[str] = []
    page_refs: list[int] = []
    font_obj = 3
    for page_no, lines in enumerate(pages, start=1):
        text_ops = ["BT", "/F1 9 Tf", "50 792 Td", "14 TL"]
        for index, line in enumerate(lines):
            safe = _pdf_escape(line)
            text_ops.append(f"({safe}) Tj" if index == 0 else f"T* ({safe}) Tj")
        text_ops.extend([f"50 36 Td (Page {page_no} of {len(pages)} | Confidential law-enforcement report) Tj", "ET"])
        stream = "\n".join(text_ops)
        content_obj = len(objects) + 4
        page_obj = content_obj + 1
        objects.append(f"{content_obj} 0 obj\n<< /Length {len(stream.encode('utf-8'))} >>\nstream\n{stream}\nendstream\nendobj\n")
        objects.append(f"{page_obj} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 {font_obj} 0 R >> >> /Contents {content_obj} 0 R >>\nendobj\n")
        page_refs.append(page_obj)

    body_objects = [
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        f"2 0 obj\n<< /Type /Pages /Kids [{' '.join(f'{ref} 0 R' for ref in page_refs)}] /Count {len(page_refs)} >>\nendobj\n",
        "3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        *objects,
    ]
    pdf = "%PDF-1.4\n"
    offsets = [0]
    for obj in body_objects:
        offsets.append(len(pdf.encode("utf-8")))
        pdf += obj
    xref_offset = len(pdf.encode("utf-8"))
    pdf += f"xref\n0 {len(body_objects) + 1}\n0000000000 65535 f \n"
    pdf += "".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
    pdf += f"trailer\n<< /Size {len(body_objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF"
    return pdf.encode("utf-8")


def _create_report_record(db: Session, current_user: User, report_type: str, export_format: str, filters: dict[str, Any]) -> Report:
    report = Report(
        template=f"{report_type}_report",
        requested_by_id=current_user.id,
        district=filters.get("district"),
        date_from=filters.get("date_from") or None,
        date_to=filters.get("date_to") or None,
        format=export_format,
        status="ready",
        file_url=f"/api/v1/reports/{report_type}/export/{export_format}",
    )
    db.add(report)
    db.flush()
    return report


@router.get("", response_model=PaginatedResponse[ReportOut])
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Report).order_by(desc(Report.created_at))
    total = query.count()
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=query.offset((page - 1) * page_size).limit(page_size).all())


@router.get("/statistics/summary")
def report_statistics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {
        "cases": db.query(func.count(CrimeCase.id)).scalar() or 0,
        "officers": db.query(func.count(Officer.id)).scalar() or 0,
        "criminals": db.query(func.count(Criminal.id)).scalar() or 0,
        "evidence": db.query(func.count(Evidence.id)).scalar() or 0,
    }


@router.get("/{report_type}")
def preview_report(
    report_type: str,
    search: str | None = None,
    status: str | None = None,
    district: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str = "created_at",
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if report_type not in REPORT_TYPES:
        return Response(status_code=404, content="Unknown report type")
    query, headers, mapper = _report_query(db, report_type, search, status, district, date_from, date_to, sort_by, sort_order)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "report_type": report_type,
        "headers": headers,
        "filters": _filters_dict(search=search, status=status, district=district, date_from=date_from, date_to=date_to, sort_by=sort_by, sort_order=sort_order),
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [mapper(item) for item in items],
    }


@router.post("/{report_type}/generate")
def generate_report(
    report_type: str,
    request: Request,
    export_format: str = Query("pdf", pattern="^(pdf|csv)$"),
    search: str | None = None,
    status: str | None = None,
    district: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if report_type not in REPORT_TYPES:
        return Response(status_code=404, content="Unknown report type")
    filters = _filters_dict(search=search, status=status, district=district, date_from=date_from, date_to=date_to)
    report = _create_report_record(db, current_user, report_type, export_format, {"district": district, "date_from": date_from, "date_to": date_to})
    audit_service.log_action(db, current_user, "REPORT_GENERATE", "Report", str(report.id), details=str(filters), ip_address=request.client.host if request.client else None)
    db.commit()
    db.refresh(report)
    return {"id": str(report.id), "status": report.status, "format": report.format, "file_url": report.file_url}


@router.get("/{report_type}/export/{export_format}")
def export_report(
    report_type: str,
    export_format: str,
    request: Request,
    search: str | None = None,
    status: str | None = None,
    district: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str = "created_at",
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if report_type not in REPORT_TYPES or export_format not in EXPORT_FORMATS:
        return Response(status_code=404, content="Unknown export")
    query, headers, mapper = _report_query(db, report_type, search, status, district, date_from, date_to, sort_by, sort_order)
    rows = [mapper(item) for item in query.limit(5000).all()]
    filters = _filters_dict(search=search, status=status, district=district, date_from=date_from, date_to=date_to, sort_by=sort_by, sort_order=sort_order)
    report = _create_report_record(db, current_user, report_type, export_format, {"district": district, "date_from": date_from, "date_to": date_to})
    audit_service.log_action(db, current_user, "REPORT_EXPORT", "Report", str(report.id), details=f"{export_format}:{filters}", ip_address=request.client.host if request.client else None)
    db.commit()
    filename = f"saksha_{report_type}_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    if export_format == "csv":
        return _csv_response(filename, headers, rows)
    pdf = _simple_pdf(f"{report_type.title()} Report", filters, headers, rows)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'})
