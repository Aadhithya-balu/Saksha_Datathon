"""Criminal intelligence API endpoints.

Prefix: /ai/criminal
Auth:   Bearer JWT (existing get_current_user dependency)

Endpoints
---------
GET  /ai/criminal/{criminal_id}/risk            – risk score
GET  /ai/criminal/{criminal_id}/repeat-offender – repeat offence prediction
GET  /ai/criminal/{criminal_id}/similar         – similar offender search
GET  /ai/criminal/{criminal_id}/cluster         – behavioural cluster
GET  /ai/criminal/{criminal_id}/recommendations – investigation recommendations
POST /ai/criminal/retrain                       – retrain all models (admin only)
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, require_roles
from app.database.postgres import get_db
from app.models.user import User

from app.ai.inference.criminal import (
    cluster_criminal,
    find_similar_offenders,
    get_investigation_recommendations,
    predict_repeat_offender,
    retrain_models,
    score_criminal_risk,
)

router = APIRouter(prefix="/ai/criminal", tags=["Criminal Intelligence"], dependencies=[Depends(require_roles(*ALL_ROLES))])


def _check_error(result: dict[str, Any], criminal_id: str) -> None:
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Criminal '{criminal_id}': {result['error']}",
        )


@router.get("/{criminal_id}/risk", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))])
def criminal_risk(
    criminal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return risk score (0-100) and contributing factors for a criminal."""
    result = score_criminal_risk(db, criminal_id)
    _check_error(result, criminal_id)
    return result


@router.get("/{criminal_id}/repeat-offender", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))])
def repeat_offender(
    criminal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Predict whether a criminal is likely to re-offend."""
    result = predict_repeat_offender(db, criminal_id)
    _check_error(result, criminal_id)
    return result


@router.get("/{criminal_id}/similar", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))])
def similar_offenders(
    criminal_id: str,
    top_k: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the top-k most behaviourally similar criminals."""
    result = find_similar_offenders(db, criminal_id, top_k=top_k)
    _check_error(result, criminal_id)
    return result


@router.get("/{criminal_id}/cluster", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))])
def criminal_cluster(
    criminal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the behavioural cluster assignment for a criminal."""
    result = cluster_criminal(db, criminal_id)
    _check_error(result, criminal_id)
    return result


@router.get("/{criminal_id}/recommendations", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))])
def investigation_recommendations(
    criminal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return combined investigation recommendations derived from all models."""
    result = get_investigation_recommendations(db, criminal_id)
    _check_error(result, criminal_id)
    return result


@router.post(
    "/retrain",
    dependencies=[Depends(require_roles(ROLE_ADMIN))],
)
def retrain(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrain all criminal intelligence models from current database state.
    Restricted to admin role.
    """
    try:
        metrics = retrain_models(db)
        return {"status": "ok", "metrics": metrics}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
