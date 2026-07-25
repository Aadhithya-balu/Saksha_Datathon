"""Strategic Intelligence routes — high-level intelligence briefing endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, require_roles
from app.database.postgres import get_db
from app.services import strategic_service

router = APIRouter(prefix="/strategic", tags=["Strategic Intelligence"], dependencies=[Depends(require_roles(*ALL_ROLES))])


@router.get("/briefing")
def get_briefing(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate comprehensive strategic intelligence briefing."""
    return strategic_service.get_strategic_briefing(db)


@router.get("/high-risk-districts")
def get_high_risk_districts(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return districts ranked by risk level and crime density."""
    return strategic_service.get_high_risk_districts(db)


@router.get("/emerging-trends")
def get_emerging_trends(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Detect emerging crime type trends."""
    return strategic_service.get_emerging_crime_types(db)


@router.get("/resource-allocation")
def get_resource_allocation(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate resource allocation recommendations."""
    return strategic_service.get_resource_allocation(db)


@router.get("/daily-summary")
def get_daily_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate daily intelligence summary."""
    return strategic_service.get_daily_intelligence_summary(db)
