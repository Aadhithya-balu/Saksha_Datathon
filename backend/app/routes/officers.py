"""Officers routes — queries real Employee table."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.officer import Officer
from app.models.user import User

router = APIRouter(prefix="/officers", tags=["Officers"])


@router.get("")
def list_officers(
    q: str | None = None,
    district_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Officer)
    if q:
        query = query.filter(Officer.FirstName.ilike(f"%{q}%"))
    if district_id:
        query = query.filter(Officer.DistrictID == district_id)
    total = query.count()
    results = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "results": [_out(r) for r in results],
    }


@router.get("/{officer_id}")
def get_officer(officer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(Officer).filter(Officer.EmployeeID == officer_id).first()
    if not row:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Officer not found")
    return _out(row)


def _out(r: Officer) -> dict:
    return {
        "id": r.EmployeeID,
        "kgid": r.KGID,
        "name": r.FirstName,
        "district_id": r.DistrictID,
        "district": r.district.DistrictName if r.district else None,
        "unit": r.unit.UnitName if r.unit else None,
        "rank": r.rank.RankName if r.rank else None,
        "designation": r.designation.DesignationName if r.designation else None,
        "dob": str(r.EmployeeDOB) if r.EmployeeDOB else None,
        "appointment_date": str(r.AppointmentDate) if r.AppointmentDate else None,
    }
