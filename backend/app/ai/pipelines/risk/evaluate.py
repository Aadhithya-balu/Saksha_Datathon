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


def compute_baseline_metrics(y_true: np.ndarray, y_baseline: np.ndarray) -> dict[str, float]:
    """Compute RMSE, MAE, R² for a simple non-ML baseline (e.g. historical average)."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_baseline = np.asarray(y_baseline, dtype=np.float64)
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_baseline))),
        "mae": float(mean_absolute_error(y_true, y_baseline)),
        "r2": float(r2_score(y_true, y_baseline)),
    }


def compute_baseline_comparison(
    model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    baseline_preds: np.ndarray,
) -> dict[str, Any]:
    """Compare ML model metrics against a simple historical baseline."""
    model_m = compute_metrics(model, X_test, y_test)
    base_m = compute_baseline_metrics(y_test, baseline_preds)

    rmse_impr = (
        round(((base_m["rmse"] - model_m["rmse"]) / base_m["rmse"] * 100.0), 2)
        if base_m["rmse"] > 1e-9
        else 0.0
    )
    mae_impr = (
        round(((base_m["mae"] - model_m["mae"]) / base_m["mae"] * 100.0), 2)
        if base_m["mae"] > 1e-9
        else 0.0
    )

    return {
        "model_metrics": model_m,
        "baseline_metrics": base_m,
        "rmse_improvement_pct": rmse_impr,
        "mae_improvement_pct": mae_impr,
        "outperforms_baseline": model_m["rmse"] <= base_m["rmse"],
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
    baseline_preds: np.ndarray | None = None,
) -> dict[str, Any]:
    """Compose full evaluation report: metrics + feature importance + baseline comparison."""
    metrics = compute_metrics(model, X, y)
    importance = feature_importance_report(model, feature_names)
    report: dict[str, Any] = {"metrics": metrics, "feature_importance": importance}

    if baseline_preds is not None:
        report["baseline_comparison"] = compute_baseline_comparison(model, X, y, baseline_preds)

    logger.info(
        "Evaluation: RMSE=%.4f MAE=%.4f R2=%.4f",
        metrics["rmse"], metrics["mae"], metrics["r2"],
    )
    return report
