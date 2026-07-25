"""
SAKSHA – District Risk Prediction & Forecast API Router

Endpoints
---------
GET  /ai/predictions/risk-scores   – district risk scores (frontend already calls this)
POST /ai/predictions/risk-scores   – risk scores from submitted records
POST /ai/predictions/forecast      – crime count forecast from submitted records
GET  /ai/predictions/model-info    – model metadata
GET  /ai/predictions/health        – liveness check

Delegates all ML logic to app.ai.inference.risk.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.ai.inference.risk import get_model_info, predict_forecast, predict_risk
from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, require_roles
from app.database.postgres import get_db
from app.models.crime import CrimeCase
from app.models.user import User

router = APIRouter(prefix="/ai/predictions", tags=["District Risk Prediction"], dependencies=[Depends(require_roles(*ALL_ROLES))])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RiskPredictRequest(BaseModel):
    records: list[dict[str, Any]] = Field(
        ..., min_length=1, description="Raw crime records with occurred_at, district, category."
    )


class RiskScoreItem(BaseModel):
    district: str
    year_month: str
    risk_score: float
    predicted_crime_count: float
    risk_band: str
    confidence: float
    top_factors: list[dict[str, Any]]
    resource_recommendation: str


class RiskScoresResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    district_id: str | None = None
    window: str
    model_version: str
    grid_predictions: list[dict[str, Any]]


class ForecastItem(BaseModel):
    district: str
    year_month: str
    predicted_crime_count: float
    lower_bound: float
    upper_bound: float
    trend: str


class ForecastResponse(BaseModel):
    forecasts: list[ForecastItem]
    total: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/risk-scores", response_model=RiskScoresResponse)
def get_risk_scores(
    window: str = Query(default="next_7d", description="Forecast window label"),
    district_id: str | None = Query(default=None, description="Filter by district"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return latest district risk scores based on crime records."""
    del current_user
    try:
        cases = db.query(CrimeCase).options(joinedload(CrimeCase.location), joinedload(CrimeCase.category)).all()
        if not cases:
            info = get_model_info()
            return RiskScoresResponse(
                district_id=district_id,
                window=window,
                model_version=info.get("version", "untrained"),
                grid_predictions=[],
            )
        
        records = [
            {
                "occurred_at": case.occurred_at.isoformat() if case.occurred_at else None,
                "district": case.location.district if case.location else "Unknown",
                "category": case.category.name if case.category else "Unknown",
            }
            for case in cases
        ]
        
        results = predict_risk(records)
        if district_id:
            results = [r for r in results if r["district"] == district_id]
            
        info = get_model_info()
        return RiskScoresResponse(
            district_id=district_id,
            window=window,
            model_version=info.get("version", "rule-based"),
            grid_predictions=results,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.post("/risk-scores", response_model=RiskScoresResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))])
def predict_risk_scores(
    payload: RiskPredictRequest,
    window: str = Query(default="next_7d"),
    current_user: User = Depends(get_current_user),
):
    """Compute district risk scores from submitted crime records."""
    try:
        results = predict_risk(payload.records)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    info = get_model_info()
    return RiskScoresResponse(
        district_id=None,
        window=window,
        model_version=info.get("version", "rule-based"),
        grid_predictions=results,
    )


@router.post("/forecast", response_model=ForecastResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))])
def predict_crime_forecast(
    payload: RiskPredictRequest,
    current_user: User = Depends(get_current_user),
):
    """Forecast next-month crime counts per district."""
    try:
        results = predict_forecast(payload.records)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return ForecastResponse(
        forecasts=[ForecastItem(**r) for r in results],
        total=len(results),
    )


@router.get("/model-info")
def risk_model_info(current_user: User = Depends(get_current_user)):
    try:
        return get_model_info()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/health")
def risk_health():
    try:
        info = get_model_info()
        return {
            "status": "ok",
            "risk_model": info.get("risk_model_loaded"),
            "forecast_model": info.get("forecast_model_loaded"),
            "version": info.get("version"),
        }
    except Exception as exc:
        return {"status": "unavailable", "detail": str(exc)}
