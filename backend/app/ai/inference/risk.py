"""
SAKSHA – District Risk & Forecast Inference

Responsibilities
----------------
- Lazy-load DistrictRiskModel and DistrictForecastModel (lru_cache)
- Accept raw crime records, build features, run predictions
- Return structured dicts for the API router
- Provide a rule-based fallback when no trained model exists

No FastAPI routes. No training.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.ai.features.risk.feature_engineering import (
    FORECAST_FEATURE_COLUMNS,
    RISK_FEATURE_COLUMNS,
    build_forecast_features,
    build_risk_features,
)

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "risk"


# ---------------------------------------------------------------------------
# Lazy-loaded singletons
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_risk_model():
    path = MODEL_DIR / "risk_model.pkl"
    if not path.exists():
        return None
    try:
        from app.ai.models.risk.risk_model import DistrictRiskModel
        logger.info("Loading risk model from %s", path)
        return DistrictRiskModel.load_model(path)
    except Exception as exc:
        logger.warning("Could not load risk model: %s", exc)
        return None


@lru_cache(maxsize=1)
def _load_forecast_model():
    path = MODEL_DIR / "forecast_model.pkl"
    if not path.exists():
        return None
    try:
        from app.ai.models.risk.forecast_model import DistrictForecastModel
        logger.info("Loading forecast model from %s", path)
        return DistrictForecastModel.load_model(path)
    except Exception as exc:
        logger.warning("Could not load forecast model: %s", exc)
        return None


@lru_cache(maxsize=1)
def _load_metadata() -> dict[str, Any]:
    path = MODEL_DIR / "model_metadata.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_training_metrics() -> dict[str, Any]:
    path = MODEL_DIR / "training_metrics.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Rule-based fallback (no trained model required)
# ---------------------------------------------------------------------------

def _rule_based_risk(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Simple aggregation-based risk score when no trained model is available."""
    df = pd.DataFrame(records)
    df["occurred_at"] = pd.to_datetime(df.get("occurred_at", pd.Series(dtype=str)), errors="coerce")
    df["district"] = df.get("district", "Unknown")

    counts = df.groupby("district").size().reset_index(name="crime_count")
    max_count = max(counts["crime_count"].max(), 1)

    results = []
    for row in counts.itertuples(index=False):
        score = round(float(row.crime_count / max_count * 100), 2)
        band = "CRITICAL" if score >= 80 else "HIGH" if score >= 60 else "MEDIUM" if score >= 35 else "LOW"
        results.append({
            "district": row.district,
            "year_month": "current",
            "risk_score": score,
            "predicted_crime_count": float(row.crime_count),
            "risk_band": band,
            "confidence": 0.5,
            "top_factors": [],
            "resource_recommendation": _resource_recommendation(band),
        })
    return results


def _resource_recommendation(band: str) -> str:
    return {
        "CRITICAL": "Deploy additional patrol units; activate rapid response team.",
        "HIGH": "Increase patrol frequency; coordinate with local stations.",
        "MEDIUM": "Maintain standard patrol schedule; monitor trends.",
        "LOW": "Routine patrol sufficient.",
    }.get(band, "Routine patrol sufficient.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def predict_risk(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run district risk inference on raw crime record dicts.

    Falls back to rule-based scoring if no trained model is present.
    """
    if not records:
        raise ValueError("records list is empty.")

    risk_model = _load_risk_model()
    if risk_model is None:
        logger.warning("No trained risk model found — using rule-based fallback.")
        return _rule_based_risk(records)

    df = pd.DataFrame(records)
    feature_df = build_risk_features(df, include_target=False)

    predictions = risk_model.predict_batch(feature_df)
    return [
        {
            "district": p.district,
            "year_month": p.year_month,
            "risk_score": p.risk_score,
            "predicted_crime_count": p.predicted_crime_count,
            "risk_band": p.risk_band,
            "confidence": p.confidence,
            "top_factors": p.top_factors,
            "resource_recommendation": _resource_recommendation(p.risk_band),
        }
        for p in predictions
    ]


def predict_forecast(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run district crime count forecast on raw crime record dicts."""
    if not records:
        raise ValueError("records list is empty.")

    forecast_model = _load_forecast_model()
    if forecast_model is None:
        logger.warning("No trained forecast model found — returning aggregated counts.")
        df = pd.DataFrame(records)
        df["occurred_at"] = pd.to_datetime(df.get("occurred_at", pd.Series(dtype=str)), errors="coerce")
        df["district"] = df.get("district", "Unknown")
        counts = df.groupby("district").size().reset_index(name="crime_count")
        return [
            {
                "district": row.district,
                "year_month": "next_month",
                "predicted_crime_count": float(row.crime_count),
                "lower_bound": float(row.crime_count * 0.8),
                "upper_bound": float(row.crime_count * 1.2),
                "trend": "stable",
            }
            for row in counts.itertuples(index=False)
        ]

    df = pd.DataFrame(records)
    feature_df = build_forecast_features(df, include_target=False)
    points = forecast_model.predict_batch(feature_df)
    return [
        {
            "district": p.district,
            "year_month": p.year_month,
            "predicted_crime_count": p.predicted_crime_count,
            "lower_bound": p.lower_bound,
            "upper_bound": p.upper_bound,
            "trend": p.trend,
        }
        for p in points
    ]


def get_model_info() -> dict[str, Any]:
    """Return model metadata for health/info endpoints."""
    meta = _load_metadata()
    metrics = _load_training_metrics()
    risk_model = _load_risk_model()
    forecast_model = _load_forecast_model()
    return {
        "model_name": meta.get("model_name", "SAKSHA District Risk & Forecast"),
        "risk_algorithm": meta.get("risk_algorithm", "RandomForest"),
        "forecast_algorithm": meta.get("forecast_algorithm", "XGBoost"),
        "version": meta.get("version", "untrained"),
        "trained_on": meta.get("trained_on"),
        "training_rows": meta.get("training_rows", 0),
        "risk_metrics": metrics.get("risk", {}),
        "forecast_metrics": metrics.get("forecast", {}),
        "risk_model_loaded": risk_model is not None,
        "forecast_model_loaded": forecast_model is not None,
    }
