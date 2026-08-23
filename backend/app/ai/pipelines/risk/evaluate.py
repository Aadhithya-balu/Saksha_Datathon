"""
SAKSHA – Risk & Forecast Model Evaluation

Shared evaluation utilities for both DistrictRiskModel and DistrictForecastModel.
No training. No inference. No FastAPI.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logger = logging.getLogger(__name__)


def compute_metrics(model, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Return RMSE, MAE, R² for any fitted model exposing .predict()."""
    preds = model.predict(X)
    return {
        "rmse": float(np.sqrt(mean_squared_error(y, preds))),
        "mae": float(mean_absolute_error(y, preds)),
        "r2": float(r2_score(y, preds)),
    }


def feature_importance_report(model, feature_names: list[str]) -> list[dict[str, Any]]:
    """Return feature importances sorted descending. Works for RF and XGBoost."""
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return []
    return sorted(
        [{"feature": f, "importance": round(float(i), 6)} for f, i in zip(feature_names, importances)],
        key=lambda x: x["importance"],
        reverse=True,
    )


def build_evaluation_report(
    model,
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
) -> dict[str, Any]:
    """Compose full evaluation report: metrics + feature importance."""
    metrics = compute_metrics(model, X, y)
    importance = feature_importance_report(model, feature_names)
    logger.info(
        "Evaluation: RMSE=%.4f MAE=%.4f R2=%.4f",
        metrics["rmse"], metrics["mae"], metrics["r2"],
    )
    return {"metrics": metrics, "feature_importance": importance}
