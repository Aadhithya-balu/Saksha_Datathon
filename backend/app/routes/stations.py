"""Station-level drill-down routes (issue #146, gap 128.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, require_roles
from app.database.postgres import get_db
from app.models.user import User
from app.services.station_service import station_summaries

router = APIRouter(prefix="/stations", tags=["Station Drill-down"], dependencies=[Depends(require_roles(*ALL_ROLES))])


@router.get("/summary")
def stations_summary(
    district: str | None = Query(default=None, description="Filter by district name"),
    q: str | None = Query(default=None, description="Search station name/address"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Live per-station aggregates: volume, recency, trend, risk score."""
    del current_user
    rows = station_summaries(db, district=district, q=q)
    return {
        "stations": rows,
        "count": len(rows),
        "source": "crime_cases+locations",
    }
