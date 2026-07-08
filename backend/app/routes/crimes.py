"""Crime/Case routes — queries real CaseMaster table."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.crime import CaseMaster
from app.models.user import User

router = APIRouter(prefix="/crimes", tags=["Crimes"])


@router.get("")
def list_crimes(
    q: str | None = None,
    status_id: int | None = None,
    district_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(CaseMaster)
    if status_id:
        query = query.filter(CaseMaster.CaseStatusID == status_id)
    if district_id:
        query = query.join(CaseMaster.station).filter_by(DistrictID=district_id)
    if q:
        query = query.filter(CaseMaster.BriefFacts.ilike(f"%{q}%"))

    total = query.count()
    cases = query.order_by(CaseMaster.CrimeRegisteredDate.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total, "page": page, "page_size": page_size,
        "results": [_case_out(c) for c in cases],
    }


@router.get("/{case_id}")
def get_crime(case_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    case = db.query(CaseMaster).filter(CaseMaster.CaseMasterID == case_id).first()
    if not case:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Case not found")
    return _case_out(case)


@router.get("/{case_id}/accused")
def case_accused(case_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.criminal import Accused
    rows = db.query(Accused).filter(Accused.CaseMasterID == case_id).all()
    return [{"id": r.AccusedMasterID, "name": r.AccusedName, "age": r.AgeYear, "person_id": r.PersonID} for r in rows]


@router.get("/{case_id}/victims")
def case_victims(case_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.victim import Victim
    rows = db.query(Victim).filter(Victim.CaseMasterID == case_id).all()
    return [{"id": r.VictimMasterID, "name": r.VictimName, "age": r.AgeYear} for r in rows]


@router.get("/{case_id}/sections")
def case_sections(case_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.fir import ActSectionAssociation
    rows = db.query(ActSectionAssociation).filter(ActSectionAssociation.CaseMasterID == case_id).all()
    return [{"act": r.ActID, "section": r.SectionID} for r in rows]


def _case_out(c: CaseMaster) -> dict:
    return {
        "id": c.CaseMasterID,
        "crime_no": c.CrimeNo,
        "case_no": c.CaseNo,
        "registered_date": str(c.CrimeRegisteredDate),
        "status_id": c.CaseStatusID,
        "status": c.status.CaseStatusName if c.status else None,
        "category": c.category.LookupValue if c.category else None,
        "major_head": c.major_head.CrimeGroupName if c.major_head else None,
        "minor_head": c.minor_head.CrimeHeadName if c.minor_head else None,
        "station": c.station.UnitName if c.station else None,
        "court": c.court.CourtName if c.court else None,
        "incident_from": str(c.IncidentFromDate) if c.IncidentFromDate else None,
        "incident_to": str(c.IncidentToDate) if c.IncidentToDate else None,
        "latitude": c.latitude,
        "longitude": c.longitude,
        "brief_facts": c.BriefFacts,
    }
