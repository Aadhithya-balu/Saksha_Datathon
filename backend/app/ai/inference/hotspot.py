"""
SAKSHA – Hotspot Prediction Inference

Responsibilities
----------------
- Load model (joblib)
- Load feature_columns.json and model_metadata.json
- Call build_features() on raw input records
- Predict next-month crime count per H3 cell
- Generate Risk Level (Low / Medium / High / Critical)
- Generate Confidence Score
- Return structured list of prediction dicts

No FastAPI routes. No training.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.ai.features.hotspot.feature_engineering import (
    REQUIRED_INPUT_COLUMNS,
    build_features,
)

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "hotspot"

# Risk thresholds (crime count per H3 cell per month)
_RISK_THRESHOLDS = {"Low": 5, "Medium": 15, "High": 30}  # ≥30 → Critical


# ---------------------------------------------------------------------------
# Lazy-loaded singletons
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_model():
    path = MODEL_DIR / "hotspot_model.pkl"
    if not path.exists():
        logger.warning("Hotspot model not found at %s — using rule-based fallback.", path)
        return None
    logger.info("Loading hotspot model from %s", path)
    return joblib.load(path)


@lru_cache(maxsize=1)
def _load_metadata() -> dict[str, Any]:
    path = MODEL_DIR / "model_metadata.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_training_metrics() -> dict[str, float]:
    """Load training_metrics.json as the guaranteed source of RMSE/MAE/R²."""
    path = MODEL_DIR / "training_metrics.json"
    if not path.exists():
        # Fall back to metadata if training_metrics.json is absent
        meta = _load_metadata()
        return {
            "rmse": float(meta.get("rmse") or 1.0),
            "mae": float(meta.get("mae") or 0.0),
            "r2": float(meta.get("r2") or 0.0),
        }
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_feature_columns() -> list[str] | None:
    path = MODEL_DIR / "feature_columns.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_records(records: list[dict[str, Any]]) -> None:
    """Raise ValueError if any required column is absent from the records."""
    if not records:
        raise ValueError("records list is empty.")
    keys = set(records[0].keys())
    missing = [c for c in REQUIRED_INPUT_COLUMNS if c not in keys]
    if missing:
        raise ValueError(f"Input records missing required fields: {missing}")


def _risk_level(count: float) -> str:
    if count >= _RISK_THRESHOLDS["High"]:
        return "Critical"
    if count >= _RISK_THRESHOLDS["Medium"]:
        return "High"
    if count >= _RISK_THRESHOLDS["Low"]:
        return "Medium"
    return "Low"


def _confidence(pred: float, rmse: float) -> float:
    """Proxy confidence: 1 – normalised RMSE (clamped 0–1)."""
    if pred <= 0:
        return 0.5
    ratio = min(rmse / (pred + 1e-9), 1.0)
    return round(float(1.0 - ratio * 0.5), 4)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def predict(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run hotspot inference on a list of raw crime record dicts.

    Parameters
    ----------
    records : list of dicts matching the CaseMaster schema fields.

    Returns
    -------
    List of prediction dicts, one per H3 cell × YearMonth combination.
    Each dict contains:
        h3_cell, year_month, predicted_crime_count,
        risk_level, confidence_score
    """
    # 1. Validate before any heavy processing
    _validate_records(records)

    df = pd.DataFrame(records)
    monthly = build_features(df, include_target=False)

    model = _load_model()

    # 2. Rule-based fallback when no trained model is present
    if model is None:
        logger.warning("No trained hotspot model — using rule-based fallback.")
        results = []
        for row in monthly.itertuples(index=False):
            count = float(max(1, len(records) // max(1, len(monthly))))
            results.append({
                "h3_cell": row.H3Cell,
                "year_month": row.YearMonth,
                "predicted_crime_count": round(count, 4),
                "risk_level": _risk_level(count),
                "confidence_score": 0.5,
            })
        return results

    # 3. Model-based inference
    feature_cols = _load_feature_columns()
    rmse = _load_training_metrics().get("rmse") or 1.0

    X = monthly[feature_cols]
    raw_preds = np.clip(model.predict(X), 0, None)

    # 4. Build results using itertuples() for performance
    results = []
    for row, pred_count in zip(monthly.itertuples(index=False), raw_preds):
        pred_count = float(pred_count)
        results.append({
            "h3_cell": row.H3Cell,
            "year_month": row.YearMonth,
            "predicted_crime_count": round(pred_count, 4),
            "risk_level": _risk_level(pred_count),
            "confidence_score": _confidence(pred_count, rmse),
        })

    logger.info("predict: %d H3-cell predictions generated.", len(results))
    return results


def get_model_info() -> dict[str, Any]:
    """Return model metadata for health/info endpoints."""
    meta = _load_metadata()
    metrics = _load_training_metrics()
    model = _load_model()
    return {
        "model_name": meta.get("model_name", "SAKSHA Hotspot Predictor"),
        "algorithm": meta.get("algorithm", "LightGBM"),
        "version": meta.get("version", "untrained"),
        "h3_resolution": meta.get("h3_resolution"),
        "prediction_target": meta.get("prediction_target"),
        "feature_count": meta.get("feature_count"),
        "trained_on": meta.get("trained_on"),
        "rmse": metrics.get("rmse"),
        "mae": metrics.get("mae"),
        "r2": metrics.get("r2"),
        "model_loaded": model is not None,
    }
