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

MODEL_DIR = Path(__file__).resolve().parents[3] / "models" / "hotspot"
H3_RESOLUTION = 7


def _versioned_dir() -> Path:
    """Return a timestamped sub-directory for versioned saves."""
    version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = MODEL_DIR / version
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, data: Any) -> None:
    """Write *data* as indented JSON with UTF-8 encoding."""
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")


def save_artifacts(
    model,
    metrics: dict[str, float],
    best_params: dict[str, Any],
    feature_columns: list[str],
    training_rows: int = 0,
    version_dir: Path | None = None,
) -> Path:
    """Serialize model and all companion JSON files.

    Parameters
    ----------
    model           : Fitted LGBMRegressor.
    metrics         : Dict with rmse, mae, r2.
    best_params     : Hyperparameters used for the final model.
    feature_columns : Ordered list of feature names (single source of truth).
    training_rows   : Number of rows used for training.
    version_dir     : Override output directory (used in tests).

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
            "version": out.name,
            "h3_resolution": H3_RESOLUTION,
            "prediction_target": "Next Month Crime Count",
            "features": feature_columns,
            "feature_count": len(feature_columns),
            "best_params": best_params,
            "training_rows": training_rows,
            "rmse": metrics.get("rmse"),
            "mae": metrics.get("mae"),
            "r2": metrics.get("r2"),
            "trained_on": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(out / "model_metadata.json", metadata)

        # 4. Training metrics (unchanged structure)
        _write_json(out / "training_metrics.json", metrics)

        # 5. Overwrite canonical model dir (latest)
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_DIR / "hotspot_model.pkl")
        _write_json(MODEL_DIR / "feature_columns.json", feature_columns)
        _write_json(MODEL_DIR / "model_metadata.json", metadata)
        _write_json(MODEL_DIR / "training_metrics.json", metrics)

        logger.info("Artifacts saved to %s (and canonical %s).", out, MODEL_DIR)
        return out

    except Exception:
        logger.exception("Failed to save model artifacts.")
        raise
