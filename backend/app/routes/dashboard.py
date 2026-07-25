"""Dashboard aggregation routes backed by the crime database."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.user import User
from app.services.dashboard import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def summary(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    district: str | None = None,
    category_id: str | None = None,
    officer_id: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return dashboard_service.get_filtered_summary(
        db,
        date_from=date_from,
        date_to=date_to,
        district=district,
        category_id=category_id,
        officer_id=officer_id,
        priority=priority,
        status=status,
    )


@router.get("/crime-trends")
def crime_trends(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    district: str | None = None,
    category_id: str | None = None,
    officer_id: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return dashboard_service.get_filtered_trends(
        db,
        date_from=date_from,
        date_to=date_to,
        district=district,
        category_id=category_id,
        officer_id=officer_id,
        priority=priority,
        status=status,
    )


@router.get("/category-breakdown")
def category_breakdown(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    district: str | None = None,
    category_id: str | None = None,
    officer_id: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return dashboard_service.get_filtered_category_breakdown(
        db,
        date_from=date_from,
        date_to=date_to,
        district=district,
        category_id=category_id,
        officer_id=officer_id,
        priority=priority,
        status=status,
    )


@router.get("/district-comparison")
def district_comparison(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    district: str | None = None,
    category_id: str | None = None,
    officer_id: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return dashboard_service.get_filtered_district_comparison(
        db,
        date_from=date_from,
        date_to=date_to,
        district=district,
        category_id=category_id,
        officer_id=officer_id,
        priority=priority,
        status=status,
    )


@router.get("/officer-stats")
def officer_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return dashboard_service.get_officer_stats(db)


@router.get("/evidence-stats")
def evidence_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return dashboard_service.get_evidence_stats(db)


@router.get("/recent-incidents")
def recent_incidents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return dashboard_service.get_recent_incidents(db)


@router.get("/forecast")
def forecast(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return dashboard_service.get_forecast_data(db)


@router.get("/risk-prediction")
def risk_prediction(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return dashboard_service.get_risk_prediction(db)


@router.get("/season-breakdown")
def season_breakdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return dashboard_service.get_season_breakdown(db)

