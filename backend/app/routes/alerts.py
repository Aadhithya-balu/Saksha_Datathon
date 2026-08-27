"""Red-zone spike alert routes (issue #146, gaps 128.3/130.4).

Refactored for Issue #10 P2: routes now return structured alerts with
evidence, provenance, confidence, policy version, and human-readable
explanations.  An admin endpoint exposes the current alert policy.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_CRIME_ANALYST, require_roles
from app.core.alert_policy import get_current_policy
from app.database.postgres import get_db
from app.models.user import User
from app.services.redzone_service import (
    detect_red_zones,
    notify_red_zones,
    rank_categories,
    rank_districts,
)

router = APIRouter(prefix="/alerts", tags=["Red-Zone Alerts"], dependencies=[Depends(require_roles(*ALL_ROLES))])


# ---------------------------------------------------------------------------
# GET /alerts/policy  (admin only — must be before parameterized routes)
# ---------------------------------------------------------------------------

@router.get(
    "/policy",
    dependencies=[Depends(require_roles(ROLE_ADMIN))],
)
def alert_policy(
    current_user: User = Depends(get_current_user),
):
    """Inspect the current alert policy (admin only).

    Displays policy version, all thresholds, baseline windows,
    minimum evidence requirements, and severity rules.
    """
    del current_user
    return get_current_policy()


# ---------------------------------------------------------------------------
# GET /alerts/ranking/districts
# ---------------------------------------------------------------------------

@router.get("/ranking/districts")
def district_ranking(
    window_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Districts ranked by raw incident count in the specified window.

    Methodology: incident_count, no population normalisation,
    no severity weighting.  Documented in alert policy.
    """
    del current_user
    return {
        "metric": "incident_count",
        "window_days": window_days,
        "districts": rank_districts(db, window_days=window_days),
    }


# ---------------------------------------------------------------------------
# GET /alerts/ranking/categories
# ---------------------------------------------------------------------------

@router.get("/ranking/categories")
def category_ranking(
    window_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crime categories ranked by total incidents in the specified window.

    Includes change_percentage vs prior window as secondary metric.
    """
    del current_user
    return {
        "metric": "incident_count",
        "window_days": window_days,
        "categories": rank_categories(db, window_days=window_days),
    }


# ---------------------------------------------------------------------------
# GET /alerts/red-zones
# ---------------------------------------------------------------------------

@router.get("/red-zones")
def red_zones(
    min_current: int = Query(default=3, ge=1),
    ratio_threshold: float = Query(default=1.5, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Districts/categories spiking vs their own historical baseline.

    Returns structured alerts with evidence, provenance, confidence,
    policy version, and human-readable explanation.
    """
    del current_user
    return detect_red_zones(db, min_current=min_current, ratio_threshold=ratio_threshold)


# ---------------------------------------------------------------------------
# POST /alerts/red-zones/notify
# ---------------------------------------------------------------------------

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
    """Push detected red zones into the notification center (deduped).

    Each notification includes policy version, provenance, and confidence
    in the message body for traceability.
    """
    result = detect_red_zones(db, min_current=min_current, ratio_threshold=ratio_threshold)
    stats = notify_red_zones(db, result["red_zones"])
    return {
        "status": "ok",
        "zones_detected": len(result["red_zones"]),
        "policy_version": result["policy_version"],
        **stats,
        "broadcast_by": current_user.username,
    }


# ---------------------------------------------------------------------------
# GET /alerts/red-zones/{district}
# ---------------------------------------------------------------------------

@router.get("/red-zones/{district}")
def red_zones_for_district(
    district: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Structured red-zone alerts for a specific district."""
    del current_user
    result = detect_red_zones(db)
    zones = [z for z in result["red_zones"] if z["district"].lower() == district.lower()]
    if not zones:
        raise HTTPException(status_code=404, detail=f"No active red zones in {district}")
    return {"district": district, "policy_version": result["policy_version"], "red_zones": zones}
