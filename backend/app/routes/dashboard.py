"""Dashboard aggregation routes backed by the crime database."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.user import User
from app.services.analytics_service import (
    category_breakdown as build_category_breakdown,
    crime_trends as build_crime_trends,
    dashboard_summary,
    district_comparison as build_district_comparison,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def summary(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return dashboard_summary(db, date_from, date_to)


@router.get("/crime-trends")
def crime_trends(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return build_crime_trends(db)


@router.get("/category-breakdown")
def category_breakdown(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return build_category_breakdown(db)


@router.get("/district-comparison")
def district_comparison(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return build_district_comparison(db)
