"""Dashboard routes — aggregates from real Supabase tables."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.crime import CaseMaster
from app.models.criminal import Accused
from app.models.victim import Victim
from app.models.fir import ArrestSurrender, ChargesheetDetails
from app.models.crime_category import CaseStatusMaster, CrimeHead
from app.models.location import District as DistrictModel, Unit
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_cases = db.query(CaseMaster).count()
    total_accused = db.query(Accused).count()
    total_victims = db.query(Victim).count()
    total_arrests = db.query(ArrestSurrender).count()
    total_chargesheets = db.query(ChargesheetDetails).count()

    # closed = status where CaseStatusName contains 'Charge' or 'Court' or 'Closed'
    closed = db.query(CaseMaster).join(CaseStatusMaster).filter(
        CaseStatusMaster.CaseStatusName.in_(["Chargesheeted", "Court Trial", "Convicted", "Closed"])
    ).count()
    resolution_rate = round((closed / total_cases) * 100, 2) if total_cases else 0.0

    return {
        "total_crimes": total_cases,
        "open_crimes": total_cases - closed,
        "total_firs": total_cases,
        "total_criminals": total_accused,
        "total_victims": total_victims,
        "total_arrests": total_arrests,
        "total_chargesheets": total_chargesheets,
        "resolution_rate_percent": resolution_rate,
    }


@router.get("/crime-trends")
def crime_trends(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(
            func.date_trunc("month", CaseMaster.CrimeRegisteredDate).label("month"),
            func.count(CaseMaster.CaseMasterID),
        )
        .group_by("month")
        .order_by("month")
        .all()
    )
    return [{"date": str(month)[:10], "count": count} for month, count in rows]


@router.get("/category-breakdown")
def category_breakdown(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(CrimeHead.CrimeGroupName, func.count(CaseMaster.CaseMasterID))
        .join(CaseMaster, CaseMaster.CrimeMajorHeadID == CrimeHead.CrimeHeadID)
        .group_by(CrimeHead.CrimeGroupName)
        .order_by(func.count(CaseMaster.CaseMasterID).desc())
        .all()
    )
    return [{"category": name, "count": count} for name, count in rows]


@router.get("/district-comparison")
def district_comparison(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.location import Unit
    rows = (
        db.query(DistrictModel.DistrictName, func.count(CaseMaster.CaseMasterID))
        .join(Unit, Unit.DistrictID == DistrictModel.DistrictID)
        .join(CaseMaster, CaseMaster.PoliceStationID == Unit.UnitID)
        .group_by(DistrictModel.DistrictName)
        .order_by(func.count(CaseMaster.CaseMasterID).desc())
        .all()
    )
    return [{"district": name, "count": count} for name, count in rows]


@router.get("/status-breakdown")
def status_breakdown(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(CaseStatusMaster.CaseStatusName, func.count(CaseMaster.CaseMasterID))
        .join(CaseMaster, CaseMaster.CaseStatusID == CaseStatusMaster.CaseStatusID)
        .group_by(CaseStatusMaster.CaseStatusName)
        .order_by(func.count(CaseMaster.CaseMasterID).desc())
        .all()
    )
    return [{"status": name, "count": count} for name, count in rows]
