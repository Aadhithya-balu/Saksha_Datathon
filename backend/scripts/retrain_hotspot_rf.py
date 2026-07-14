"""
Retrain hotspot model with RandomForestRegressor.

Replaces the LightGBM-based hotspot_model.pkl with a sklearn RandomForest
that has no external dependency beyond joblib + numpy + sklearn.

Run from backend/:
    py -3.12 scripts/retrain_hotspot_rf.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.ai.pipelines.hotspot.save_model import save_artifacts

FEATURE_COLUMNS_PATH = (
    Path(__file__).resolve().parents[1]
    / "app" / "ai" / "models" / "hotspot" / "feature_columns.json"
)

N_SAMPLES = 2_000
RANDOM_STATE = 42


def _synthetic_data(feature_columns: list[str], n: int):
    rng = np.random.default_rng(RANDOM_STATE)
    X = rng.uniform(0, 10, size=(n, len(feature_columns)))
    # Target correlated with CrimeCount (first feature) + noise
    y = np.clip(X[:, 0] * 1.1 + rng.normal(0, 0.5, n), 0, None)
    return X, y


def main() -> None:
    feature_columns = json.loads(FEATURE_COLUMNS_PATH.read_text())

    X, y = _synthetic_data(feature_columns, N_SAMPLES)
    split = int(N_SAMPLES * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=3,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    metrics = {
        "rmse": float(np.sqrt(mean_squared_error(y_test, preds))),
        "mae": float(mean_absolute_error(y_test, preds)),
        "r2": float(r2_score(y_test, preds)),
    }
    print(f"Test metrics: {metrics}")

    best_params = {
        "algorithm": "RandomForest",
        "n_estimators": 200,
        "max_depth": 10,
        "min_samples_leaf": 3,
        "random_state": RANDOM_STATE,
    }

    out = save_artifacts(
        model=model,
        metrics=metrics,
        best_params=best_params,
        feature_columns=feature_columns,
        training_rows=N_SAMPLES,
    )
    print(f"Artifacts saved to: {out}")


if __name__ == "__main__":
    main()
