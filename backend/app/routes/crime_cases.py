"""API endpoints for Crime Case Management Workflow."""
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, require_roles
from app.database.postgres import get_db
from app.models.crime import CrimeCase
from app.models.fir import FIR
from app.models.officer import Officer
from app.models.location import Location
from app.models.crime_category import CrimeCategory
from app.models.investigation_note import InvestigationNote
from app.models.user import User

from app.schemas.common import PaginatedResponse
from app.schemas.crime import CrimeCaseCreate, CrimeCaseOut, CrimeCaseUpdate
from app.schemas.fir import FIROut
from app.schemas.officer import OfficerOut
from app.services import audit_service
from app.services.crime_service import crime_crud

router = APIRouter(prefix="/crime-cases", tags=["Crime Case Management"], dependencies=[Depends(require_roles(*ALL_ROLES))])


# --- Schemas ---

class InvestigationNoteCreate(BaseModel):
    content: str


class InvestigationNoteOut(BaseModel):
    id: uuid.UUID
    officer_name: str
    officer_badge: str
    created_at: datetime
    content: str


class TimelineEventOut(BaseModel):
    timestamp: datetime
    event: str
    actor: str | None = None


class AIRecommendationOut(BaseModel):
    type: str
    title: str
    description: str


class CrimeCaseDetailOut(CrimeCaseOut):
    priority: str
    progress: int
    assigned_officer_id: uuid.UUID | None
    assigned_officer: Any | None = None
    notes: list[InvestigationNoteOut]
    timeline: list[TimelineEventOut]
    firs: list[FIROut]
    ai_recommendations: list[AIRecommendationOut]


class LinkFIRsPayload(BaseModel):
    fir_ids: list[uuid.UUID]


class OfficerWithUserOut(OfficerOut):
    full_name: str


class CrimeCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    section_code: str | None = None
    severity: str | None = None


class LocationSimpleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    district: str
    station: str
    pincode: str | None = None


# --- Endpoints ---

@router.get("", response_model=PaginatedResponse[CrimeCaseDetailOut])
def list_cases(
    q: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List crime cases from PostgreSQL with complete detail attributes."""
    query = db.query(CrimeCase)
    if status:
        query = query.filter(CrimeCase.status == status)
    if q:
        query = query.filter(CrimeCase.description.ilike(f"%{q}%"))

    total = query.count()
    results = query.offset((page - 1) * page_size).limit(page_size).all()

    extended_results = []
    for case in results:
        priority = case.priority or "medium"
        progress = case.progress if case.progress is not None else 10
        assigned_officer_id = case.assigned_officer_id
        assigned_officer = None
        if case.assigned_officer:
            assigned_officer = {
                "id": case.assigned_officer.id,
                "badge_number": case.assigned_officer.badge_number,
                "rank": case.assigned_officer.rank,
                "district": case.assigned_officer.district,
                "station": case.assigned_officer.station,
                "full_name": case.assigned_officer.user.full_name if case.assigned_officer.user else case.assigned_officer.name
            }

        # Query investigation notes for case
        notes_db = db.query(InvestigationNote).filter(InvestigationNote.case_id == case.id).order_by(InvestigationNote.created_at.desc()).all()
        notes_out = [
            InvestigationNoteOut(
                id=n.id,
                officer_name=n.officer_name,
                officer_badge=n.officer_badge,
                created_at=n.created_at,
                content=n.content
            )
            for n in notes_db
        ]

        extended_results.append(
            CrimeCaseDetailOut(
                id=case.id,
                case_number=case.case_number,
                category_id=case.category_id,
                location_id=case.location_id,
                occurred_at=case.occurred_at,
                reported_at=case.reported_at,
                description=case.description,
                mo_tags=case.mo_tags,
                status=case.status,
                created_at=case.created_at,
                priority=priority,
                progress=progress,
                assigned_officer_id=assigned_officer_id,
                assigned_officer=assigned_officer,
                notes=notes_out,
                timeline=[],
                firs=[],
                ai_recommendations=[]
            )
        )

    return PaginatedResponse(total=total, page=page, page_size=page_size, results=extended_results)


# --- Static Routes (Must be declared before parameterized /{case_id} route to avoid validation conflict) ---

@router.get("/unassigned-officers", response_model=list[OfficerWithUserOut])
def list_unassigned_officers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all officer profiles with full names for assignment dropdowns."""
    officers = db.query(Officer).join(User).all()
    results = []
    for off in officers:
        results.append(
            OfficerWithUserOut(
                id=off.id,
                user_id=off.user_id,
                badge_number=off.badge_number,
                rank=off.rank,
                district=off.district,
                station=off.station,
                created_at=off.created_at,
                full_name=off.user.full_name,
                name=off.name
            )
        )
    return results


@router.get("/unlinked-firs", response_model=list[FIROut])
def list_unlinked_firs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all FIRs so they can be selected for linking to cases."""
    firs = db.query(FIR).all()
    return [FIROut.model_validate(fir) for fir in firs]


@router.get("/categories", response_model=list[CrimeCategoryOut])
def list_crime_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return list of all categories."""
    categories = db.query(CrimeCategory).all()
    return [CrimeCategoryOut.model_validate(c) for c in categories]


@router.get("/locations", response_model=list[LocationSimpleOut])
def list_locations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return list of all locations."""
    locations = db.query(Location).all()
    return [LocationSimpleOut.model_validate(loc) for loc in locations]


# --- Parameterized Routes ---

@router.get("/{case_id}", response_model=CrimeCaseDetailOut)
def get_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full details of a crime case, including linked FIRs, timeline and persisted investigation notes."""
    case = crime_crud.get(db, case_id)

    # 1. Fetch linked FIRs from existing table
    firs_list = db.query(FIR).filter(FIR.crime_case_id == case.id).all()
    firs_out = [FIROut.model_validate(fir) for fir in firs_list]

    # 2. Build timeline from report date + linked FIR registrations + investigation notes
    timeline = [
        TimelineEventOut(timestamp=case.reported_at, event="Case Created", actor=None)
    ]
    for fir in firs_list:
        timeline.append(
            TimelineEventOut(
                timestamp=fir.filed_at,
                event=f"FIR {fir.fir_number} Linked",
                actor=fir.complainant_name
            )
        )

    # Query notes from PostgreSQL investigation_notes table
    notes_db = db.query(InvestigationNote).filter(InvestigationNote.case_id == case.id).order_by(InvestigationNote.created_at.desc()).all()
    for note in notes_db:
        timeline.append(
            TimelineEventOut(
                timestamp=note.created_at,
                event="Investigation Note Added",
                actor=note.officer_name
            )
        )

    timeline = sorted(timeline, key=lambda e: e.timestamp)

    notes_out = [
        InvestigationNoteOut(
            id=n.id,
            officer_name=n.officer_name,
            officer_badge=n.officer_badge,
            created_at=n.created_at,
            content=n.content
        )
        for n in notes_db
    ]

    # 3. AI Recommendations
    ai_recommendations = [
        AIRecommendationOut(
            type="crime_pattern",
            title="Similar Nearby Incident",
            description="A house break-in was reported 1.2km away with similar MO (lock-break during early hours)."
        ),
        AIRecommendationOut(
            type="suspect",
            title="Possible Repeat Offender",
            description="Prior offender Ramu 'Kodaikanal' Swamy has active modus operandi pattern match in this sector."
        ),
        AIRecommendationOut(
            type="evidence",
            title="Suggested Evidence Checklist",
            description="Establish custody of CCTV footage from entry corridors and run fingerprint matching."
        ),
        AIRecommendationOut(
            type="legal",
            title="Recommended Sections",
            description="Review applicability of BNS Section 305 (Theft) and BNS Section 331 (House-trespass)."
        )
    ]

    priority = case.priority or "medium"
    progress = case.progress if case.progress is not None else 10
    assigned_officer_id = case.assigned_officer_id
    assigned_officer = None
    if case.assigned_officer:
        assigned_officer = {
            "id": case.assigned_officer.id,
            "badge_number": case.assigned_officer.badge_number,
            "rank": case.assigned_officer.rank,
            "district": case.assigned_officer.district,
            "station": case.assigned_officer.station,
            "full_name": case.assigned_officer.user.full_name if case.assigned_officer.user else case.assigned_officer.name
        }

    return CrimeCaseDetailOut(
        id=case.id,
        case_number=case.case_number,
        category_id=case.category_id,
        location_id=case.location_id,
        occurred_at=case.occurred_at,
        reported_at=case.reported_at,
        description=case.description,
        mo_tags=case.mo_tags,
        status=case.status,
        created_at=case.created_at,
        priority=priority,
        progress=progress,
        assigned_officer_id=assigned_officer_id,
        assigned_officer=assigned_officer,
        notes=notes_out,
        timeline=timeline,
        firs=firs_out,
        ai_recommendations=ai_recommendations
    )


@router.post("", response_model=CrimeCaseOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_CRIME_ANALYST))])
def create_case(
    payload: CrimeCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new crime case in PostgreSQL."""
    case = crime_crud.create(db, payload.model_dump())
    audit_service.log_action(db, current_user, "CREATE", "CrimeCase", str(case.id))
    return case


@router.put("/{case_id}", response_model=CrimeCaseOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_CRIME_ANALYST))])
def update_case(
    case_id: uuid.UUID,
    payload: CrimeCaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a crime case with priority, progress, status, and assigned officer."""
    case = crime_crud.update(db, case_id, payload.model_dump(exclude_unset=True))
    audit_service.log_action(db, current_user, "UPDATE", "CrimeCase", str(case_id))
    return case


@router.delete("/{case_id}", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def delete_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a crime case."""
    crime_crud.delete(db, case_id)
    audit_service.log_action(db, current_user, "DELETE", "CrimeCase", str(case_id))
    return {"message": "Crime case deleted successfully"}


@router.post("/{case_id}/notes", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def add_case_note(
    case_id: uuid.UUID,
    payload: InvestigationNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add and persist an investigation note in PostgreSQL."""
    # Verify case exists
    crime_crud.get(db, case_id)

    # Check if officer record exists for current_user
    officer = db.query(Officer).filter(Officer.user_id == current_user.id).first()
    officer_id = officer.id if officer else None
    officer_name = current_user.full_name or current_user.username
    officer_badge = officer.badge_number if officer else current_user.username

    note = InvestigationNote(
        case_id=case_id,
        officer_id=officer_id,
        officer_name=officer_name,
        officer_badge=officer_badge,
        content=payload.content
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    audit_service.log_action(
        db, current_user, "CREATE", "InvestigationNote", f"Note added to case {case_id}"
    )
    return {"message": "Investigation note added successfully", "id": str(note.id), "content": note.content}


@router.delete("/{case_id}/notes/{note_id}", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def delete_case_note(
    case_id: uuid.UUID,
    note_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an investigation note from PostgreSQL."""
    note = db.query(InvestigationNote).filter(
        InvestigationNote.id == note_id,
        InvestigationNote.case_id == case_id
    ).first()

    if not note:
        raise HTTPException(status_code=404, detail="Investigation note not found")

    db.delete(note)
    db.commit()

    audit_service.log_action(
        db, current_user, "DELETE", "InvestigationNote", f"Note {note_id} deleted"
    )
    return {"message": "Investigation note deleted successfully"}



@router.post("/{case_id}/link-firs", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def link_firs_to_case(
    case_id: uuid.UUID,
    payload: LinkFIRsPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Link multiple FIRs to a crime case using the existing 'crime_case_id' column relationship.
    """
    # Verify case exists
    crime_crud.get(db, case_id)

    for fir_id in payload.fir_ids:
        fir = db.query(FIR).filter(FIR.id == fir_id).first()
        if fir:
            fir.crime_case_id = case_id
    db.commit()

    audit_service.log_action(
        db, current_user, "UPDATE", "CrimeCase", f"Linked {len(payload.fir_ids)} FIRs to case {case_id}"
    )
    return {"message": f"Successfully linked {len(payload.fir_ids)} FIRs"}
