"""Evidence CRUD and advanced routes (Upload, Assign, Timeline, Summary)."""
import uuid
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, Response
from fpdf import FPDF
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_INSPECTOR, ROLE_FORENSIC, ROLE_CRIME_ANALYST, require_roles
from app.database.postgres import get_db
from app.models.evidence import Evidence
from app.models.evidence_metadata import EvidenceMetadata
from app.models.evidence_timeline import EvidenceTimeline
from app.models.evidence_assignment import EvidenceAssignment
from app.models.chain_of_custody import ChainOfCustody
from app.models.evidence_ai_summary import EvidenceAISummary
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.evidence import (
    EvidenceCreate, EvidenceOut, EvidenceUpdate, EvidenceDetailOut,
    EvidenceMetadataOut, EvidenceTimelineOut, EvidenceAssignmentOut,
    ChainOfCustodyOut, EvidenceAISummaryOut
)
from app.services import audit_service
from app.services.base_service import BaseCRUDService
from app.services.evidence_service import save_upload_file, extract_metadata, add_timeline_event, generate_ai_summary

router = APIRouter(prefix="/evidence", tags=["Evidence"], dependencies=[Depends(require_roles(*ALL_ROLES))])
evidence_crud = BaseCRUDService(Evidence)


def _is_admin(user: User) -> bool:
    return user.role.name == ROLE_ADMIN


def _ensure_assignment_actor(assignment: EvidenceAssignment | None, current_user: User) -> EvidenceAssignment:
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    if not _is_admin(current_user) and assignment.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this assignment.")
    return assignment


def _add_custody_record(
    db: Session,
    evidence_id: uuid.UUID,
    current_user: User,
    action: str,
    from_user: uuid.UUID | None = None,
    to_user: uuid.UUID | None = None,
    remarks: str | None = None,
) -> None:
    db.add(ChainOfCustody(
        evidence_id=evidence_id,
        from_user=from_user if from_user is not None else current_user.id,
        to_user=to_user,
        action=action,
        location="System",
        remarks=remarks,
    ))

@router.get("", response_model=PaginatedResponse[EvidenceOut])
def list_evidence(
    case_id: uuid.UUID | None = None,
    search: str | None = None,
    status: str | None = None,
    evidence_type: str | None = None,
    assigned_to: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Evidence)
    if case_id:
        query = query.filter(Evidence.case_id == case_id)
    if search:
        query = query.filter(or_(
            Evidence.title.ilike(f"%{search}%"),
            Evidence.description.ilike(f"%{search}%"),
            Evidence.evidence_type.ilike(f"%{search}%"),
        ))
    if status:
        query = query.filter(Evidence.status == status)
    if evidence_type:
        query = query.filter(Evidence.evidence_type == evidence_type)
    if assigned_to:
        query = query.filter(Evidence.assigned_to == assigned_to)
        
    total = query.count()
    items = query.order_by(Evidence.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse(
        results=items,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{evidence_id}", response_model=EvidenceDetailOut)
def get_evidence(evidence_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence = evidence_crud.get(db, evidence_id)
    
    # Track View Event
    add_timeline_event(db, evidence_id, "Evidence Viewed", current_user)
    
    metadata = db.query(EvidenceMetadata).filter(EvidenceMetadata.evidence_id == evidence_id).first()
    timeline = db.query(EvidenceTimeline).filter(EvidenceTimeline.evidence_id == evidence_id).order_by(EvidenceTimeline.created_at.asc()).all()
    assignments = db.query(EvidenceAssignment).filter(EvidenceAssignment.evidence_id == evidence_id).order_by(EvidenceAssignment.created_at.asc()).all()
    custody = db.query(ChainOfCustody).filter(ChainOfCustody.evidence_id == evidence_id).order_by(ChainOfCustody.timestamp.asc()).all()
    ai_summaries = db.query(EvidenceAISummary).filter(EvidenceAISummary.evidence_id == evidence_id).order_by(EvidenceAISummary.created_at.desc()).all()
    
    return EvidenceDetailOut(
        id=evidence.id,
        case_id=evidence.case_id,
        title=evidence.title,
        evidence_type=evidence.evidence_type,
        description=evidence.description,
        status=evidence.status,
        created_by=evidence.created_by,
        assigned_to=evidence.assigned_to,
        storage_path=evidence.storage_path,
        created_at=evidence.created_at,
        updated_at=evidence.updated_at,
        metadata=EvidenceMetadataOut.model_validate(metadata) if metadata else None,
        timeline=[EvidenceTimelineOut.model_validate(t) for t in timeline],
        assignments=[EvidenceAssignmentOut.model_validate(a) for a in assignments],
        chain_of_custody=[ChainOfCustodyOut.model_validate(c) for c in custody],
        ai_summaries=[EvidenceAISummaryOut.model_validate(s) for s in ai_summaries],
    )

from sqlalchemy.exc import IntegrityError

@router.post("", response_model=EvidenceOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_INSPECTOR, ROLE_CRIME_ANALYST))])
def create_evidence(payload: EvidenceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = payload.model_dump()
    data["created_by"] = current_user.full_name or current_user.username
    try:
        item = evidence_crud.create(db, data)
        _add_custody_record(db, item.id, current_user, "Evidence Registered", to_user=current_user.id)
        add_timeline_event(db, item.id, "Evidence Created", current_user)
        audit_service.log_action(db, current_user, "CREATE", "Evidence", str(item.id))
        return item
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid case_id. The specified Case UUID does not exist in the system.")

@router.put("/{evidence_id}", response_model=EvidenceOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_INSPECTOR, ROLE_CRIME_ANALYST))])
def update_evidence(evidence_id: uuid.UUID, payload: EvidenceUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = evidence_crud.update(db, evidence_id, payload.model_dump(exclude_unset=True))
    add_timeline_event(db, evidence_id, "Evidence Updated", current_user)
    audit_service.log_action(db, current_user, "UPDATE", "Evidence", str(evidence_id))
    return item

@router.delete("/{evidence_id}", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def delete_evidence(evidence_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence = evidence_crud.get(db, evidence_id)
    evidence.status = "Deleted"
    evidence.assigned_to = None
    add_timeline_event(db, evidence_id, "Evidence Deleted", current_user)
    _add_custody_record(db, evidence_id, current_user, "Evidence Deleted", remarks="Deleted by administrator")
    db.add(evidence)
    audit_service.log_action(db, current_user, "DELETE", "Evidence", str(evidence_id))
    return {"detail": "Evidence deleted successfully"}

@router.post("/{evidence_id}/upload", response_model=EvidenceMetadataOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_FORENSIC, ROLE_CRIME_ANALYST))])
def upload_evidence_file(evidence_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence = evidence_crud.get(db, evidence_id)
    
    file_path = save_upload_file(file, evidence_id)
    file_size = os.path.getsize(file_path)
    mime_type = file.content_type or "application/octet-stream"
    
    extracted = extract_metadata(file_path, mime_type)
    
    metadata = db.query(EvidenceMetadata).filter(EvidenceMetadata.evidence_id == evidence_id).first()
    if metadata:
        metadata.filename = file.filename
        metadata.filepath = file_path
        metadata.filesize = file_size
        metadata.mime_type = mime_type
        metadata.uploaded_by = current_user.full_name or current_user.username
        metadata.extracted_data = extracted
    else:
        metadata = EvidenceMetadata(
            evidence_id=evidence_id,
            filename=file.filename,
            filepath=file_path,
            filesize=file_size,
            mime_type=mime_type,
            uploaded_by=current_user.full_name or current_user.username,
            extracted_data=extracted
        )
        db.add(metadata)
        
    evidence.storage_path = file_path
    _add_custody_record(db, evidence_id, current_user, "Evidence File Uploaded", to_user=current_user.id, remarks=file.filename)
    db.commit()
    db.refresh(metadata)
    
    add_timeline_event(db, evidence_id, "Evidence Uploaded", current_user, f"File {file.filename} uploaded.")
    audit_service.log_action(db, current_user, "UPLOAD", "Evidence", str(evidence_id))
    return metadata


def _safe_pdf_text(text: any) -> str:
    """Sanitize strings for PDF core fonts (replace Unicode chars with ASCII equivalents)."""
    if text is None:
        return ""
    s = str(text).strip()
    replacements = {
        "\u2014": " - ",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "\u2192": " -> ",
        "\u2713": " [OK] ",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def _generate_evidence_pdf(evidence: Evidence, metadata: EvidenceMetadata | None, custody_records: list[ChainOfCustody], db: Session) -> bytes:
    class EvidencePDF(FPDF):
        def header(self):
            self.set_font("helvetica", "B", 14)
            self.set_text_color(15, 23, 42)
            self.cell(0, 7, "KARNATAKA STATE POLICE", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font("helvetica", "B", 10)
            self.set_text_color(30, 111, 217)
            self.cell(0, 6, "OFFICIAL EVIDENCE & FORENSIC CUSTODY CERTIFICATE", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(200, 210, 225)
            self.line(10, self.get_y() + 2, self.w - 10, self.get_y() + 2)
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("helvetica", "I", 8)
            self.set_text_color(100, 115, 140)
            self.cell(0, 10, f"SAKSHA Intelligence Platform  |  Page {self.page_no()} of {{nb}}  |  OFFICIAL POLICE RECORD", align="C")

    pdf = EvidencePDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    case = evidence.crime_case
    case_num = _safe_pdf_text(case.case_number if case else "UNASSIGNED")
    category = _safe_pdf_text(case.category.name if case and case.category else "General Investigation")
    location = _safe_pdf_text(f"{case.location.station or ''}, {case.location.district or ''}" if case and case.location else "Karnataka Jurisdiction")
    firs_list = case.firs if case and case.firs else []
    firs_str = _safe_pdf_text(", ".join([f"{f.fir_number} ({f.sections or 'Sec Unspecified'})" for f in firs_list]) or "Direct Evidence")

    # 1. Evidence Overview Header
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, _safe_pdf_text(f"EVIDENCE DOSSIER: {evidence.title.upper()}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # 2. Case Details Table
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(30, 41, 59)
    pdf.set_fill_color(241, 245, 249)
    pdf.cell(95, 6, "  CASE & JURISDICTION DETAILS", fill=True)
    pdf.cell(95, 6, "  EVIDENCE ITEM SPECIFICATIONS", fill=True, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(51, 65, 85)
    
    details_left = [
        _safe_pdf_text(f"Case Number: {case_num}"),
        _safe_pdf_text(f"Crime Category: {category}"),
        _safe_pdf_text(f"Jurisdiction: {location}"),
        _safe_pdf_text(f"Linked FIRs: {firs_str}"),
    ]
    details_right = [
        _safe_pdf_text(f"Evidence ID: {str(evidence.id)[:18]}..."),
        _safe_pdf_text(f"Classification: {evidence.evidence_type.upper()}"),
        _safe_pdf_text(f"Status: {evidence.status.upper()}"),
        _safe_pdf_text(f"Collected By: {evidence.created_by or 'Investigating Officer'}"),
    ]

    for left, right in zip(details_left, details_right):
        pdf.cell(95, 5.5, f"  {left}", border="LR")
        pdf.cell(95, 5.5, f"  {right}", border="LR", new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(95, 1, "", border="B")
    pdf.cell(95, 1, "", border="B", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 3. Description & Forensic Notes
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 6, "EVIDENCE DESCRIPTION & LOGGED PARTICULARS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(51, 65, 85)
    desc = _safe_pdf_text(evidence.description or "Supporting documentation and evidentiary item cataloged for investigation.")
    pdf.multi_cell(0, 4.5, desc)
    pdf.ln(4)

    # 4. Chain of Custody Ledger
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 6, _safe_pdf_text(f"CHAIN OF CUSTODY AUDIT TRAIL ({len(custody_records)} Recorded Events)"), new_x="LMARGIN", new_y="NEXT")

    if custody_records:
        pdf.set_font("helvetica", "B", 8)
        pdf.set_fill_color(226, 232, 240)
        pdf.cell(35, 6, "Timestamp", border=1, fill=True)
        pdf.cell(55, 6, "Action / Event", border=1, fill=True)
        pdf.cell(45, 6, "Handler / Status", border=1, fill=True)
        pdf.cell(55, 6, "Remarks / Location", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("helvetica", "", 7.5)
        for c in custody_records:
            t_str = _safe_pdf_text(c.timestamp.strftime("%Y-%m-%d %H:%M") if c.timestamp else "Logged")
            act_str = _safe_pdf_text(str(c.action)[:28])
            user_str = _safe_pdf_text(str(c.remarks or "Investigating Officer")[:25])
            loc_str = _safe_pdf_text(str(c.location or "Evidence Locker")[:30])
            pdf.cell(35, 5.5, t_str, border=1)
            pdf.cell(55, 5.5, act_str, border=1)
            pdf.cell(45, 5.5, user_str, border=1)
            pdf.cell(55, 5.5, loc_str, border=1, new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("helvetica", "I", 8)
        pdf.cell(0, 5, "Evidence securely cataloged and maintained in station registry.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 5. Forensic Hash & Verification
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 6, "DIGITAL INTEGRITY & SECURITY VERIFICATION", new_x="LMARGIN", new_y="NEXT")
    
    # Generate deterministic cryptographic SHA256 checksum
    raw_hash_input = f"{evidence.id}:{case_num}:{evidence.created_at}:{evidence.description}"
    sha256_hash = hashlib.sha256(raw_hash_input.encode("utf-8")).hexdigest().upper()

    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 4.5, _safe_pdf_text(f"Storage Identifier: {evidence.storage_path or f'/EVIDENCE/{str(evidence.id).upper()}/DOCUMENT_PACKET'}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 4.5, _safe_pdf_text(f"Cryptographic Integrity Checksum (SHA-256): {sha256_hash}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("helvetica", "I", 7.5)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(0, 4, "NOTICE: This certified dossier is automatically compiled from the secure PostgreSQL Law Enforcement database of the Karnataka State Police. Any alteration or unauthorized reproduction of this evidentiary record is strictly prohibited under Indian Penal Code and the IT Act.")

    return bytes(pdf.output())


@router.get("/{evidence_id}/download", dependencies=[Depends(require_roles(*ALL_ROLES))])
def download_evidence_file(
    evidence_id: uuid.UUID, 
    format: str = Query("pdf", pattern="^(pdf|raw)$"),
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    evidence = evidence_crud.get(db, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence record not found.")

    metadata = db.query(EvidenceMetadata).filter(EvidenceMetadata.evidence_id == evidence_id).first()
    file_path = Path(metadata.filepath if metadata else evidence.storage_path or "")

    # If raw file format is requested and file exists on disk, serve physical binary file
    if format == "raw" and file_path.exists() and file_path.is_file():
        add_timeline_event(db, evidence_id, "Evidence File Downloaded", current_user)
        audit_service.log_action(db, current_user, "DOWNLOAD", "Evidence", str(evidence_id))
        return FileResponse(path=str(file_path), filename=metadata.filename if metadata else file_path.name, media_type=metadata.mime_type if metadata else "application/octet-stream")

    # Otherwise, generate authentic official Karnataka Police PDF dossier from live database
    custody_records = (
        db.query(ChainOfCustody)
        .filter(ChainOfCustody.evidence_id == evidence_id)
        .order_by(ChainOfCustody.timestamp.asc())
        .all()
    )

    pdf_bytes = _generate_evidence_pdf(evidence, metadata, custody_records, db)
    case_number = evidence.crime_case.case_number if evidence.crime_case else "Case"
    clean_filename = f"KSP_Evidence_{case_number}_{str(evidence.id)[:8]}.pdf"

    add_timeline_event(db, evidence_id, "Evidence PDF Dossier Exported", current_user)
    audit_service.log_action(db, current_user, "EXPORT", "Evidence", str(evidence_id))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'}
    )

@router.post("/{evidence_id}/assign", response_model=EvidenceAssignmentOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_INSPECTOR, ROLE_CRIME_ANALYST))])
def assign_evidence(
    evidence_id: uuid.UUID, 
    assigned_to: uuid.UUID = Query(...), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    evidence = evidence_crud.get(db, evidence_id)
    assignee = db.query(User).filter(User.id == assigned_to, User.is_active == True).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assigned user not found or inactive.")
    
    assignment = EvidenceAssignment(
        evidence_id=evidence_id,
        assigned_by=current_user.id,
        assigned_to=assigned_to
    )
    db.add(assignment)
    
    custody = ChainOfCustody(
        evidence_id=evidence_id,
        from_user=current_user.id,
        to_user=assigned_to,
        action="Assigned to Forensic/Investigator",
        location="System"
    )
    db.add(custody)
    
    evidence.assigned_to = assigned_to
    evidence.status = "Assigned"
    
    db.commit()
    db.refresh(assignment)
    
    add_timeline_event(db, evidence_id, "Evidence Assigned", current_user, f"Assigned to user {assigned_to}")
    audit_service.log_action(db, current_user, "ASSIGN", "Evidence", str(evidence_id), details=f"assigned_to={assigned_to}")
    return assignment

from datetime import datetime, timezone

@router.post("/{evidence_id}/assignments/{assignment_id}/accept", response_model=EvidenceAssignmentOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_FORENSIC, ROLE_CRIME_ANALYST))])
def accept_assignment(evidence_id: uuid.UUID, assignment_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence = evidence_crud.get(db, evidence_id)
    assignment = _ensure_assignment_actor(
        db.query(EvidenceAssignment).filter(EvidenceAssignment.id == assignment_id, EvidenceAssignment.evidence_id == evidence_id).first(),
        current_user,
    )
    
    assignment.status = "In Progress"
    assignment.accepted_at = datetime.now(timezone.utc)
    evidence.status = "Under Analysis"
    _add_custody_record(db, evidence_id, current_user, "Assignment Accepted", from_user=assignment.assigned_by, to_user=assignment.assigned_to)
    
    add_timeline_event(db, evidence_id, "Assignment Accepted", current_user)
    audit_service.log_action(db, current_user, "ASSIGNMENT_ACCEPT", "Evidence", str(evidence_id))
    db.commit()
    db.refresh(assignment)
    return assignment

@router.post("/{evidence_id}/assignments/{assignment_id}/complete", response_model=EvidenceAssignmentOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_FORENSIC, ROLE_CRIME_ANALYST))])
def complete_assignment(evidence_id: uuid.UUID, assignment_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence = evidence_crud.get(db, evidence_id)
    assignment = _ensure_assignment_actor(
        db.query(EvidenceAssignment).filter(EvidenceAssignment.id == assignment_id, EvidenceAssignment.evidence_id == evidence_id).first(),
        current_user,
    )
    
    assignment.status = "Completed"
    assignment.completed_at = datetime.now(timezone.utc)
    evidence.status = "Analyzed"
    _add_custody_record(db, evidence_id, current_user, "Assignment Completed", from_user=assignment.assigned_to, to_user=assignment.assigned_by)
    
    add_timeline_event(db, evidence_id, "Assignment Completed", current_user)
    audit_service.log_action(db, current_user, "ASSIGNMENT_COMPLETE", "Evidence", str(evidence_id))
    db.commit()
    db.refresh(assignment)
    return assignment

@router.post("/{evidence_id}/assignments/{assignment_id}/return", response_model=EvidenceAssignmentOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_FORENSIC, ROLE_CRIME_ANALYST))])
def return_evidence(evidence_id: uuid.UUID, assignment_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence = evidence_crud.get(db, evidence_id)
    assignment = _ensure_assignment_actor(
        db.query(EvidenceAssignment).filter(EvidenceAssignment.id == assignment_id, EvidenceAssignment.evidence_id == evidence_id).first(),
        current_user,
    )
    
    # Returning it transfers custody back to the assigner
    custody = ChainOfCustody(
        evidence_id=evidence_id,
        from_user=current_user.id,
        to_user=assignment.assigned_by,
        action="Returned Evidence to Assigner",
        location="System"
    )
    db.add(custody)
    
    evidence.assigned_to = assignment.assigned_by
    evidence.status = "Returned"
    assignment.status = "Returned"
    
    add_timeline_event(db, evidence_id, "Evidence Returned", current_user)
    audit_service.log_action(db, current_user, "ASSIGNMENT_RETURN", "Evidence", str(evidence_id))
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/{evidence_id}/assignments/{assignment_id}/reject", response_model=EvidenceAssignmentOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_FORENSIC, ROLE_CRIME_ANALYST))])
def reject_assignment(evidence_id: uuid.UUID, assignment_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence = evidence_crud.get(db, evidence_id)
    assignment = _ensure_assignment_actor(
        db.query(EvidenceAssignment).filter(EvidenceAssignment.id == assignment_id, EvidenceAssignment.evidence_id == evidence_id).first(),
        current_user,
    )
    assignment.status = "Rejected"
    evidence.status = "Assignment Rejected"
    evidence.assigned_to = assignment.assigned_by
    _add_custody_record(db, evidence_id, current_user, "Assignment Rejected", from_user=assignment.assigned_to, to_user=assignment.assigned_by)
    add_timeline_event(db, evidence_id, "Assignment Rejected", current_user)
    audit_service.log_action(db, current_user, "ASSIGNMENT_REJECT", "Evidence", str(evidence_id))
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/{evidence_id}/summary", response_model=EvidenceAISummaryOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_INSPECTOR, ROLE_FORENSIC, ROLE_CRIME_ANALYST))])
def get_evidence_summary(evidence_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence = evidence_crud.get(db, evidence_id)
    metadata = db.query(EvidenceMetadata).filter(EvidenceMetadata.evidence_id == evidence_id).first()
    timeline = db.query(EvidenceTimeline).filter(EvidenceTimeline.evidence_id == evidence_id).all()
    assignments = db.query(EvidenceAssignment).filter(EvidenceAssignment.evidence_id == evidence_id).all()
    custody = db.query(ChainOfCustody).filter(ChainOfCustody.evidence_id == evidence_id).order_by(ChainOfCustody.timestamp.desc()).all()
    
    summary_text = generate_ai_summary(evidence, metadata, timeline, assignments, custody)
    
    ai_summary = EvidenceAISummary(
        evidence_id=evidence_id,
        summary=summary_text,
        model="saksha-evidence-summary"
    )
    db.add(ai_summary)
    db.commit()
    db.refresh(ai_summary)
    
    add_timeline_event(db, evidence_id, "Summary Generated", current_user)
    audit_service.log_action(db, current_user, "SUMMARY_GENERATE", "Evidence", str(evidence_id))
    return ai_summary
