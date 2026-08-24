"""
SAKSHA – Hotspot Prediction Training Pipeline

Responsibilities
----------------
- Load dataframe from PostgreSQL
- Call build_features()
- TimeSeriesSplit cross-validation
- LightGBM + Optuna hyperparameter search
- Train final model on full training set
- Evaluate on held-out test set
- Save artifacts via save_model.py
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sqlalchemy import create_engine

import json
from pathlib import Path

import lightgbm as lgb
import optuna

from app.ai.features.hotspot.feature_engineering import build_features
from app.ai.pipelines.hotspot.evaluate import compute_metrics
from app.ai.pipelines.hotspot.save_model import save_artifacts
from app.core.config import settings

_FEATURE_COLUMNS_PATH = (
    Path(__file__).resolve().parents[3] / "models" / "hotspot" / "feature_columns.json"
)


def _load_feature_columns() -> list[str]:
    """Feature list used for training.

    The checked-in feature_columns.json documents the artifact currently
    deployed for inference. At training time the code-level FEATURE_COLUMNS
    (which may include newer engineered features) is the source of truth;
    save_artifacts() then writes a matching feature_columns.json alongside
    the freshly trained model.
    """
    from app.ai.features.hotspot.feature_engineering import FEATURE_COLUMNS

    if _FEATURE_COLUMNS_PATH.exists():
        try:
            stored = json.loads(_FEATURE_COLUMNS_PATH.read_text())
        except Exception:
            stored = None
        if isinstance(stored, list):
            if stored == FEATURE_COLUMNS:
                return list(stored)
            logger.warning(
                "feature_columns.json has %d features but FEATURE_COLUMNS defines %d — "
                "training with the current FEATURE_COLUMNS set.",
                len(stored), len(FEATURE_COLUMNS),
            )
    return list(FEATURE_COLUMNS)

optuna.logging.set_verbosity(optuna.logging.WARNING)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_SPLITS = 5
TEST_RATIO = 0.20
N_TRIALS = 30
RANDOM_STATE = 42

QUERY = """
SELECT
    cm."CaseMasterID",
    cm."CrimeRegisteredDate",
    cm."IncidentFromDate",
    cm."latitude",
    cm."longitude",
    cm."PoliceStationID",
    cm."GravityOffenceID",
    cm."CrimeMajorHeadID",
    cm."CrimeMinorHeadID",
    cm."CaseStatusID"
FROM "CaseMaster" cm
"""


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data() -> pd.DataFrame:
    try:
        engine = create_engine(settings.DATABASE_URL)
        df = pd.read_sql(QUERY, engine)
        logger.info("Loaded %d crime records.", len(df))
        return df
    except Exception:
        logger.exception("Failed to load crime data from database.")
        raise


# ---------------------------------------------------------------------------
# Optuna objective
# ---------------------------------------------------------------------------

def _make_objective(X: pd.DataFrame, y: pd.Series, tscv: TimeSeriesSplit):
    def objective(trial: optuna.Trial) -> float:
        params = {
            "objective": "regression",
            "random_state": RANDOM_STATE,
            "verbosity": -1,
            "n_estimators": trial.suggest_int("n_estimators", 200, 1000),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 20, 300),
            "max_depth": trial.suggest_int("max_depth", 4, 15),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 80),
        }
        scores = []
        for train_idx, val_idx in tscv.split(X):
            model = lgb.LGBMRegressor(**params)
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            pred = model.predict(X.iloc[val_idx])
            scores.append(np.sqrt(mean_squared_error(y.iloc[val_idx], pred)))
        return float(np.mean(scores))

    return objective


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_training() -> None:
    # 1. Load & engineer features
    raw_df = load_data()
    monthly = build_features(raw_df)

    feature_columns = _load_feature_columns()

    if "TargetCrimeCount" not in monthly.columns:
        raise RuntimeError(
            "TargetCrimeCount missing from build_features() output. "
            "Ensure feature_engineering.py is up to date."
        )

    monthly = monthly.sort_values("YearMonth").reset_index(drop=True)
    X = monthly[feature_columns]
    y = monthly["TargetCrimeCount"]

    # 2. Train / test split (time-based, 80/20)
    split_idx = int(len(monthly) * (1 - TEST_RATIO))
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    logger.info(
        "Train/test split: train=%d rows, test=%d rows.",
        len(X_train), len(X_test),
    )

    # 3. Optuna hyperparameter search
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    study = optuna.create_study(direction="minimize")
    study.optimize(_make_objective(X_train, y_train, tscv), n_trials=N_TRIALS)
    logger.info("Best CV RMSE: %.4f | params: %s", study.best_value, study.best_params)

    # 4. Train final model
    best_params = {"objective": "regression", "random_state": RANDOM_STATE, "verbosity": -1,
                   **study.best_params}
    model = lgb.LGBMRegressor(**best_params)
    model.fit(X_train, y_train)

    # 5. Evaluate
    metrics = compute_metrics(model, X_test, y_test)
    logger.info("Test metrics: %s", metrics)

    # 6. Save
    save_artifacts(model, metrics, best_params)
    logger.info("Training complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_training()
