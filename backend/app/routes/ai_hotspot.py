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
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, require_roles
from app.models.user import User

router = APIRouter(prefix="/ai/hotspot", tags=["Crime Hotspot Prediction"], dependencies=[Depends(require_roles(*ALL_ROLES))])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class HotspotPredictRequest(BaseModel):
    records: list[dict[str, Any]] = Field(
        ..., min_length=1, description="Raw crime records (CaseMaster fields)."
    )
    default_hour: int | None = Field(
        default=None,
        ge=0,
        le=23,
        description=(
            "Hour-of-day drill-down (issue #146 gap 131.2): records with a blank "
            "IncidentFromDate are stamped with today's date at this hour before "
            "feature building, so predictions answer 'what happens at 22:00?'."
        ),
    )


class HotspotPrediction(BaseModel):
    h3_cell: str
    year_month: str
    predicted_crime_count: float
    risk_level: str
    confidence_score: float
    prediction_mode: str | None = "ML"


class HotspotPredictResponse(BaseModel):
    predictions: list[HotspotPrediction]
    total: int
    # Issue 8 §12: honest inference provenance — "ML" only when a trained
    # artifact is loaded, "FALLBACK" when rule-based heuristics were used.
    prediction_mode: str = "UNKNOWN"
    model_version: str | None = None
    prediction_mode: str = "ML"
    model_version: str | None = None
    validation_status: str | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def _apply_default_hour(records: list[dict[str, Any]], default_hour: int | None) -> list[dict[str, Any]]:
    """Stamp blank IncidentFromDate values with today's date at ``default_hour``."""
    if default_hour is None:
        return records
    from datetime import datetime

    stamped = [dict(record) for record in records]
    for record in stamped:
        raw = record.get("IncidentFromDate")
        if not raw or not str(raw).strip():
            record["IncidentFromDate"] = datetime.now().replace(
                hour=default_hour, minute=0, second=0, microsecond=0
            ).isoformat()
    return stamped


def _response_with_mode(predictions: list[dict]) -> HotspotPredictResponse:
    info = get_model_info()
    return HotspotPredictResponse(
        predictions=predictions,
        total=len(predictions),
        prediction_mode="ML" if info.get("model_loaded") else "FALLBACK",
        model_version=info.get("version"),
    )


@router.post("/predict", response_model=HotspotPredictResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))])
def hotspot_predict(
    payload: HotspotPredictRequest,
    current_user: User = Depends(get_current_user),
):
    from app.ai.inference.refresh import maybe_refresh_async

    maybe_refresh_async("hotspot", reason="inference")
    try:
        results = predict(_apply_default_hour(payload.records, payload.default_hour))
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Hotspot prediction failed. Ensure records contain required fields.")
    return _response_with_mode(results)
    
    info = get_model_info()
    pred_mode = results[0].get("prediction_mode", "ML") if results else info.get("prediction_mode", "FALLBACK")
    return HotspotPredictResponse(
        predictions=results,
        total=len(results),
        prediction_mode=pred_mode,
        model_version=info.get("version", "trained"),
        validation_status=info.get("validation_status", "VALIDATED" if pred_mode == "ML" else "FALLBACK"),
    )


@router.post("/predict_batch", response_model=HotspotPredictResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))])
def hotspot_predict_batch(
    payload: HotspotPredictRequest,
    current_user: User = Depends(get_current_user),
):
    """Alias of /predict – accepts larger record batches."""
    try:
        results = predict(_apply_default_hour(payload.records, payload.default_hour))
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Hotspot prediction failed. Ensure records contain required fields.")
    return _response_with_mode(results)
    
    info = get_model_info()
    pred_mode = results[0].get("prediction_mode", "ML") if results else info.get("prediction_mode", "FALLBACK")
    return HotspotPredictResponse(
        predictions=results,
        total=len(results),
        prediction_mode=pred_mode,
        model_version=info.get("version", "trained"),
        validation_status=info.get("validation_status", "VALIDATED" if pred_mode == "ML" else "FALLBACK"),
    )


@router.get("/model-info")
def hotspot_model_info(current_user: User = Depends(get_current_user)):
    from app.ai.inference.refresh import check_external_updates

    check_external_updates()
    try:
        return get_model_info()
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Hotspot model not available.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Hotspot model artifact is corrupt or unreadable: {type(e).__name__}")


@router.get("/health")
def hotspot_health():
    try:
        info = get_model_info()
        return {"status": "ok", "model": info.get("model_name"), "version": info.get("version")}
    except Exception:
        return {"status": "unavailable", "detail": "Model not loaded"}
