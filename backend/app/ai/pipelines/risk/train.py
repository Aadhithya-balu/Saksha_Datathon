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
    """Load real crime records from PostgreSQL (or local fallback DB)."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            df = pd.read_sql(QUERY, conn)
        logger.info("Loaded %d crime records from primary database.", len(df))
        return df
    except Exception as exc:
        logger.warning("Primary DB connection failed (%s), trying SQLite fallback...", exc)
        for sqlite_path in ("sqlite:///saksha_fallback.db", "sqlite:///backend/saksha_fallback.db"):
            try:
                engine = create_engine(sqlite_path)
                with engine.connect() as conn:
                    df = pd.read_sql(QUERY, conn)
                logger.info("Loaded %d crime records from fallback SQLite database.", len(df))
                return df
            except Exception:
                continue
        raise


def _split(df: pd.DataFrame, feature_cols: list[str], target_col: str):
    """Time-aware chronological train-test split."""
    df = df.sort_values("year_month").reset_index(drop=True)
    X = df[feature_cols].values
    y = df[target_col].values
    split_idx = int(len(df) * (1 - TEST_RATIO))
    return X[:split_idx], X[split_idx:], y[:split_idx], y[split_idx:]


def run_training() -> dict:
    from app.ai.pipelines.risk.evaluate import compute_baseline_comparison

    raw_df = load_data()

    date_min = str(pd.to_datetime(raw_df["occurred_at"]).min())[:10] if not raw_df.empty else "N/A"
    date_max = str(pd.to_datetime(raw_df["occurred_at"]).max())[:10] if not raw_df.empty else "N/A"
    training_period = f"{date_min} to {date_max}"

    # ── Risk model ────────────────────────────────────────────────────────────
    risk_df = build_risk_features(raw_df, include_target=True)
    X_tr, X_te, y_tr, y_te = _split(risk_df, RISK_FEATURE_COLUMNS, "TargetRiskScore")

    risk_model = DistrictRiskModel(feature_names=RISK_FEATURE_COLUMNS)
    risk_model.train(X_tr, y_tr)

    # Baseline for risk: mean historical risk score from training set
    baseline_risk_val = float(np.mean(y_tr)) if len(y_tr) > 0 else 50.0
    baseline_risk_preds = np.full_like(y_te, fill_value=baseline_risk_val)
    risk_comparison = compute_baseline_comparison(risk_model._model, X_te, y_te, baseline_risk_preds)
    risk_metrics = risk_comparison["model_metrics"]
    logger.info("Risk model test metrics: %s (vs baseline: %s)", risk_metrics, risk_comparison["baseline_metrics"])

    # ── Forecast model ────────────────────────────────────────────────────────
    forecast_df = build_forecast_features(raw_df, include_target=True)
    Xf_tr, Xf_te, yf_tr, yf_te = _split(forecast_df, FORECAST_FEATURE_COLUMNS, "TargetCrimeCount")

    forecast_model = DistrictForecastModel(feature_names=FORECAST_FEATURE_COLUMNS)
    forecast_model.train(Xf_tr, yf_tr)

    # Baseline for forecast: lag_1 value if available in feature column, else mean count
    lag1_col_idx = FORECAST_FEATURE_COLUMNS.index("lag_1") if "lag_1" in FORECAST_FEATURE_COLUMNS else None
    if lag1_col_idx is not None and len(Xf_te) > 0:
        baseline_forecast_preds = Xf_te[:, lag1_col_idx]
    else:
        baseline_forecast_preds = np.full_like(yf_te, fill_value=float(np.mean(yf_tr)) if len(yf_tr) > 0 else 1.0)
    
    forecast_comparison = compute_baseline_comparison(forecast_model._model, Xf_te, yf_te, baseline_forecast_preds)
    forecast_metrics = forecast_comparison["model_metrics"]
    logger.info("Forecast model test metrics: %s (vs baseline: %s)", forecast_metrics, forecast_comparison["baseline_metrics"])

    # ── Save ──────────────────────────────────────────────────────────────────
    save_artifacts(
        risk_model=risk_model,
        forecast_model=forecast_model,
        risk_metrics=risk_metrics,
        forecast_metrics=forecast_metrics,
        risk_feature_columns=RISK_FEATURE_COLUMNS,
        forecast_feature_columns=FORECAST_FEATURE_COLUMNS,
        training_rows=len(risk_df),
        risk_baseline_comparison=risk_comparison,
        forecast_baseline_comparison=forecast_comparison,
        training_period=training_period,
        validation_period="Chronological Holdout (20%)",
    )
    logger.info("Training complete.")
    return {
        "risk": risk_metrics,
        "forecast": forecast_metrics,
        "risk_baseline": risk_comparison,
        "forecast_baseline": forecast_comparison,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_training()
