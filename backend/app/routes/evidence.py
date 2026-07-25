"""Evidence CRUD and advanced routes (Upload, Assign, Timeline, Summary)."""
import uuid
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
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
    except IntegrityError as e:
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


@router.get("/{evidence_id}/download", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_INSPECTOR, ROLE_FORENSIC, ROLE_CRIME_ANALYST))])
def download_evidence_file(evidence_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence = evidence_crud.get(db, evidence_id)
    metadata = db.query(EvidenceMetadata).filter(EvidenceMetadata.evidence_id == evidence_id).first()
    file_path = Path(metadata.filepath if metadata else evidence.storage_path or "")
    if not metadata or not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Evidence file not found.")
    add_timeline_event(db, evidence_id, "Evidence File Downloaded", current_user)
    audit_service.log_action(db, current_user, "DOWNLOAD", "Evidence", str(evidence_id))
    return FileResponse(path=str(file_path), filename=metadata.filename, media_type=metadata.mime_type)

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
