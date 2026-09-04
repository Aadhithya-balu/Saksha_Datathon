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

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.inference.hotspot import get_model_info, predict
from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, require_roles
from app.core.config import settings
from app.database.postgres import get_db
from app.models.model_update import ModelUpdateJob
from app.models.user import User
from app.services import audit_service
from app.services.model_management import (
    active_status,
    build_version_record,
    copy_candidate_to_active,
    current_model_version,
    hotspot_model_dir,
    load_versions,
    next_version,
    register_version,
    should_retrain,
)

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
    prediction_mode: str = "ML"
    model_version: str | None = None
    validation_status: str | None = None
    data_provenance: str = "UNKNOWN"


class RetrainRequest(BaseModel):
    reason: str | None = None
    explicit: bool = True


class ModelStatusResponse(BaseModel):
    current: dict[str, Any]
    versions: list[dict[str, Any]]
    retrain_policy: dict[str, Any]
    active_job: dict[str, Any] | None = None


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
    try:
        results = predict(_apply_default_hour(payload.records, payload.default_hour))
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Hotspot prediction failed. Ensure records contain required fields.")
    return _response_with_mode(results)


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


@router.get("/model-info")
def hotspot_model_info(current_user: User = Depends(get_current_user)):
    try:
        return get_model_info()
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Hotspot model not available.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Hotspot model artifact is corrupt or unreadable: {type(e).__name__}")


@router.get("/current", response_model=ModelStatusResponse, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))])
def hotspot_current_model(current_user: User = Depends(get_current_user)):
    del current_user
    return ModelStatusResponse(
        current=active_status(),
        versions=load_versions(),
        retrain_policy={
            "min_new_cases": settings.HOTSPOT_RETRAIN_MIN_NEW_CASES,
            "min_dataset_change_pct": settings.HOTSPOT_RETRAIN_MIN_DATASET_CHANGE_PCT,
            "min_rmse_improvement_pct": settings.HOTSPOT_RETRAIN_MIN_RMSE_IMPROVEMENT_PCT,
            "scheduled_enabled": settings.HOTSPOT_RETRAIN_ALLOW_SCHEDULED,
        },
        active_job=None,
    )


@router.get("/versions", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR))])
def hotspot_model_versions(current_user: User = Depends(get_current_user)):
    del current_user
    return {"results": load_versions()}


def _run_retrain_job(job_id: str, user_id: str | None, reason: str | None) -> None:
    from app.database.postgres import SessionLocal
    from app.ai.pipelines.hotspot.train import run_training
    from app.ai.inference.hotspot import invalidate_caches

    session = SessionLocal()
    try:
        job = session.query(ModelUpdateJob).filter(ModelUpdateJob.id == job_id).first()
        if not job:
            return
        job.status = "training"
        job.started_at = datetime.now(timezone.utc)
        session.commit()

        candidate = run_training(publish_active=False, artifact_root=hotspot_model_dir() / "versions")
        job.status = "evaluating"
        session.commit()

        metrics = candidate.get("metrics", {})
        baseline = candidate.get("baseline_comparison", {})
        candidate_rmse = float(metrics.get("rmse") or 0.0)
        baseline_rmse = float((baseline.get("baseline_metrics") or {}).get("rmse") or candidate_rmse)
        improvement_pct = ((baseline_rmse - candidate_rmse) / baseline_rmse * 100.0) if baseline_rmse else 0.0

        version = next_version()
        prev_version = current_model_version()
        accepted = bool(improvement_pct >= settings.HOTSPOT_RETRAIN_MIN_RMSE_IMPROVEMENT_PCT)
        version_record = build_version_record(
            version=version,
            status="active" if accepted else "rejected",
            previous_version=prev_version,
            dataset_version=f"hotspot-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            training_records=int(candidate.get("baseline_comparison", {}).get("training_rows", 0) or 0),
            metrics=metrics,
            deployment_status="deployed" if accepted else "kept-current",
            reason=reason,
        )
        version_record["improvement_pct"] = improvement_pct
        register_version(version_record)

        if accepted:
            copy_candidate_to_active(Path(candidate.get("artifacts_dir") or hotspot_model_dir() / "versions"))
            invalidate_caches()
            job.status = "deployed"
            job.new_version = version
        else:
            job.status = "rejected"
            job.new_version = prev_version
        job.completed_at = datetime.now(timezone.utc)
        job.previous_version = prev_version
        job.deployment_status = "deployed" if accepted else "kept-current"
        job.evaluation_metrics = json.dumps({**metrics, "improvement_pct": improvement_pct})
        session.commit()
    except Exception as exc:
        job = session.query(ModelUpdateJob).filter(ModelUpdateJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
    finally:
        session.close()


@router.post("/retrain", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def hotspot_retrain(
    payload: RetrainRequest,
    request: Any = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed, reason_code = should_retrain(new_cases=settings.HOTSPOT_RETRAIN_MIN_NEW_CASES, dataset_change_pct=settings.HOTSPOT_RETRAIN_MIN_DATASET_CHANGE_PCT, explicit=payload.explicit)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Retraining threshold not reached.")
    job = ModelUpdateJob(
        model_name="hotspot",
        trigger_type="manual" if payload.explicit else "automatic",
        reason=payload.reason or reason_code,
        triggered_by_id=current_user.id,
        status="queued",
        previous_version=current_model_version(),
        deployment_status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    audit_service.log_action(db, current_user, "MODEL_RETRAIN", "HotspotModel", str(job.id), details=job.reason)
    threading.Thread(target=_run_retrain_job, args=(str(job.id), str(current_user.id), job.reason), daemon=True).start()
    return {"status": "queued", "job_id": str(job.id), "current_version": current_model_version()}


@router.get("/health")
def hotspot_health():
    try:
        info = get_model_info()
        return {"status": "ok", "model": info.get("model_name"), "version": info.get("version")}
    except Exception:
        return {"status": "unavailable", "detail": "Model not loaded"}
