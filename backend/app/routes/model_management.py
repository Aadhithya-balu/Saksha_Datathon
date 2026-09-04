"""Unified model management endpoints for all ML model domains.

Endpoints
---------
GET  /ai/models/status              – all-model status overview
GET  /ai/models/{domain}/status     – single-model status
GET  /ai/models/{domain}/versions   – version history
POST /ai/models/{domain}/retrain    – trigger background retrain (admin)
GET  /ai/models/jobs                – recent retrain job history
GET  /ai/models/jobs/{job_id}       – single job detail
"""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_CRIME_ANALYST, require_roles
from app.core.config import settings
from app.database.postgres import get_db
from app.models.model_update import ModelUpdateJob
from app.models.user import User
from app.services import audit_service
from app.services.model_management import (
    DOMAINS,
    all_model_status,
    build_version_record,
    domain_active_status,
    domain_register_version,
    domain_should_retrain,
    get_model_status,
    load_domain_versions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/models", tags=["Model Management"], dependencies=[Depends(require_roles(*ALL_ROLES))])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RetrainRequest(BaseModel):
    reason: str | None = None
    explicit: bool = True


class RetrainResponse(BaseModel):
    status: str
    job_id: str
    domain: str
    current_version: str | None = None


class JobListResponse(BaseModel):
    jobs: list[dict[str, Any]]
    total: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/status")
def models_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return unified status for all model domains."""
    status_data = all_model_status()

    from app.ai.inference.refresh import get_refresh_status
    try:
        refresh = get_refresh_status(db=db)
        status_data["refresh_status"] = refresh
    except Exception:
        status_data["refresh_status"] = None

    return status_data


@router.get("/refresh-status")
def models_refresh_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staleness + auto-refresh status for every model domain."""
    from app.ai.inference.refresh import get_refresh_status
    return get_refresh_status(db=db)


@router.get("/{domain}/status")
def model_domain_status(
    domain: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return status for a single model domain."""
    if domain not in DOMAINS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown model domain: {domain!r}")

    result = get_model_status(domain)

    from app.ai.inference.refresh import is_stale, trainer_available
    try:
        stale, stale_info = is_stale(db, domain)
        result["staleness"] = stale_info
        result["is_stale"] = stale
        result["trainer_available"] = trainer_available(domain)
    except Exception:
        result["staleness"] = None
        result["is_stale"] = None
        result["trainer_available"] = False

    return result


@router.get("/{domain}/versions")
def model_domain_versions(
    domain: str,
    current_user: User = Depends(get_current_user),
):
    """Return version history for a model domain."""
    if domain not in DOMAINS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown model domain: {domain!r}")
    return {"domain": domain, "versions": load_domain_versions(domain)}


@router.post("/{domain}/retrain", dependencies=[Depends(require_roles(ROLE_ADMIN))])
def retrain_model(
    domain: str,
    payload: RetrainRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger a background retrain for the specified model domain.

    Only admins can trigger retraining. The candidate model is evaluated
    against the active model; the active model is only replaced if the
    candidate satisfies the configured acceptance threshold.
    """
    if domain not in DOMAINS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown model domain: {domain!r}")

    allowed, reason_code = domain_should_retrain(
        domain,
        new_records=0,
        dataset_change_pct=0.0,
        explicit=payload.explicit,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Retraining threshold not met for {domain}.",
        )

    current_version = domain_active_status(domain).get("model_version")

    job = ModelUpdateJob(
        model_name=domain,
        trigger_type="manual" if payload.explicit else "automatic",
        reason=payload.reason or reason_code,
        triggered_by_id=current_user.id,
        status="queued",
        previous_version=current_version,
        deployment_status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    audit_service.log_action(
        db, current_user, "MODEL_RETRAIN",
        "ModelUpdateJob", str(job.id),
        details=f"{domain} retrain: {job.reason}",
    )

    threading.Thread(
        target=_run_domain_retrain_job,
        args=(domain, str(job.id), str(current_user.id), job.reason),
        daemon=True,
        name=f"saksha-retrain-{domain}-{job.id}",
    ).start()

    return RetrainResponse(
        status="queued",
        job_id=str(job.id),
        domain=domain,
        current_version=current_version,
    )


@router.get("/jobs", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST))])
def list_jobs(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return recent model update jobs."""
    jobs = (
        db.query(ModelUpdateJob)
        .order_by(ModelUpdateJob.created_at.desc())
        .limit(limit)
        .all()
    )
    return JobListResponse(
        jobs=[_serialize_job(j) for j in jobs],
        total=len(jobs),
    )


@router.get("/jobs/{job_id}", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST))])
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a single model update job."""
    job = db.query(ModelUpdateJob).filter(ModelUpdateJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return _serialize_job(job)


# ---------------------------------------------------------------------------
# Background retrain worker
# ---------------------------------------------------------------------------

def _run_domain_retrain_job(
    domain: str,
    job_id: str,
    user_id: str | None,
    reason: str | None,
) -> None:
    """Execute the retrain -> evaluate -> accept/reject cycle for a model domain."""
    from app.database.postgres import SessionLocal
    from app.services.model_management import _domain_next_version

    session = SessionLocal()
    try:
        job = session.query(ModelUpdateJob).filter(ModelUpdateJob.id == job_id).first()
        if not job:
            return

        job.status = "training"
        job.started_at = datetime.now(timezone.utc)
        session.commit()

        result = _train_domain(domain)

        job.status = "evaluating"
        session.commit()

        metrics = result.get("metrics", {})
        candidate_info = _evaluate_domain(domain, metrics)

        version = _domain_next_version(domain)
        prev_version = domain_active_status(domain).get("model_version")
        accepted = candidate_info.get("accepted", False)

        version_record = build_version_record(
            version=version,
            status="active" if accepted else "rejected",
            previous_version=prev_version,
            dataset_version=result.get("dataset_version"),
            training_records=result.get("training_rows", 0),
            metrics=metrics,
            deployment_status="deployed" if accepted else "kept-current",
            reason=reason,
        )
        version_record["improvement_pct"] = candidate_info.get("improvement_pct", 0.0)
        domain_register_version(domain, version_record)

        if accepted:
            _invalidate_domain_caches(domain)
            job.status = "deployed"
            job.new_version = version
        else:
            job.status = "rejected"
            job.new_version = prev_version

        job.completed_at = datetime.now(timezone.utc)
        job.previous_version = prev_version
        job.deployment_status = "deployed" if accepted else "kept-current"
        job.evaluation_metrics = json.dumps({
            **metrics,
            "improvement_pct": candidate_info.get("improvement_pct", 0.0),
            "accepted": accepted,
        })
        session.commit()

    except Exception as exc:
        logger.exception("Retrain job %s failed for domain %s", job_id, domain)
        session.rollback()
        job = session.query(ModelUpdateJob).filter(ModelUpdateJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(exc)[:2000]
            job.completed_at = datetime.now(timezone.utc)
            job.deployment_status = "failed"
            session.commit()
    finally:
        session.close()


def _train_domain(domain: str) -> dict[str, Any]:
    """Run the trainer for a domain and return training results."""
    import importlib.util

    domain_info = DOMAINS[domain]
    trainer_module_name = domain_info.trainer_module

    for pkg in domain_info.optional_packages:
        try:
            if importlib.util.find_spec(pkg) is None:
                return {
                    "status": "skipped",
                    "error": f"optional dependency {pkg} not installed",
                    "metrics": {},
                    "training_rows": 0,
                }
        except (ImportError, ValueError):
            return {
                "status": "skipped",
                "error": f"optional dependency {pkg} not available",
                "metrics": {},
                "training_rows": 0,
            }

    try:
        module = importlib.import_module(trainer_module_name)
    except ModuleNotFoundError as exc:
        return {
            "status": "skipped",
            "error": f"trainer module not found: {exc.name}",
            "metrics": {},
            "training_rows": 0,
        }

    run_training = getattr(module, "run_training", None)
    if run_training is None:
        return {
            "status": "skipped",
            "error": "trainer module has no run_training function",
            "metrics": {},
            "training_rows": 0,
        }

    try:
        sig = inspect.signature(run_training)
        kwargs: dict[str, Any] = {}
        if "db_session" in sig.parameters:
            from app.database.postgres import SessionLocal
            db = SessionLocal()
            try:
                kwargs["db_session"] = db
            finally:
                db.close()
        result = run_training(**kwargs)
    except TypeError:
        result = run_training()
    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "metrics": {},
            "training_rows": 0,
        }

    if isinstance(result, dict):
        return result
    return {"status": "ok", "metrics": {}, "training_rows": 0}


def _evaluate_domain(domain: str, candidate_metrics: dict[str, Any]) -> dict[str, Any]:
    """Compare candidate metrics against the active model. Returns acceptance verdict."""
    domain_info = DOMAINS[domain]
    min_improvement = getattr(settings, domain_info.retrain_min_improvement_setting, 0.0)

    active_metrics = _domain_current_metrics(domain)
    if not active_metrics or not isinstance(active_metrics, dict):
        return {"accepted": True, "improvement_pct": 100.0, "reason": "no-active-model"}

    if domain in ("hotspot", "risk"):
        return _compare_rmse(active_metrics, candidate_metrics, min_improvement)
    elif domain == "criminal":
        return _compare_criminal(active_metrics, candidate_metrics, min_improvement)
    return {"accepted": True, "improvement_pct": 0.0, "reason": "no-comparison-available"}


def _domain_current_metrics(domain: str) -> dict[str, Any]:
    from app.services.model_management import DOMAINS
    d = DOMAINS[domain]
    try:
        raw = (d.model_dir / d.metrics_file).read_text(encoding="utf-8")
        return json.loads(raw)
    except Exception:
        return {}


def _compare_rmse(
    active: dict[str, Any],
    candidate: dict[str, Any],
    min_improvement_pct: float,
) -> dict[str, Any]:
    """Compare RMSE-based models (hotspot, risk)."""
    active_rmse = active.get("rmse")
    if active_rmse is None:
        bc = active.get("baseline_comparison", {})
        active_rmse = bc.get("rmse")
    candidate_rmse = candidate.get("rmse")
    if candidate_rmse is None:
        bc = candidate.get("baseline_comparison", {})
        candidate_rmse = bc.get("rmse")

    if active_rmse is None or candidate_rmse is None:
        return {"accepted": True, "improvement_pct": 0.0, "reason": "no-metric-to-compare"}

    if active_rmse <= 0:
        return {"accepted": True, "improvement_pct": 0.0, "reason": "baseline-rmse-nonpositive"}

    improvement_pct = ((active_rmse - candidate_rmse) / active_rmse) * 100.0
    accepted = improvement_pct >= min_improvement_pct
    return {
        "accepted": accepted,
        "improvement_pct": round(improvement_pct, 2),
        "active_rmse": active_rmse,
        "candidate_rmse": candidate_rmse,
        "reason": "improvement-threshold-met" if accepted else "below-improvement-threshold",
    }


def _compare_criminal(
    active: dict[str, Any],
    candidate: dict[str, Any],
    min_improvement_pct: float,
) -> dict[str, Any]:
    """Criminal models are custom (no sklearn metrics). Accept if training succeeded with data."""
    candidate_rows = candidate.get("training_rows", 0)
    if candidate_rows < 2:
        return {"accepted": False, "improvement_pct": 0.0, "reason": "insufficient-training-data"}
    return {"accepted": True, "improvement_pct": 100.0, "reason": "training-succeeded"}


def _invalidate_domain_caches(domain: str) -> None:
    """Invalidate inference caches for a domain after a successful retrain."""
    try:
        from app.ai.inference.refresh import _invalidate
        _invalidate(domain, "model-management-retrain")
    except Exception as exc:
        logger.warning("Cache invalidation failed for %s: %s", domain, exc)


def _serialize_job(job: ModelUpdateJob) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "model_name": job.model_name,
        "trigger_type": job.trigger_type,
        "reason": job.reason,
        "status": job.status,
        "previous_version": job.previous_version,
        "new_version": job.new_version,
        "dataset_version": job.dataset_version,
        "training_records": job.training_records,
        "evaluation_metrics": json.loads(job.evaluation_metrics) if job.evaluation_metrics else None,
        "deployment_status": job.deployment_status,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
