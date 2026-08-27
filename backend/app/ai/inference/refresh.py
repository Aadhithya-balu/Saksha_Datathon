"""Staleness-aware model refresh orchestration (issue #145).

Closes four gaps from issue #133/#145:

* **133.1** – inference modules cached trained artifacts forever via
  ``@lru_cache`` and only auto-trained when the artifact was *missing*.
  This service compares each artifact's training timestamp against the
  newest relevant database record and schedules a throttled background
  retrain whenever data has moved forward.
* **133.2** – CRUD routes now call :func:`mark_data_changed` after commits,
  which dirties the affected model domains and evaluates staleness.
* **133.4** – artifacts retrained/promoted by an external process (CI MLOps
  cycle) are detected via a disk mtime signature; when the signature changes
  every in-process lru_cache is invalidated so the running API immediately
  serves the promoted weights.
* **133.5** – ``monitoring.needs_retraining()`` snapshots are consulted: a
  drift-flagged model is treated as stale even if its timestamps look fresh.

The service is deliberately best-effort: every failure is logged, recorded
in the per-model status dict, and never allowed to break an inference or
CRUD request.
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_AI_DIR = Path(__file__).resolve().parents[1]  # .../app/ai
_BACKEND_DIR = _AI_DIR.parents[1]              # .../backend
# NOTE: artifact locations intentionally differ per domain because the
# existing pipelines/inference modules disagree on layout (issue #145):
#   criminal + hotspot -> app/ai/models/<name>
#   risk + anomaly     -> app/models/<name>
_AI_MODELS_DIR = _BACKEND_DIR / "app" / "ai" / "models"
_APP_MODELS_DIR = _BACKEND_DIR / "app" / "models"
_MONITORING_DIR = _AI_DIR.parents[1] / "monitoring"


def _ai_model_dir(name: str) -> Path:
    return _AI_MODELS_DIR / name


def _app_model_dir(name: str) -> Path:
    return _APP_MODELS_DIR / name


@dataclass(frozen=True)
class ModelSpec:
    """Static description of one trainable model domain."""

    key: str
    label: str
    # Artifact files that together represent "the trained model" for this domain.
    artifact_files: tuple[Path, ...]
    # JSON metadata keys scanned (newest wins) to learn when training happened.
    metadata_keys: tuple[str, ...]
    # Module exposing run_training(...) — empty string means no DB trainer exists.
    trainer_module: str
    # Module exposing invalidate_caches().
    invalidator_module: str
    # (module_path, ClassName) probes: newest created_at across these tables
    # decides whether the data has moved past the artifact's training time.
    probes: tuple[tuple[str, str], ...]
    # Optional packages the trainer imports at module level; when any is
    # missing the domain reports trainer_available=False instead of failing
    # every background attempt (e.g. hotspot needs lightgbm/optuna/shap).
    optional_packages: tuple[str, ...] = ()


SPECS: dict[str, ModelSpec] = {
    "criminal": ModelSpec(
        key="criminal",
        label="Criminal intelligence models",
        artifact_files=(
            _ai_model_dir("criminal") / "risk_scorer.json",
            _ai_model_dir("criminal") / "repeat_offender.json",
            _ai_model_dir("criminal") / "similarity.json",
            _ai_model_dir("criminal") / "clustering.json",
        ),
        metadata_keys=("training_metrics.json",),
        trainer_module="app.ai.pipelines.criminal.train",
        invalidator_module="app.ai.inference.criminal",
        probes=(
            ("app.models.criminal", "Criminal"),
            ("app.models.fir", "FIR"),
        ),
    ),
    "risk": ModelSpec(
        key="risk",
        label="District risk + forecast models",
        artifact_files=(
            _ai_model_dir("risk") / "risk_model.pkl",
            _ai_model_dir("risk") / "forecast_model.pkl",
            _ai_model_dir("risk") / "model_metadata.json",
        ),
        metadata_keys=("model_metadata.json",),
        trainer_module="app.ai.pipelines.risk.train",
        invalidator_module="app.ai.inference.risk",
        probes=(("app.models.crime", "CrimeCase"),),
    ),
    "hotspot": ModelSpec(
        key="hotspot",
        label="Crime hotspot predictor",
        artifact_files=(
            _ai_model_dir("hotspot") / "hotspot_model.pkl",
            _ai_model_dir("hotspot") / "feature_columns.json",
            _ai_model_dir("hotspot") / "model_metadata.json",
        ),
        metadata_keys=("model_metadata.json", "training_metrics.json"),
        trainer_module="app.ai.pipelines.hotspot.train",
        invalidator_module="app.ai.inference.hotspot",
        probes=(("app.models.crime", "CrimeCase"),),
        optional_packages=("lightgbm", "optuna", "shap"),
    ),
    "anomaly": ModelSpec(
        key="anomaly",
        label="Anomaly detector",
        artifact_files=(_app_model_dir("anomaly") / "anomaly_model.json",),
        metadata_keys=("anomaly_model.json",),
        trainer_module="",  # trains from event batches; no DB trainer yet
        invalidator_module="app.ai.inference.anomaly",
        probes=(("app.models.fir", "FIR"),),
    ),
}

# CRUD domain -> model keys whose features may shift.
_DOMAIN_MODELS: dict[str, tuple[str, ...]] = {
    "crime_case": ("hotspot", "risk"),
    "fir": ("criminal", "hotspot", "risk", "anomaly"),
    "criminal": ("criminal",),
    "victim": (),  # no model consumes victim rows yet; recorded for future use
}


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


@dataclass
class ModelState:
    last_probe: float = 0.0
    last_refresh_completed: float = 0.0
    last_refreshed_at: str | None = None
    last_reason: str | None = None
    last_error: str | None = None
    refreshing: bool = False
    dirty: bool = False
    seen_signature: float | None = None


_state_lock = threading.Lock()
_states: dict[str, ModelState] = {key: ModelState() for key in SPECS}


# ---------------------------------------------------------------------------
# Artifact helpers
# ---------------------------------------------------------------------------

def artifact_signature(key: str) -> float:
    """Max mtime across the domain's artifacts (0.0 when none exist)."""
    spec = SPECS[key]
    stamps = [p.stat().st_mtime for p in spec.artifact_files if p.exists()]
    return max(stamps) if stamps else 0.0


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def artifact_trained_at(key: str) -> datetime | None:
    """Newest ``trained_at``/``trained_on`` timestamp found in metadata JSONs."""
    spec = SPECS[key]
    newest: datetime | None = None
    seen: set[Path] = set()
    # Metadata may sit beside any artifact or in the canonical model dir.
    candidate_dirs: list[Path] = []
    for artifact in spec.artifact_files:
        if artifact.parent not in candidate_dirs:
            candidate_dirs.append(artifact.parent)
    for directory in candidate_dirs:
        for meta_name in spec.metadata_keys:
            meta_path = directory / meta_name
            if meta_path in seen or not meta_path.exists():
                continue
            seen.add(meta_path)
            try:
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            for field_name in ("trained_at", "trained_on"):
                parsed = _parse_iso(payload.get(field_name))
                if parsed and (newest is None or parsed > newest):
                    newest = parsed
    if newest is None:
        # Fall back to the artifact file mtime when no parseable stamp exists.
        sig = artifact_signature(key)
        if sig > 0:
            newest = datetime.fromtimestamp(sig, tz=timezone.utc)
    return newest


# ---------------------------------------------------------------------------
# Database staleness probes
# ---------------------------------------------------------------------------

def newest_data_ts(db, key: str) -> datetime | None:
    """Newest relevant ``created_at`` across the domain's probe tables."""
    from sqlalchemy import func

    spec = SPECS[key]
    newest: datetime | None = None
    for module_name, class_name in spec.probes:
        try:
            model = getattr(importlib.import_module(module_name), class_name)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("refresh probe import failed for %s.%s: %s", module_name, class_name, exc)
            continue
        try:
            value = db.query(func.max(model.created_at)).scalar()
        except Exception as exc:
            logger.debug("refresh probe query failed for %s: %s", class_name, exc)
            continue
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            if newest is None or value > newest:
                newest = value
    return newest


def monitoring_flagged(key: str) -> bool:
    """Consult the MLOps monitor snapshot for this model (gap 1335).

    Rebuilds the persisted MonitoringSnapshot and defers the verdict to
    ModelMonitor.needs_retraining() so drift detection finally gates a real
    decision instead of being dead code (issue #145, gap 133.5).
    """
    snapshot_path = _MONITORING_DIR / f"{key}-latest.json"
    if not snapshot_path.exists():
        return False
    try:
        from app.mlops.drift import DriftReport
        from app.mlops.monitoring import ModelMonitor, MonitoringSnapshot

        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        drift = [
            DriftReport(
                feature_name=str(item.get("feature_name", "")),
                baseline_mean=float(item.get("baseline_mean", 0.0)),
                current_mean=float(item.get("current_mean", 0.0)),
                absolute_shift=float(item.get("absolute_shift", 0.0)),
                drift_detected=bool(item.get("drift_detected", False)),
            )
            for item in payload.get("drift", [])
            if isinstance(item, dict)
        ]
        snapshot = MonitoringSnapshot(
            model_name=str(payload.get("model_name", key)),
            dataset_version=str(payload.get("dataset_version", "")),
            timestamp=str(payload.get("timestamp", "")),
            metrics=payload.get("metrics") or {},
            drift=drift,
        )
        return ModelMonitor(root=_MONITORING_DIR).needs_retraining(snapshot)
    except Exception as exc:
        logger.debug("monitoring_flagged failed for %s: %s", key, exc)
        return False


def is_stale(db, key: str) -> tuple[bool, dict[str, Any]]:
    trained_at = artifact_trained_at(key)
    data_ts = newest_data_ts(db, key) if db is not None else None
    stale_reasons: list[str] = []
    with _state_lock:
        dirty = _states[key].dirty
    if trained_at is None:
        stale_reasons.append("no_artifact")
    elif data_ts is not None and data_ts > trained_at:
        stale_reasons.append("data_newer_than_model")
    if dirty:
        stale_reasons.append("crud_dirty")
    if monitoring_flagged(key):
        stale_reasons.append("drift_flagged")
    info = {
        "trained_at": trained_at.isoformat() if trained_at else None,
        "newest_data_ts": data_ts.isoformat() if data_ts else None,
        "stale_reasons": stale_reasons,
    }
    return bool(stale_reasons), info


# ---------------------------------------------------------------------------
# Cache invalidation + training
# ---------------------------------------------------------------------------

def _invalidate(key: str, reason: str) -> bool:
    """Invalidate the domain's inference caches. Returns True on success."""
    spec = SPECS[key]
    try:
        module = importlib.import_module(spec.invalidator_module)
        invalidate = getattr(module, "invalidate_caches")
        invalidate()
        logger.info("Invalidated %s inference caches (%s)", key, reason)
        return True
    except Exception as exc:
        logger.warning("Failed to invalidate %s caches: %s", key, exc)
        return False


def invalidate_all_caches(reason: str = "external") -> dict[str, bool]:
    results = {}
    for key in SPECS:
        results[key] = _invalidate(key, reason)
        state = _states[key]
        state.seen_signature = artifact_signature(key)
    return results


def trainer_available(key: str) -> bool:
    spec = SPECS[key]
    if not spec.trainer_module:
        return False
    for pkg in spec.optional_packages:
        try:
            if importlib.util.find_spec(pkg) is None:
                return False
        except (ImportError, ValueError):
            return False
    try:
        return importlib.util.find_spec(spec.trainer_module) is not None
    except (ImportError, ValueError):
        return False


def refresh_model(db, key: str, reason: str = "manual") -> dict[str, Any]:
    """Train the domain synchronously using the given session/engine."""
    spec = SPECS[key]
    summary: dict[str, Any] = {"model": key, "reason": reason, "status": "ok"}
    with _state_lock:
        state = _states[key]
        state.last_reason = reason
        state.refreshing = True
    try:
        if not spec.trainer_module:
            summary["status"] = "skipped"
            summary["detail"] = "no DB trainer registered for this domain"
            return summary
        try:
            trainer_mod = importlib.import_module(spec.trainer_module)
        except ModuleNotFoundError as exc:
            summary["status"] = "skipped"
            summary["detail"] = f"trainer dependency missing: {exc.name}"
            return summary
        run_training = getattr(trainer_mod, "run_training")
        kwargs: dict[str, Any] = {}
        try:
            params = inspect.signature(run_training).parameters
            if "db_session" in params:
                kwargs["db_session"] = db
        except (TypeError, ValueError):  # pragma: no cover - builtins edge
            pass
        result = run_training(**kwargs)
        if isinstance(result, dict):
            summary["metrics"] = result
        _invalidate(key, reason)
        with _state_lock:
            state.dirty = False
            state.last_refresh_completed = _now()
            state.last_refreshed_at = datetime.now(timezone.utc).isoformat()
            state.last_error = None
            state.seen_signature = artifact_signature(key)
        return summary
    except Exception as exc:
        with _state_lock:
            state.last_error = str(exc)
        summary["status"] = "failed"
        summary["detail"] = str(exc)
        logger.exception("Model refresh failed for %s", key)
        return summary
    finally:
        with _state_lock:
            state.refreshing = False


# ---------------------------------------------------------------------------
# Background scheduling
# ---------------------------------------------------------------------------

def _same_engine(db) -> bool:
    """Only auto-refresh when the caller's session uses the app engine.

    Tests inject throwaway SQLite sessions; those must never trigger
    production retrains in background threads.
    """
    if db is None:
        return True
    try:
        from app.database.postgres import engine

        bind = db.get_bind()
        return str(bind.url) == str(engine.url)
    except Exception:
        return False


def maybe_refresh_async(
    key: str | None = None,
    db=None,
    reason: str = "inference-request",
) -> list[str]:
    """Schedule throttled background retrains for stale domains.

    Returns the list of model keys for which a refresh thread was started.
    Never raises.
    """
    if not settings.AUTO_RETRAIN_ENABLED:
        return []
    # Cheap stat()-only check first: pick up artifacts promoted by an
    # external process (CI MLOps cycle) and drop stale caches (gap 133.4).
    try:
        check_external_updates()
    except Exception:  # pragma: no cover - defensive
        pass
    keys = [key] if key else list(SPECS)
    scheduled: list[str] = []
    for k in keys:
        try:
            if not _should_schedule(k, db, reason):
                continue
            threading.Thread(
                target=_worker,
                args=(k, reason),
                name=f"saksha-retrain-{k}",
                daemon=True,
            ).start()
            scheduled.append(k)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("maybe_refresh_async failed for %s: %s", k, exc)
    return scheduled


def _should_schedule(key: str, db, reason: str) -> bool:
    if not trainer_available(key):
        return False
    if db is not None and not _same_engine(db):
        return False
    # Probe gate: at most one staleness probe per model per short window so
    # inference endpoints stay cheap under load.
    with _state_lock:
        state = _states[key]
        if state.refreshing:
            return False
        now = _now()
        if now - state.last_probe < 30.0:
            return False
        state.last_probe = now
    stale, _info = is_stale(db, key)
    if not stale:
        return False
    # Retrain cooldown: bound how often a genuinely stale model retrains.
    with _state_lock:
        state = _states[key]
        interval = max(30, settings.AUTO_RETRAIN_MIN_INTERVAL_SECONDS)
        if now - state.last_refresh_completed < interval:
            return False
    return True


def _worker(key: str, reason: str) -> None:
    from app.database.postgres import SessionLocal

    session = SessionLocal()
    try:
        summary = refresh_model(session, key, reason=reason)
        if summary.get("status") == "ok":
            _notify_retrain_success(session, key, summary)
    finally:
        session.close()


def _notify_retrain_success(db, key: str, summary: dict[str, Any]) -> None:
    """Broadcast a system notification after an automatic retrain (gap 133.2).

    The issue explicitly called out that CRUD writes never produced any AI
    notification; this closes the loop for dashboard/notification-center
    consumers. Best-effort: never raises.
    """
    try:
        from app.models.notification import Notification

        label = SPECS[key].label
        db.add(
            Notification(
                user_id=None,
                subject="AI model refreshed",
                notification_type="model_retrained",
                category="system_notification",
                title=f"{label} retrained automatically",
                message=(
                    f"New crime data was detected and the {label} were retrained "
                    f"(trigger: {summary.get('reason', 'auto')}). Predictions now "
                    "reflect the latest records."
                ),
                severity="low",
                priority="low",
                status="unread",
                resource_type="ai_model",
                resource_id=key,
                is_broadcast=True,
            )
        )
        db.commit()
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        logger.debug("retrain notification failed for %s: %s", key, exc)


def mark_data_changed(domain: str, db=None) -> list[str]:
    """Called by CRUD routes after commit: flag + evaluate staleness (gap 133.2)."""
    keys = _DOMAIN_MODELS.get(domain, ())
    with _state_lock:
        for k in keys:
            _states[k].dirty = True
    return maybe_refresh_async(db=db, reason=f"crud:{domain}")


# ---------------------------------------------------------------------------
# Status reporting
# ---------------------------------------------------------------------------

def get_refresh_status(db=None) -> dict[str, Any]:
    status: dict[str, Any] = {
        "enabled": settings.AUTO_RETRAIN_ENABLED,
        "min_interval_seconds": settings.AUTO_RETRAIN_MIN_INTERVAL_SECONDS,
        "models": {},
    }
    for key, spec in SPECS.items():
        with _state_lock:
            state = _states[key]
            state_snapshot = {
                "last_refreshed_at": state.last_refreshed_at,
                "last_reason": state.last_reason,
                "last_error": state.last_error,
                "refreshing": state.refreshing,
                "dirty": state.dirty,
            }
        stale, info = is_stale(db, key)
        status["models"][key] = {
            "label": spec.label,
            "stale": stale,
            "trainer_available": trainer_available(key),
            "artifact_present": artifact_signature(key) > 0,
            **state_snapshot,
            **info,
        }
    return status


def observe_signatures() -> None:
    """Record current disk signatures without invalidating anything."""
    with _state_lock:
        for key in SPECS:
            _states[key].seen_signature = artifact_signature(key)


def record_refresh_success(key: str) -> None:
    """Let legacy/manual training paths register success for cooldown + status."""
    with _state_lock:
        state = _states[key]
        state.last_refresh_completed = _now()
        state.last_refreshed_at = datetime.now(timezone.utc).isoformat()
        state.last_error = None
        state.dirty = False
        state.seen_signature = artifact_signature(key)


def check_external_updates() -> list[str]:
    """Detect artifacts replaced by another process (CI promotion, gap 133.4).

    When a signature changed, all caches are invalidated so the API serves
    the freshly promoted weights instead of stale lru_cache contents.
    """
    updated: list[str] = []
    for key in SPECS:
        sig = artifact_signature(key)
        with _state_lock:
            seen = _states[key].seen_signature
        if seen is None:
            observe_signatures()
            continue
        if sig != seen:
            _invalidate(key, "disk-artifacts-changed")
            with _state_lock:
                _states[key].seen_signature = sig
            updated.append(key)
    return updated
