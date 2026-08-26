"""Rule-based AI support endpoints backed by live database records."""
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, require_roles
from app.database.postgres import get_db
from app.models.user import User
from app.services.analytics_service import (
    anomalies as build_anomalies,
    hotspots as build_hotspots,
    network_person as build_network_person,
    offender_dossiers,
)

router = APIRouter(prefix="/ai", tags=["AI Integration Support"], dependencies=[Depends(require_roles(*ALL_ROLES))])


class ChatQueryRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatQueryResponse(BaseModel):
    answer: str
    data: list[dict[str, Any]] = []
    sources: list[str] = []
    chart_suggestion: str | None = None


# NOTE: /chat/query is intentionally omitted from this router — it is defined
# in app/routes/ai_chat.py which has the full investigation-chat implementation.
# Including it here would produce a duplicate-route crash at startup.

# NOTE: /predictions/risk-scores is intentionally omitted — it is defined in
# app/routes/ai_risk.py which has the dedicated district-risk implementation.


@router.get("/predictions/anomalies")
def anomalies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return build_anomalies(db)


# Note: GET /hotspots and GET /predictions/anomalies are intentionally auth-only (no role restriction)
# because they serve dashboard pages accessible to all authenticated roles.
# The role-gated AI endpoints (POST predict, etc.) are in their respective route modules.

@router.get("/hotspots")
def hotspots(
    district_id: str | None = None,
    hour: int | None = Query(default=None, ge=0, le=23, description="Hour-of-day drill-down (issue #146 gap 128.2)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return build_hotspots(db, district_id=district_id, hour=hour)


@router.get(
    "/offenders/dossiers",
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))],
)
def offenders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"offenders": offender_dossiers(db)}


@router.get(
    "/network/person/{person_id}",
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))],
)
def network_person(person_id: str, depth: int = 1, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return build_network_person(db, person_id=person_id, depth=depth)


# Issue #165: ML Model Validation & Health endpoint
@router.get(
    "/model-health",
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST))],
)
def model_health(current_user: User = Depends(get_current_user)):
    """Full ML model validation: artifact integrity, feature schema, training state, metadata consistency."""
    from app.services.model_validation_service import get_all_model_health
    return get_all_model_health()
