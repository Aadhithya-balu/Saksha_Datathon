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
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sqlalchemy import create_engine

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import lightgbm as lgb
try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
except ImportError:
    optuna = None
    HAS_OPTUNA = False

from app.ai.features.hotspot.feature_engineering import build_features
from app.ai.pipelines.hotspot.evaluate import compute_metrics
from app.ai.pipelines.hotspot.save_model import save_artifacts
from app.core.config import settings

_FEATURE_COLUMNS_PATH = (
    Path(__file__).resolve().parents[3] / "models" / "hotspot" / "feature_columns.json"
)


def _load_feature_columns() -> list[str]:
    """Feature list used for training matching feature_columns.json."""
    from app.ai.features.hotspot.feature_engineering import LEGACY_FEATURE_COLUMNS

    if _FEATURE_COLUMNS_PATH.exists():
        try:
            stored = json.loads(_FEATURE_COLUMNS_PATH.read_text(encoding="utf-8"))
            if isinstance(stored, list) and len(stored) > 0:
                return list(stored)
        except Exception:
            pass
    return list(LEGACY_FEATURE_COLUMNS)


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_SPLITS = 5
TEST_RATIO = 0.20
N_TRIALS = 30
RANDOM_STATE = 42

QUERY_CASEMASTER = """
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

QUERY_CRIME_CASES = """
SELECT
    cc.id AS "CaseMasterID",
    cc.created_at AS "CrimeRegisteredDate",
    cc.occurred_at AS "IncidentFromDate",
    l.latitude AS "latitude",
    l.longitude AS "longitude",
    COALESCE(l.station, '1') AS "PoliceStationID",
    CASE
        WHEN cc.priority = 'critical' THEN 4
        WHEN cc.priority = 'high' THEN 3
        WHEN cc.priority = 'medium' THEN 2
        ELSE 1
    END AS "GravityOffenceID",
    COALESCE(cc.category_id, '1') AS "CrimeMajorHeadID",
    1 AS "CrimeMinorHeadID",
    1 AS "CaseStatusID"
FROM crime_cases cc
JOIN locations l ON cc.location_id = l.id
"""


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data() -> pd.DataFrame:
    """Load crime records from PostgreSQL (CaseMaster or crime_cases join) or SQLite fallback."""
    candidate_urls = [
        settings.DATABASE_URL,
        "sqlite:///saksha.db",
        "sqlite:///./saksha.db",
        "sqlite:///backend/saksha.db",
        "sqlite:///saksha_fallback.db",
        "sqlite:///backend/saksha_fallback.db",
    ]
    for db_url in candidate_urls:
        if not db_url:
            continue
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                try:
                    df = pd.read_sql(QUERY_CASEMASTER, conn)
                    logger.info("Loaded %d records from CaseMaster (%s).", len(df), db_url)
                    return df
                except Exception:
                    df = pd.read_sql(QUERY_CRIME_CASES, conn)
                    logger.info("Loaded %d records from crime_cases join (%s).", len(df), db_url)
                    return df
        except Exception:
            continue
    raise RuntimeError("Failed to load hotspot crime data from database.")


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

def run_training(*, publish_active: bool = True, artifact_root: Path | None = None) -> dict:
    from app.ai.pipelines.hotspot.evaluate import (
        build_evaluation_report,
        compute_baseline_metrics,
        compute_hotspot_ranking_metrics,
        compute_metrics,
    )

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

    # 3. Hyperparameter selection (Optuna if available, robust configuration otherwise)
    if HAS_OPTUNA and len(X_train) >= N_SPLITS * 2:
        tscv = TimeSeriesSplit(n_splits=min(N_SPLITS, max(2, len(X_train) // 4)))
        study = optuna.create_study(direction="minimize")
        study.optimize(_make_objective(X_train, y_train, tscv), n_trials=min(N_TRIALS, 10))
        best_params = {"objective": "regression", "random_state": RANDOM_STATE, "verbosity": -1,
                       **study.best_params}
    else:
        best_params = {
            "objective": "regression",
            "random_state": RANDOM_STATE,
            "verbosity": -1,
            "n_estimators": 100,
            "learning_rate": 0.03,
            "num_leaves": 15,
            "min_child_samples": 5,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
        }

    # 4. Train final model
    model = lgb.LGBMRegressor(**best_params)
    model.fit(X_train, y_train)

    # 5. Baseline and Evaluation
    # Spatial baseline: historical moving average (RollingMean3) or mean of target
    if "RollingMean3" in X_test.columns:
        baseline_preds = X_test["RollingMean3"].fillna(y_train.mean())
    else:
        baseline_preds = np.full_like(y_test, fill_value=float(y_train.mean()) if len(y_train) > 0 else 1.0)

    eval_report = build_evaluation_report(model, X_test, y_test, baseline_preds=baseline_preds)
    metrics = eval_report["metrics"]
    ranking_metrics = eval_report.get("ranking_metrics", {})
    baseline_comparison = eval_report.get("baseline_comparison", {})

    logger.info("Test metrics: %s", metrics)
    logger.info("Ranking metrics: %s", ranking_metrics)

    # 6. Save
    date_min = str(pd.to_datetime(raw_df["IncidentFromDate"]).min())[:10] if not raw_df.empty else "N/A"
    date_max = str(pd.to_datetime(raw_df["IncidentFromDate"]).max())[:10] if not raw_df.empty else "N/A"
    training_period = f"{date_min} to {date_max}"

    version_dir = None
    temp_dir_ctx = TemporaryDirectory() if not publish_active else None
    try:
        if not publish_active:
            root = artifact_root or Path(temp_dir_ctx.name)
            version_dir = root / datetime.now().strftime("%Y%m%d_%H%M%S")
        artifacts_dir = save_artifacts(
            model=model,
            metrics=metrics,
            best_params=best_params,
            feature_columns=feature_columns,
            training_rows=len(monthly),
            ranking_metrics=ranking_metrics,
            baseline_comparison=baseline_comparison,
            training_period=training_period,
            validation_period="Chronological Holdout (20%)",
            version_dir=version_dir,
            publish_active=publish_active,
        )
    finally:
        if temp_dir_ctx is not None:
            temp_dir_ctx.cleanup()
    logger.info("Training complete.")
    return {
        "metrics": metrics,
        "ranking_metrics": ranking_metrics,
        "baseline_comparison": baseline_comparison,
        "artifacts_dir": str(artifacts_dir),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_training()
