"""
SAKSHA – Hotspot Prediction Evaluation

Responsibilities
----------------
- RMSE, MAE, R²
- Feature importance (gain)
- SHAP values summary
- Returns structured evaluation report dict

No training. No inference. No FastAPI.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logger = logging.getLogger(__name__)


def compute_metrics(model, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float]:
    """Return RMSE, MAE, R² for a fitted model."""
    pred = model.predict(X_test)
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_test, pred))),
        "mae": float(mean_absolute_error(y_test, pred)),
        "r2": float(r2_score(y_test, pred)),
    }


def compute_baseline_metrics(y_true: pd.Series | np.ndarray, y_baseline: pd.Series | np.ndarray) -> dict[str, float]:
    """Compute RMSE, MAE, R² for simple baseline (e.g. historical spatial average)."""
    y_true_arr = np.asarray(y_true, dtype=np.float64)
    y_base_arr = np.asarray(y_baseline, dtype=np.float64)
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true_arr, y_base_arr))),
        "mae": float(mean_absolute_error(y_true_arr, y_base_arr)),
        "r2": float(r2_score(y_true_arr, y_base_arr)),
    }


def compute_hotspot_ranking_metrics(
    y_true: pd.Series | np.ndarray,
    y_pred: pd.Series | np.ndarray,
    k: int = 10,
) -> dict[str, float]:
    """Compute Top-K hotspot capture metrics: Precision@K and Hit Rate."""
    y_true_arr = np.asarray(y_true, dtype=np.float64)
    y_pred_arr = np.asarray(y_pred, dtype=np.float64)

    if len(y_true_arr) == 0 or len(y_pred_arr) == 0:
        return {"precision_at_k": 0.0, "hit_rate": 0.0, "k": k}

    k_actual = min(k, len(y_true_arr))
    top_k_pred_idx = set(np.argsort(-y_pred_arr)[:k_actual])
    top_k_true_idx = set(np.argsort(-y_true_arr)[:k_actual])

    overlap = len(top_k_pred_idx.intersection(top_k_true_idx))
    precision_at_k = float(overlap / max(1, k_actual))
    hit_rate = 1.0 if overlap > 0 else 0.0

    return {
        "precision_at_k": round(precision_at_k, 4),
        "hit_rate": round(hit_rate, 4),
        "top_k_captured": overlap,
        "k": k_actual,
    }


def feature_importance_report(model, X_test: pd.DataFrame) -> list[dict[str, Any]]:
    """Return feature importances sorted descending by gain."""
    features = X_test.columns.tolist()
    importances = model.feature_importances_
    return sorted(
        [{"feature": f, "importance": int(i)} for f, i in zip(features, importances)],
        key=lambda x: x["importance"],
        reverse=True,
    )


def shap_summary(model, X_test: pd.DataFrame) -> dict[str, float]:
    """Return mean absolute SHAP value per feature."""
    features = X_test.columns.tolist()
    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)
        mean_shap = np.abs(shap_values).mean(axis=0)
        return {f: float(v) for f, v in zip(features, mean_shap)}
    except Exception as exc:
        logger.warning("SHAP calculation skipped: %s", exc)
        return {}


def build_evaluation_report(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    baseline_preds: pd.Series | np.ndarray | None = None,
) -> dict[str, Any]:
    """Compose full evaluation report: metrics + baseline comparison + ranking + feature importance + SHAP."""
    metrics = compute_metrics(model, X_test, y_test)
    ranking = compute_hotspot_ranking_metrics(y_test, model.predict(X_test), k=10)
    importance = feature_importance_report(model, X_test)
    shap_scores = shap_summary(model, X_test)

    report: dict[str, Any] = {
        "metrics": metrics,
        "ranking_metrics": ranking,
        "feature_importance": importance,
        "shap_mean_abs": shap_scores,
    }

    if baseline_preds is not None:
        base_metrics = compute_baseline_metrics(y_test, baseline_preds)
        rmse_impr = (
            round(((base_metrics["rmse"] - metrics["rmse"]) / base_metrics["rmse"] * 100.0), 2)
            if base_metrics["rmse"] > 1e-9
            else 0.0
        )
        report["baseline_comparison"] = {
            "model_metrics": metrics,
            "baseline_metrics": base_metrics,
            "rmse_improvement_pct": rmse_impr,
            "outperforms_baseline": metrics["rmse"] <= base_metrics["rmse"],
        }

    logger.info("Evaluation report: RMSE=%.4f MAE=%.4f R2=%.4f",
                metrics["rmse"], metrics["mae"], metrics["r2"])
    return report
