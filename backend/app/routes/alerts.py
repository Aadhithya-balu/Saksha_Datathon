"""Red-zone spike alert routes (issue #146, gaps 128.3/130.4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_CRIME_ANALYST, require_roles
from app.database.postgres import get_db
from app.models.user import User
from app.services.redzone_service import detect_red_zones, notify_red_zones

router = APIRouter(prefix="/alerts", tags=["Red-Zone Alerts"], dependencies=[Depends(require_roles(*ALL_ROLES))])


@router.get("/red-zones")
def red_zones(
    min_current: int = Query(default=3, ge=1),
    ratio_threshold: float = Query(default=1.5, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Districts/categories spiking vs their own historical baseline."""
    del current_user
    return detect_red_zones(db, min_current=min_current, ratio_threshold=ratio_threshold)


@router.post(
    "/red-zones/notify",
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST))],
)
def broadcast_red_zones(
    min_current: int = Query(default=3, ge=1),
    ratio_threshold: float = Query(default=1.5, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Push detected red zones into the notification center (deduped)."""
    result = detect_red_zones(db, min_current=min_current, ratio_threshold=ratio_threshold)
    stats = notify_red_zones(db, result["red_zones"])
    return {
        "status": "ok",
        "zones_detected": len(result["red_zones"]),
        **stats,
        "broadcast_by": current_user.username,
    }


@router.get("/red-zones/{district}")
def red_zones_for_district(
    district: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    result = detect_red_zones(db)
    zones = [z for z in result["red_zones"] if z["district"].lower() == district.lower()]
    if not zones:
        raise HTTPException(status_code=404, detail=f"No active red zones in {district}")
    return {"district": district, "red_zones": zones}
