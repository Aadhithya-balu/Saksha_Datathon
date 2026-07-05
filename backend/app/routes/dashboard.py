"""Dashboard aggregation routes — powers the SCRB overview screen."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.fir import FIR
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def summary(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    crime_query = db.query(CrimeCase)
    if date_from:
        crime_query = crime_query.filter(CrimeCase.occurred_at >= date_from)
    if date_to:
        crime_query = crime_query.filter(CrimeCase.occurred_at <= date_to)

    total_crimes = crime_query.count()
    open_crimes = crime_query.filter(CrimeCase.status == "open").count()
    total_firs = db.query(FIR).count()
    total_criminals = db.query(Criminal).count()
    resolved = crime_query.filter(CrimeCase.status == "closed").count()
    resolution_rate = round((resolved / total_crimes) * 100, 2) if total_crimes else 0.0

    return {
        "total_crimes": total_crimes,
        "open_crimes": open_crimes,
        "total_firs": total_firs,
        "total_criminals": total_criminals,
        "resolution_rate_percent": resolution_rate,
    }


@router.get("/crime-trends")
def crime_trends(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(func.date_trunc("day", CrimeCase.occurred_at).label("day"), func.count(CrimeCase.id))
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [{"date": str(day), "count": count} for day, count in rows]


@router.get("/category-breakdown")
def category_breakdown(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.crime_category import CrimeCategory

    rows = (
        db.query(CrimeCategory.name, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.category_id == CrimeCategory.id)
        .group_by(CrimeCategory.name)
        .all()
    )
    return [{"category": name, "count": count} for name, count in rows]


@router.get("/district-comparison")
def district_comparison(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.location import Location

    rows = (
        db.query(Location.district, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .group_by(Location.district)
        .all()
    )
    return [{"district": district, "count": count} for district, count in rows]
