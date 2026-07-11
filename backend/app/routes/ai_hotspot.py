"""
SAKSHA – Hotspot Prediction API Router

Endpoints
---------
POST /ai/hotspot/predict        – single-batch prediction
POST /ai/hotspot/predict_batch  – alias for larger payloads
GET  /ai/hotspot/model-info     – model metadata
GET  /ai/hotspot/health         – liveness check

Delegates all ML logic to app.ai.inference.hotspot.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.inference.hotspot import get_model_info, predict
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai/hotspot", tags=["Crime Hotspot Prediction"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class HotspotPredictRequest(BaseModel):
    records: list[dict[str, Any]] = Field(
        ..., min_length=1, description="Raw crime records (CaseMaster fields)."
    )


class HotspotPrediction(BaseModel):
    h3_cell: str
    year_month: str
    predicted_crime_count: float
    risk_level: str
    confidence_score: float


class HotspotPredictResponse(BaseModel):
    predictions: list[HotspotPrediction]
    total: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/predict", response_model=HotspotPredictResponse)
def hotspot_predict(
    payload: HotspotPredictRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        results = predict(payload.records)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HotspotPredictResponse(predictions=results, total=len(results))


@router.post("/predict_batch", response_model=HotspotPredictResponse)
def hotspot_predict_batch(
    payload: HotspotPredictRequest,
    current_user: User = Depends(get_current_user),
):
    """Alias of /predict – accepts larger record batches."""
    try:
        results = predict(payload.records)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HotspotPredictResponse(predictions=results, total=len(results))


@router.get("/model-info")
def hotspot_model_info(current_user: User = Depends(get_current_user)):
    try:
        return get_model_info()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/health")
def hotspot_health():
    try:
        info = get_model_info()
        return {"status": "ok", "model": info.get("model_name"), "version": info.get("version")}
    except Exception as exc:
        return {"status": "unavailable", "detail": str(exc)}
