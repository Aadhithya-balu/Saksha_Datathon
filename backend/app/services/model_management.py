from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

_AI_MODELS_DIR = Path(__file__).resolve().parents[1] / "ai" / "models"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Model domain registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelDomain:
    key: str
    label: str
    model_dir: Path
    artifact_files: tuple[str, ...]
    metadata_file: str
    metrics_file: str
    versions_file: str
    algorithm: str
    trainer_module: str
    retrain_min_new_records_setting: str
    retrain_min_change_pct_setting: str
    retrain_min_improvement_setting: str
    retrain_scheduled_setting: str
    optional_packages: tuple[str, ...] = ()


def _hotspot_dir() -> Path:
    if settings.HOTSPOT_MODEL_STORE_DIR:
        return Path(settings.HOTSPOT_MODEL_STORE_DIR)
    return _AI_MODELS_DIR / "hotspot"


DOMAINS: dict[str, ModelDomain] = {
    "hotspot": ModelDomain(
        key="hotspot",
        label="Crime Hotspot Predictor",
        model_dir=_hotspot_dir(),
        artifact_files=("hotspot_model.pkl", "feature_columns.json", "model_metadata.json", "training_metrics.json"),
        metadata_file="model_metadata.json",
        metrics_file="training_metrics.json",
        versions_file="model_versions.json",
        algorithm="LightGBM",
        trainer_module="app.ai.pipelines.hotspot.train",
        retrain_min_new_records_setting="HOTSPOT_RETRAIN_MIN_NEW_CASES",
        retrain_min_change_pct_setting="HOTSPOT_RETRAIN_MIN_DATASET_CHANGE_PCT",
        retrain_min_improvement_setting="HOTSPOT_RETRAIN_MIN_RMSE_IMPROVEMENT_PCT",
        retrain_scheduled_setting="HOTSPOT_RETRAIN_ALLOW_SCHEDULED",
        optional_packages=("lightgbm", "optuna", "shap"),
    ),
    "risk": ModelDomain(
        key="risk",
        label="District Risk & Forecast",
        model_dir=_AI_MODELS_DIR / "risk",
        artifact_files=("risk_model.pkl", "forecast_model.pkl", "model_metadata.json", "training_metrics.json"),
        metadata_file="model_metadata.json",
        metrics_file="training_metrics.json",
        versions_file="model_versions.json",
        algorithm="RandomForest + XGBoost",
        trainer_module="app.ai.pipelines.risk.train",
        retrain_min_new_records_setting="RISK_RETRAIN_MIN_NEW_CASES",
        retrain_min_change_pct_setting="RISK_RETRAIN_MIN_DATASET_CHANGE_PCT",
        retrain_min_improvement_setting="RISK_RETRAIN_MIN_IMPROVEMENT_PCT",
        retrain_scheduled_setting="RISK_RETRAIN_ALLOW_SCHEDULED",
    ),
    "criminal": ModelDomain(
        key="criminal",
        label="Criminal Intelligence Models",
        model_dir=_AI_MODELS_DIR / "criminal",
        artifact_files=("risk_scorer.json", "repeat_offender.json", "similarity.json", "clustering.json", "training_metrics.json"),
        metadata_file="training_metrics.json",
        metrics_file="training_metrics.json",
        versions_file="model_versions.json",
        algorithm="Custom (Weighted Linear + Logistic + Cosine KNN + k-means)",
        trainer_module="app.ai.pipelines.criminal.train",
        retrain_min_new_records_setting="CRIMINAL_RETRAIN_MIN_NEW_RECORDS",
        retrain_min_change_pct_setting="CRIMINAL_RETRAIN_MIN_DATASET_CHANGE_PCT",
        retrain_min_improvement_setting="CRIMINAL_RETRAIN_MIN_NEW_RECORDS",
        retrain_scheduled_setting="CRIMINAL_RETRAIN_ALLOW_SCHEDULED",
        optional_packages=(),
    ),
}


# ---------------------------------------------------------------------------
# Hotspot-specific helpers (kept for backward compatibility)
# ---------------------------------------------------------------------------

def hotspot_model_dir() -> Path:
    return DOMAINS["hotspot"].model_dir


def versions_dir() -> Path:
    d = hotspot_model_dir() / "versions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_versions() -> list[dict[str, Any]]:
    return _read_json(hotspot_model_dir() / "model_versions.json", [])


def save_versions(items: list[dict[str, Any]]) -> None:
    _write_json(hotspot_model_dir() / "model_versions.json", items)


def current_metadata() -> dict[str, Any]:
    return _read_json(hotspot_model_dir() / "model_metadata.json", {})


def current_metrics() -> dict[str, Any]:
    return _read_json(hotspot_model_dir() / "training_metrics.json", {})


def current_model_version() -> str | None:
    return current_metadata().get("version")


def active_status() -> dict[str, Any]:
    meta = current_metadata()
    metrics = current_metrics()
    versions = load_versions()
    latest = versions[-1] if versions else {}
    return {
        "model_name": meta.get("model_name", "SAKSHA Hotspot Predictor"),
        "model_version": meta.get("version"),
        "algorithm": meta.get("algorithm", "LightGBM"),
        "trained_at": meta.get("trained_on"),
        "training_rows": meta.get("training_rows", 0),
        "dataset_version": meta.get("dataset_version"),
        "feature_version": meta.get("feature_version", "v1"),
        "previous_version": meta.get("previous_version"),
        "status": latest.get("status", "active"),
        "deployment_status": latest.get("deployment_status", "deployed"),
        "metrics": metrics or {
            "rmse": meta.get("rmse"),
            "mae": meta.get("mae"),
            "r2": meta.get("r2"),
        },
        "versions": versions,
    }


def should_retrain(*, new_cases: int, dataset_change_pct: float, explicit: bool = False) -> tuple[bool, str]:
    if explicit:
        return True, "explicit-admin-action"
    if new_cases >= settings.HOTSPOT_RETRAIN_MIN_NEW_CASES:
        return True, f"new-cases-threshold:{new_cases}"
    if dataset_change_pct >= settings.HOTSPOT_RETRAIN_MIN_DATASET_CHANGE_PCT:
        return True, f"dataset-change:{dataset_change_pct:.2f}%"
    return False, "below-threshold"


@dataclass(frozen=True)
class CandidateArtifact:
    version: str
    path: Path
    metadata: dict[str, Any]
    metrics: dict[str, Any]


def next_version() -> str:
    versions = load_versions()
    return f"v{len(versions) + 1:03d}"


def register_version(record: dict[str, Any]) -> None:
    versions = load_versions()
    versions.append(record)
    save_versions(versions)


def copy_candidate_to_active(candidate_dir: Path) -> None:
    target = hotspot_model_dir()
    target.mkdir(parents=True, exist_ok=True)
    for name in ("hotspot_model.pkl", "feature_columns.json", "model_metadata.json", "training_metrics.json"):
        src = candidate_dir / name
        if src.exists():
            shutil.copy2(src, target / name)


def build_version_record(
    *,
    version: str,
    status: str,
    previous_version: str | None,
    dataset_version: str | None,
    training_records: int,
    metrics: dict[str, Any],
    deployment_status: str,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "model_version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_version": dataset_version,
        "training_records": training_records,
        "metrics": metrics,
        "status": status,
        "deployment_status": deployment_status,
        "previous_version": previous_version,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Unified domain-level helpers (used by the model management router)
# ---------------------------------------------------------------------------

def _domain_versions_path(domain: str) -> Path:
    d = DOMAINS[domain]
    return d.model_dir / d.versions_file


def load_domain_versions(domain: str) -> list[dict[str, Any]]:
    return _read_json(_domain_versions_path(domain), [])


def save_domain_versions(domain: str, items: list[dict[str, Any]]) -> None:
    _write_json(_domain_versions_path(domain), items)


def _domain_next_version(domain: str) -> str:
    versions = load_domain_versions(domain)
    return f"v{len(versions) + 1:03d}"


def _domain_current_metadata(domain: str) -> dict[str, Any]:
    d = DOMAINS[domain]
    return _read_json(d.model_dir / d.metadata_file, {})


def _domain_current_metrics(domain: str) -> dict[str, Any]:
    d = DOMAINS[domain]
    return _read_json(d.model_dir / d.metrics_file, {})


def domain_active_status(domain: str) -> dict[str, Any]:
    """Return the active model status for any domain."""
    d = DOMAINS[domain]
    meta = _domain_current_metadata(domain)
    metrics = _domain_current_metrics(domain)
    versions = load_domain_versions(domain)
    latest = versions[-1] if versions else {}

    artifacts_present = all(
        (d.model_dir / f).exists() for f in d.artifact_files if f != d.versions_file
    )

    trained_at = meta.get("trained_on") or meta.get("trained_at")
    training_rows = meta.get("training_rows", 0)
    algorithm = meta.get("algorithm", d.algorithm)
    model_version = meta.get("version")
    previous_version = meta.get("previous_version")

    if domain == "hotspot":
        display_metrics = metrics or {
            "rmse": meta.get("rmse"),
            "mae": meta.get("mae"),
            "r2": meta.get("r2"),
        }
    elif domain == "risk":
        display_metrics = metrics or {}
    elif domain == "criminal":
        display_metrics = metrics or {}
    else:
        display_metrics = metrics or {}

    return {
        "model_name": meta.get("model_name", d.label),
        "model_version": model_version,
        "algorithm": algorithm,
        "trained_at": trained_at,
        "training_rows": training_rows,
        "dataset_version": meta.get("dataset_version"),
        "feature_version": meta.get("feature_version", "v1"),
        "previous_version": previous_version,
        "status": latest.get("status", "active"),
        "deployment_status": latest.get("deployment_status", "deployed"),
        "artifacts_present": artifacts_present,
        "metrics": display_metrics,
    }


def domain_retrain_policy(domain: str) -> dict[str, Any]:
    d = DOMAINS[domain]
    return {
        "min_new_records": getattr(settings, d.retrain_min_new_records_setting),
        "min_dataset_change_pct": getattr(settings, d.retrain_min_change_pct_setting),
        "min_improvement_pct": getattr(settings, d.retrain_min_improvement_setting),
        "scheduled_enabled": getattr(settings, d.retrain_scheduled_setting),
    }


def domain_should_retrain(
    domain: str,
    *,
    new_records: int = 0,
    dataset_change_pct: float = 0.0,
    explicit: bool = False,
) -> tuple[bool, str]:
    """Evaluate whether a model domain should be retrained."""
    d = DOMAINS[domain]
    min_new = getattr(settings, d.retrain_min_new_records_setting)
    min_pct = getattr(settings, d.retrain_min_change_pct_setting)

    if explicit:
        return True, "explicit-admin-action"
    if new_records >= min_new:
        return True, f"new-records-threshold:{new_records}"
    if dataset_change_pct >= min_pct:
        return True, f"dataset-change:{dataset_change_pct:.2f}%"
    return False, "below-threshold"


def domain_register_version(domain: str, record: dict[str, Any]) -> None:
    versions = load_domain_versions(domain)
    versions.append(record)
    save_domain_versions(domain, versions)


def all_model_status() -> dict[str, Any]:
    """Return a unified status response for all model domains."""
    models = {}
    for domain_key in DOMAINS:
        models[domain_key] = {
            "current": domain_active_status(domain_key),
            "versions": load_domain_versions(domain_key),
            "retrain_policy": domain_retrain_policy(domain_key),
        }
    return {
        "models": models,
        "auto_retrain_enabled": settings.AUTO_RETRAIN_ENABLED,
        "min_interval_seconds": settings.AUTO_RETRAIN_MIN_INTERVAL_SECONDS,
    }


def get_model_status(domain: str) -> dict[str, Any]:
    """Return status for a single model domain."""
    if domain not in DOMAINS:
        raise ValueError(f"Unknown model domain: {domain!r}")
    return {
        "current": domain_active_status(domain),
        "versions": load_domain_versions(domain),
        "retrain_policy": domain_retrain_policy(domain),
    }
