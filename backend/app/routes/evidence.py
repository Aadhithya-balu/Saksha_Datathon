"""Evidence CRUD and advanced routes (Upload, Assign, Timeline, Summary)."""
import uuid
import os

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_INSPECTOR, ROLE_FORENSIC, ROLE_VIEWER, require_roles
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

router = APIRouter(prefix="/evidence", tags=["Evidence"])
evidence_crud = BaseCRUDService(Evidence)

@router.get("", response_model=PaginatedResponse[EvidenceOut])
def list_evidence(
    case_id: uuid.UUID | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Evidence)
    if case_id:
        query = query.filter(Evidence.case_id == case_id)
    if status:
        query = query.filter(Evidence.status == status)
        
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
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
    timeline = db.query(EvidenceTimeline).filter(EvidenceTimeline.evidence_id == evidence_id).order_by(EvidenceTimeline.created_at.desc()).all()
    assignments = db.query(EvidenceAssignment).filter(EvidenceAssignment.evidence_id == evidence_id).order_by(EvidenceAssignment.created_at.desc()).all()
    custody = db.query(ChainOfCustody).filter(ChainOfCustody.evidence_id == evidence_id).order_by(ChainOfCustody.timestamp.desc()).all()
    ai_summaries = db.query(EvidenceAISummary).filter(EvidenceAISummary.evidence_id == evidence_id).order_by(EvidenceAISummary.created_at.desc()).all()
    
    result = EvidenceDetailOut.model_validate(evidence)
    result.metadata = EvidenceMetadataOut.model_validate(metadata) if metadata else None
    result.timeline = [EvidenceTimelineOut.model_validate(t) for t in timeline]
    result.assignments = [EvidenceAssignmentOut.model_validate(a) for a in assignments]
    result.chain_of_custody = [ChainOfCustodyOut.model_validate(c) for c in custody]
    result.ai_summaries = [EvidenceAISummaryOut.model_validate(s) for s in ai_summaries]
    
    return result

@router.post("", response_model=EvidenceOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_INSPECTOR))])
def create_evidence(payload: EvidenceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = payload.model_dump()
    data["created_by"] = current_user.full_name or current_user.username
    item = evidence_crud.create(db, data)
    
    add_timeline_event(db, item.id, "Evidence Created", current_user)
    audit_service.log_action(db, current_user, "CREATE", "Evidence", str(item.id))
    return item

@router.put("/{evidence_id}", response_model=EvidenceOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_INSPECTOR))])
def update_evidence(evidence_id: uuid.UUID, payload: EvidenceUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = evidence_crud.update(db, evidence_id, payload.model_dump(exclude_unset=True))
    add_timeline_event(db, evidence_id, "Evidence Updated", current_user)
    audit_service.log_action(db, current_user, "UPDATE", "Evidence", str(evidence_id))
    return item

@router.delete("/{evidence_id}", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def delete_evidence(evidence_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence_crud.delete(db, evidence_id)
    audit_service.log_action(db, current_user, "DELETE", "Evidence", str(evidence_id))
    return {"detail": "Evidence deleted successfully"}

@router.post("/{evidence_id}/upload", response_model=EvidenceMetadataOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_FORENSIC))])
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
    db.commit()
    db.refresh(metadata)
    
    add_timeline_event(db, evidence_id, "Evidence Uploaded", current_user, f"File {file.filename} uploaded.")
    audit_service.log_action(db, current_user, "UPLOAD", "Evidence", str(evidence_id))
    return metadata

@router.post("/{evidence_id}/assign", response_model=EvidenceAssignmentOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INSPECTOR))])
def assign_evidence(
    evidence_id: uuid.UUID, 
    assigned_to: uuid.UUID = Query(...), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    evidence = evidence_crud.get(db, evidence_id)
    
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
    return assignment

from datetime import datetime

@router.post("/{evidence_id}/assignments/{assignment_id}/accept", response_model=EvidenceAssignmentOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_FORENSIC))])
def accept_assignment(evidence_id: uuid.UUID, assignment_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence = evidence_crud.get(db, evidence_id)
    assignment = db.query(EvidenceAssignment).filter(EvidenceAssignment.id == assignment_id).first()
    if not assignment or assignment.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to accept this assignment.")
    
    assignment.status = "In Progress"
    assignment.accepted_at = datetime.utcnow()
    evidence.status = "Under Analysis"
    
    add_timeline_event(db, evidence_id, "Assignment Accepted", current_user)
    db.commit()
    db.refresh(assignment)
    return assignment

@router.post("/{evidence_id}/assignments/{assignment_id}/complete", response_model=EvidenceAssignmentOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_FORENSIC))])
def complete_assignment(evidence_id: uuid.UUID, assignment_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence = evidence_crud.get(db, evidence_id)
    assignment = db.query(EvidenceAssignment).filter(EvidenceAssignment.id == assignment_id).first()
    if not assignment or assignment.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to complete this assignment.")
    
    assignment.status = "Completed"
    assignment.completed_at = datetime.utcnow()
    evidence.status = "Analyzed"
    
    add_timeline_event(db, evidence_id, "Assignment Completed", current_user)
    db.commit()
    db.refresh(assignment)
    return assignment

@router.post("/{evidence_id}/assignments/{assignment_id}/return", response_model=EvidenceAssignmentOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_FORENSIC))])
def return_evidence(evidence_id: uuid.UUID, assignment_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evidence = evidence_crud.get(db, evidence_id)
    assignment = db.query(EvidenceAssignment).filter(EvidenceAssignment.id == assignment_id).first()
    if not assignment or assignment.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to return this evidence.")
    
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
    
    add_timeline_event(db, evidence_id, "Evidence Returned", current_user)
    db.commit()
    db.refresh(assignment)
    return assignment

@router.post("/{evidence_id}/summary", response_model=EvidenceAISummaryOut)
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
        model="mock-ai-datathon"
    )
    db.add(ai_summary)
    db.commit()
    db.refresh(ai_summary)
    
    add_timeline_event(db, evidence_id, "Summary Generated", current_user)
    return ai_summary
