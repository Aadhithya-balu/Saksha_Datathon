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
ALT_MODEL_DIR = Path(__file__).resolve().parents[3] / "ai" / "models" / "risk"


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")


def save_artifacts(
    risk_model,
    forecast_model,
    risk_metrics: dict[str, float],
    forecast_metrics: dict[str, float],
    risk_feature_columns: list[str],
    forecast_feature_columns: list[str],
    training_rows: int = 0,
    risk_baseline_comparison: dict[str, Any] | None = None,
    forecast_baseline_comparison: dict[str, Any] | None = None,
    training_period: str | None = None,
    validation_period: str | None = None,
) -> Path:
    """Serialize both models and companion JSON files to MODEL_DIR.

    Returns the directory where artifacts were saved.
    """
    for target_dir in (MODEL_DIR, ALT_MODEL_DIR):
        target_dir.mkdir(parents=True, exist_ok=True)

        risk_model.save_model(target_dir / "risk_model.pkl")
        forecast_model.save_model(target_dir / "forecast_model.pkl")

        metadata = {
            "model_name": "SAKSHA District Risk & Forecast",
            "risk_algorithm": "RandomForest",
            "forecast_algorithm": "XGBoost",
            "version": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
            "risk_features": risk_feature_columns,
            "forecast_features": forecast_feature_columns,
            "training_rows": training_rows,
            "training_period": training_period or "historical",
            "validation_period": validation_period or "test_split",
            "validation_status": "VALIDATED" if training_rows >= 10 else "INSUFFICIENT_DATA",
            "risk_metrics": risk_metrics,
            "forecast_metrics": forecast_metrics,
            "risk_baseline_comparison": risk_baseline_comparison or {},
            "forecast_baseline_comparison": forecast_baseline_comparison or {},
            "trained_on": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(target_dir / "model_metadata.json", metadata)
        _write_json(target_dir / "training_metrics.json", {
            "risk": risk_metrics,
            "forecast": forecast_metrics,
            "risk_baseline_comparison": risk_baseline_comparison or {},
            "forecast_baseline_comparison": forecast_baseline_comparison or {},
        })

    logger.info("Risk artifacts saved to %s (and synced to %s)", MODEL_DIR, ALT_MODEL_DIR)
    return MODEL_DIR
