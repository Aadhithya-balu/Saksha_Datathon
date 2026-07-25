"""Anomaly detection endpoints.

This router is intentionally minimal and only supports real-time anomaly detection
+ alert generation for incoming event batches.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, require_roles
from app.models.user import User

from app.ai.inference.anomaly import run_anomaly_inference

router = APIRouter(prefix="/ai", tags=["Crime Anomaly Detection"], dependencies=[Depends(require_roles(*ALL_ROLES))])


class AnomalyDetectRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    # Each event is a best-effort dictionary with keys consumed by feature engineering.
    # The backend will tolerate missing keys.
    events: list[dict[str, Any]] = Field(default_factory=list)
    model_path: str | None = None


class AnomalyAlertItem(BaseModel):
    event_id: str | None
    is_anomaly: bool
    score: float
    threshold: float
    explanation: dict[str, Any]


class AnomalyDetectResponse(BaseModel):
    alerts: list[AnomalyAlertItem]


@router.post(
    "/anomaly/detect",
    response_model=AnomalyDetectResponse,
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))],
)
def detect_anomalies(
    payload: AnomalyDetectRequest,
    current_user: User = Depends(get_current_user),
):
    # current_user is required for auth consistency; anomaly logic itself is payload-only.
    alerts = run_anomaly_inference(payload.events, model_path=payload.model_path)
    return AnomalyDetectResponse(alerts=alerts)
