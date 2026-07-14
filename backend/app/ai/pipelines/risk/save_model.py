"""
SAKSHA – Risk Model Artifact Serialization

Saves both DistrictRiskModel and DistrictForecastModel artifacts plus metadata JSON.
No training. No inference. No FastAPI.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parents[3] / "models" / "risk"


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")


def save_artifacts(
    risk_model,
    forecast_model,
    risk_metrics: dict[str, float],
    forecast_metrics: dict[str, float],
    risk_feature_columns: list[str],
    forecast_feature_columns: list[str],
    training_rows: int = 0,
) -> Path:
    """Serialize both models and companion JSON files to MODEL_DIR.

    Returns the directory where artifacts were saved.
    """
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    risk_model.save_model(MODEL_DIR / "risk_model.pkl")
    forecast_model.save_model(MODEL_DIR / "forecast_model.pkl")

    metadata = {
        "model_name": "SAKSHA District Risk & Forecast",
        "risk_algorithm": "RandomForest",
        "forecast_algorithm": "XGBoost",
        "version": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        "risk_features": risk_feature_columns,
        "forecast_features": forecast_feature_columns,
        "training_rows": training_rows,
        "risk_metrics": risk_metrics,
        "forecast_metrics": forecast_metrics,
        "trained_on": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(MODEL_DIR / "model_metadata.json", metadata)
    _write_json(MODEL_DIR / "training_metrics.json", {
        "risk": risk_metrics,
        "forecast": forecast_metrics,
    })

    logger.info("Risk artifacts saved to %s", MODEL_DIR)
    return MODEL_DIR
