"""
SAKSHA – Hotspot Model Artifact Serialization

Responsibilities
----------------
- joblib serialization of trained model
- feature_columns.json
- model_metadata.json  (includes training_rows, rmse, mae, r2)
- training_metrics.json
- Versioned output directory

No training. No inference. No FastAPI.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger(__name__)

AI_MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "hotspot"
APP_MODEL_DIR = Path(__file__).resolve().parents[3] / "models" / "hotspot"
H3_RESOLUTION = 7


def _versioned_dir() -> Path:
    """Return a timestamped sub-directory for versioned saves."""
    version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = AI_MODEL_DIR / version
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, data: Any) -> None:
    """Write *data* as indented JSON with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")


def save_artifacts(
    model,
    metrics: dict[str, float],
    best_params: dict[str, Any],
    feature_columns: list[str],
    training_rows: int = 0,
    version_dir: Path | None = None,
    ranking_metrics: dict[str, Any] | None = None,
    baseline_comparison: dict[str, Any] | None = None,
    training_period: str | None = None,
    validation_period: str | None = None,
) -> Path:
    """Serialize model and all companion JSON files.

    Parameters
    ----------
    model               : Fitted LGBMRegressor.
    metrics             : Dict with rmse, mae, r2.
    best_params         : Hyperparameters used for the final model.
    feature_columns     : Ordered list of feature names (single source of truth).
    training_rows       : Number of rows used for training.
    version_dir         : Override output directory (used in tests).
    ranking_metrics     : Top-K precision, hit rate, and capture metrics.
    baseline_comparison : Comparison metrics against simple spatial baseline.
    training_period     : Date range string of training data.
    validation_period   : Description of validation split.

    Returns
    -------
    Path to the directory where artifacts were saved.
    """
    try:
        out = version_dir or _versioned_dir()
        out.mkdir(parents=True, exist_ok=True)

        # 1. Model pickle
        joblib.dump(model, out / "hotspot_model.pkl")

        # 2. Feature columns
        _write_json(out / "feature_columns.json", feature_columns)

        # 3. Model metadata (includes metrics for quick inspection)
        metadata = {
            "model_name": "SAKSHA Hotspot Predictor",
            "algorithm": "LightGBM",
            "version": out.name if out != AI_MODEL_DIR else datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
            "h3_resolution": H3_RESOLUTION,
            "prediction_target": "Next Month Crime Count per H3 Cell",
            "features": feature_columns,
            "feature_count": len(feature_columns),
            "best_params": best_params,
            "training_rows": training_rows,
            "training_period": training_period or "historical",
            "validation_period": validation_period or "test_split",
            "validation_status": "VALIDATED" if training_rows >= 10 else "INSUFFICIENT_DATA",
            "rmse": metrics.get("rmse"),
            "mae": metrics.get("mae"),
            "r2": metrics.get("r2"),
            "ranking_metrics": ranking_metrics or {},
            "baseline_comparison": baseline_comparison or {},
            "trained_on": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(out / "model_metadata.json", metadata)

        # 4. Training metrics
        full_metrics = {
            **metrics,
            "ranking_metrics": ranking_metrics or {},
            "baseline_comparison": baseline_comparison or {},
        }
        _write_json(out / "training_metrics.json", full_metrics)

        # 5. Overwrite canonical model dirs (AI_MODEL_DIR and APP_MODEL_DIR)
        for canonical_dir in (AI_MODEL_DIR, APP_MODEL_DIR):
            canonical_dir.mkdir(parents=True, exist_ok=True)
            joblib.dump(model, canonical_dir / "hotspot_model.pkl")
            _write_json(canonical_dir / "feature_columns.json", feature_columns)
            _write_json(canonical_dir / "model_metadata.json", metadata)
            _write_json(canonical_dir / "training_metrics.json", full_metrics)

        logger.info("Artifacts saved to %s (and canonical %s).", out, AI_MODEL_DIR)
        return out

    except Exception:
        logger.exception("Failed to save model artifacts.")
        raise
