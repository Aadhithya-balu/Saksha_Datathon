"""
Issue #165: ML Model Validation & Health Reporting Service.

Validates trained model artifacts, feature schemas, training state,
and metadata consistency across all ML pipelines (hotspot, risk, forecast).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Artifact validation helpers
# ---------------------------------------------------------------------------

def _check_artifact_exists(path: Path, label: str) -> dict[str, Any]:
    """Check if an artifact file exists and is non-empty."""
    if not path.exists():
        return {"valid": False, "error": f"{label} artifact not found: {path}", "artifact": label}
    if path.stat().st_size == 0:
        return {"valid": False, "error": f"{label} artifact is empty: {path}", "artifact": label}
    return {"valid": True, "size_bytes": path.stat().st_size, "artifact": label}


def _validate_json_artifact(path: Path, label: str) -> dict[str, Any]:
    """Load and validate a JSON artifact."""
    check = _check_artifact_exists(path, label)
    if not check["valid"]:
        return check
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"valid": True, "data": data, "artifact": label}
    except json.JSONDecodeError as exc:
        return {"valid": False, "error": f"{label} is not valid JSON: {exc}", "artifact": label}


# ---------------------------------------------------------------------------
# Hotspot model validation
# ---------------------------------------------------------------------------

def validate_hotspot_model(model_dir: Path) -> dict[str, Any]:
    """Validate the hotspot model artifacts: model pickle, metadata, features, metrics."""
    results: list[dict[str, Any]] = []

    # 1. Model pickle
    pkl_check = _check_artifact_exists(model_dir / "hotspot_model.pkl", "hotspot_model")
    results.append(pkl_check)

    # 2. Metadata
    meta_check = _validate_json_artifact(model_dir / "model_metadata.json", "metadata")
    results.append(meta_check)

    # 3. Feature columns
    feat_check = _validate_json_artifact(model_dir / "feature_columns.json", "feature_columns")
    results.append(feat_check)

    # 4. Training metrics
    metrics_check = _validate_json_artifact(model_dir / "training_metrics.json", "training_metrics")
    results.append(metrics_check)

    # 5. Feature schema match: check that feature_columns.json list is non-empty
    if feat_check.get("valid") and feat_check.get("data") is not None:
        feat_list = feat_check["data"]
        if not isinstance(feat_list, list) or len(feat_list) == 0:
            results.append({"valid": False, "error": "feature_columns.json is empty or not a list", "artifact": "feature_schema"})
        else:
            results.append({"valid": True, "feature_count": len(feat_list), "artifact": "feature_schema"})

    # 6. Metadata consistency: check required keys
    if meta_check.get("valid") and meta_check.get("data"):
        meta = meta_check["data"]
        required_keys = ["model_name", "algorithm", "h3_resolution", "trained_on"]
        missing_keys = [k for k in required_keys if k not in meta]
        if missing_keys:
            results.append({"valid": False, "error": f"Metadata missing keys: {missing_keys}", "artifact": "metadata_completeness"})
        else:
            results.append({"valid": True, "artifact": "metadata_completeness"})

    # 7. Training state: model_loaded indicates trained state
    model_loaded = pkl_check.get("valid", False)
    results.append({
        "valid": True,
        "artifact": "training_state",
        "model_loaded": model_loaded,
        "status": "TRAINED" if model_loaded else "UNTRAINED",
    })

    valid_count = sum(1 for r in results if r.get("valid"))
    invalid_count = sum(1 for r in results if not r.get("valid"))
    overall_status = "VALID" if invalid_count == 0 else "INVALID"

    return {
        "model": "hotspot",
        "overall_status": overall_status,
        "checks": results,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "model_loaded": model_loaded,
    }


# ---------------------------------------------------------------------------
# Risk model validation
# ---------------------------------------------------------------------------

def validate_risk_model(model_dir: Path) -> dict[str, Any]:
    """Validate risk model artifacts: risk_model.pkl, forecast_model.pkl, metadata, metrics."""
    results: list[dict[str, Any]] = []

    # 1. Risk model pickle
    risk_pkl = _check_artifact_exists(model_dir / "risk_model.pkl", "risk_model")
    results.append(risk_pkl)

    # 2. Forecast model pickle
    forecast_pkl = _check_artifact_exists(model_dir / "forecast_model.pkl", "forecast_model")
    results.append(forecast_pkl)

    # 3. Metadata
    meta_check = _validate_json_artifact(model_dir / "model_metadata.json", "metadata")
    results.append(meta_check)

    # 4. Training metrics
    metrics_check = _validate_json_artifact(model_dir / "training_metrics.json", "training_metrics")
    results.append(metrics_check)

    # 5. Metadata consistency
    if meta_check.get("valid") and meta_check.get("data"):
        meta = meta_check["data"]
        required_keys = ["model_name", "risk_algorithm", "forecast_algorithm", "trained_on"]
        missing_keys = [k for k in required_keys if k not in meta]
        if missing_keys:
            results.append({"valid": False, "error": f"Metadata missing keys: {missing_keys}", "artifact": "metadata_completeness"})
        else:
            results.append({"valid": True, "artifact": "metadata_completeness"})

    # 6. Training state
    risk_loaded = risk_pkl.get("valid", False)
    forecast_loaded = forecast_pkl.get("valid", False)
    status = "TRAINED" if risk_loaded and forecast_loaded else ("PARTIAL" if risk_loaded or forecast_loaded else "UNTRAINED")
    results.append({
        "valid": True,
        "artifact": "training_state",
        "risk_model_loaded": risk_loaded,
        "forecast_model_loaded": forecast_loaded,
        "status": status,
    })

    # 7. Metrics consistency: if training_metrics exist, check risk and forecast keys
    if metrics_check.get("valid") and metrics_check.get("data"):
        metrics = metrics_check["data"]
        has_risk = "risk" in metrics and isinstance(metrics["risk"], dict) and len(metrics["risk"]) > 0
        has_forecast = "forecast" in metrics and isinstance(metrics["forecast"], dict) and len(metrics["forecast"]) > 0
        results.append({
            "valid": has_risk and has_forecast,
            "artifact": "metrics_completeness",
            "has_risk_metrics": has_risk,
            "has_forecast_metrics": has_forecast,
        })

    valid_count = sum(1 for r in results if r.get("valid"))
    invalid_count = sum(1 for r in results if not r.get("valid"))
    overall_status = "VALID" if invalid_count == 0 else "INVALID"

    return {
        "model": "risk",
        "overall_status": overall_status,
        "checks": results,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "risk_model_loaded": risk_loaded,
        "forecast_model_loaded": forecast_loaded,
    }


# ---------------------------------------------------------------------------
# Combined model health
# ---------------------------------------------------------------------------

def _model_dir(name: str) -> Path:
    """Locate a model directory, preferring the canonical trainer path.

    Domain pipelines save artifacts under ``app/ai/models/<name>``, but some
    legacy copies also live under ``app/models/<name>``. Prefer the trainer's
    canonical location; fall back to the legacy location when present so the
    health report reflects exactly what the inference/training code uses.
    """
    app_dir = Path(__file__).resolve().parents[1]  # .../app
    canonical = app_dir / "ai" / "models" / name
    legacy = app_dir / "models" / name
    if canonical.exists():
        return canonical
    if legacy.exists():
        return legacy
    return canonical


def get_all_model_health() -> dict[str, Any]:
    """Aggregate validation for all ML models."""
    hotspot_dir = _model_dir("hotspot")
    risk_dir = _model_dir("risk")

    hotspot = validate_hotspot_model(hotspot_dir)
    risk = validate_risk_model(risk_dir)

    return {
        "hotspot": hotspot,
        "risk": risk,
        "overall_status": "VALID" if hotspot["overall_status"] == "VALID" and risk["overall_status"] == "VALID" else "DEGRADED",
    }
