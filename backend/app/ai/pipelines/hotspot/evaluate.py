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
import shap
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
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)
    mean_shap = np.abs(shap_values).mean(axis=0)
    return {f: float(v) for f, v in zip(features, mean_shap)}


def build_evaluation_report(model, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, Any]:
    """Compose full evaluation report: metrics + feature importance + SHAP."""
    metrics = compute_metrics(model, X_test, y_test)
    importance = feature_importance_report(model, X_test)
    shap_scores = shap_summary(model, X_test)

    report = {
        "metrics": metrics,
        "feature_importance": importance,
        "shap_mean_abs": shap_scores,
    }
    logger.info("Evaluation report: RMSE=%.4f MAE=%.4f R2=%.4f",
                metrics["rmse"], metrics["mae"], metrics["r2"])
    return report
