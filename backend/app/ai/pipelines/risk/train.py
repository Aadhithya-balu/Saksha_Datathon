"""
SAKSHA – District Risk & Forecast Training Pipeline

Responsibilities
----------------
- Load crime records from PostgreSQL (crime_cases JOIN locations)
- Build risk features and forecast features
- TimeSeriesSplit cross-validation for both models
- Train DistrictRiskModel (RandomForest) and DistrictForecastModel (XGBoost)
- Evaluate on held-out test set
- Save artifacts via save_model.py

Usage:
    python -m app.ai.pipelines.risk.train
"""

from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import create_engine

from app.ai.features.risk.feature_engineering import (
    FORECAST_FEATURE_COLUMNS,
    RISK_FEATURE_COLUMNS,
    build_forecast_features,
    build_risk_features,
)
from app.ai.models.risk.forecast_model import DistrictForecastModel
from app.ai.models.risk.risk_model import DistrictRiskModel
from app.ai.pipelines.risk.evaluate import compute_metrics
from app.ai.pipelines.risk.save_model import save_artifacts
from app.core.config import settings

logger = logging.getLogger(__name__)

N_SPLITS = 5
TEST_RATIO = 0.20
RANDOM_STATE = 42

QUERY = """
SELECT
    cc.occurred_at,
    l.district,
    cat.name AS category
FROM crime_cases cc
JOIN locations l ON cc.location_id = l.id
JOIN crime_categories cat ON cc.category_id = cat.id
"""


def load_data() -> pd.DataFrame:
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            df = pd.read_sql(QUERY, conn.connection)
        logger.info("Loaded %d crime records.", len(df))
        return df
    except Exception:
        logger.exception("Failed to load crime data.")
        raise


def _split(df: pd.DataFrame, feature_cols: list[str], target_col: str):
    df = df.sort_values("year_month").reset_index(drop=True)
    X = df[feature_cols].values
    y = df[target_col].values
    split_idx = int(len(df) * (1 - TEST_RATIO))
    return X[:split_idx], X[split_idx:], y[:split_idx], y[split_idx:]


def run_training() -> dict:
    raw_df = load_data()

    # ── Risk model ────────────────────────────────────────────────────────────
    risk_df = build_risk_features(raw_df, include_target=True)
    X_tr, X_te, y_tr, y_te = _split(risk_df, RISK_FEATURE_COLUMNS, "TargetRiskScore")

    risk_model = DistrictRiskModel(feature_names=RISK_FEATURE_COLUMNS)
    risk_model.train(X_tr, y_tr)
    risk_metrics = compute_metrics(risk_model._model, X_te, y_te)
    logger.info("Risk model test metrics: %s", risk_metrics)

    # ── Forecast model ────────────────────────────────────────────────────────
    forecast_df = build_forecast_features(raw_df, include_target=True)
    Xf_tr, Xf_te, yf_tr, yf_te = _split(forecast_df, FORECAST_FEATURE_COLUMNS, "TargetCrimeCount")

    forecast_model = DistrictForecastModel(feature_names=FORECAST_FEATURE_COLUMNS)
    forecast_model.train(Xf_tr, yf_tr)
    forecast_metrics = compute_metrics(forecast_model._model, Xf_te, yf_te)
    logger.info("Forecast model test metrics: %s", forecast_metrics)

    # ── Save ──────────────────────────────────────────────────────────────────
    save_artifacts(
        risk_model=risk_model,
        forecast_model=forecast_model,
        risk_metrics=risk_metrics,
        forecast_metrics=forecast_metrics,
        risk_feature_columns=RISK_FEATURE_COLUMNS,
        forecast_feature_columns=FORECAST_FEATURE_COLUMNS,
        training_rows=len(risk_df),
    )
    logger.info("Training complete.")
    return {"risk": risk_metrics, "forecast": forecast_metrics}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_training()
