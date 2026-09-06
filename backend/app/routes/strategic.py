"""Strategic Intelligence routes — high-level intelligence briefing endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, require_roles
from app.database.postgres import get_db
from app.services import strategic_service
from app.services.ttl_cache import ttl_cached

router = APIRouter(prefix="/strategic", tags=["Strategic Intelligence"], dependencies=[Depends(require_roles(*ALL_ROLES))])

# Strategic aggregations are expensive and polled by the Strategic page; cache
# them so repeated loads/polls hit memory instead of Postgres.
_STRATEGIC_TTL = 60


@router.get("/briefing")
def get_briefing(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate comprehensive strategic intelligence briefing."""
    return ttl_cached(
        "strategic:briefing",
        (),
        _STRATEGIC_TTL,
        lambda: strategic_service.get_strategic_briefing(db),
        scope=db.get_bind(),
    )


@router.get("/high-risk-districts")
def get_high_risk_districts(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return districts ranked by risk level and crime density."""
    return ttl_cached(
        "strategic:high-risk-districts",
        (),
        _STRATEGIC_TTL,
        lambda: strategic_service.get_high_risk_districts(db),
        scope=db.get_bind(),
    )


@router.get("/emerging-trends")
def get_emerging_trends(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Detect emerging crime type trends."""
    return ttl_cached(
        "strategic:emerging-trends",
        (),
        _STRATEGIC_TTL,
        lambda: strategic_service.get_emerging_crime_types(db),
        scope=db.get_bind(),
    )


@router.get("/resource-allocation")
def get_resource_allocation(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate resource allocation recommendations."""
    return ttl_cached(
        "strategic:resource-allocation",
        (),
        _STRATEGIC_TTL,
        lambda: strategic_service.get_resource_allocation(db),
        scope=db.get_bind(),
    )


@router.get("/daily-summary")
def get_daily_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate daily intelligence summary."""
    return ttl_cached(
        "strategic:daily-summary",
        (),
        _STRATEGIC_TTL,
        lambda: strategic_service.get_daily_intelligence_summary(db),
        scope=db.get_bind(),
    )
