"""
SAKSHA – District Crime Forecast Model

Forecasts next-month crime count per district using XGBoost on lag/rolling features.
Falls back to LightGBM if xgboost is unavailable.

Interface: train / evaluate / predict / save_model / load_model
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ForecastPoint:
    district: str
    year_month: str
    predicted_crime_count: float
    lower_bound: float
    upper_bound: float
    trend: str   # "up" | "stable" | "down"


def _trend(pred: float, lag1: float) -> str:
    delta = pred - lag1
    if delta > lag1 * 0.05:
        return "up"
    if delta < -lag1 * 0.05:
        return "down"
    return "stable"


class DistrictForecastModel:
    """XGBoost district crime count forecaster."""

    def __init__(self, feature_names: list[str]) -> None:
        if not feature_names:
            raise ValueError("feature_names must be non-empty")
        self.feature_names = feature_names
        self._model = None
        self._rmse: float = 1.0

    # ── mandatory interface ───────────────────────────────────────────────────

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        from sklearn.metrics import mean_squared_error  # lazy
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        self._model = self._build_model()
        self._model.fit(X, y)
        preds = self._model.predict(X)
        self._rmse = float(np.sqrt(mean_squared_error(y, preds)))
        logger.info("DistrictForecastModel trained on %d samples. Train RMSE=%.4f", len(y), self._rmse)

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score  # lazy
        if self._model is None:
            raise RuntimeError("Model must be trained before evaluate")
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        preds = self._model.predict(X)
        rmse = float(np.sqrt(mean_squared_error(y, preds)))
        self._rmse = rmse
        return {
            "rmse": rmse,
            "mae": float(mean_absolute_error(y, preds)),
            "r2": float(r2_score(y, preds)),
        }

    def predict(
        self,
        x: np.ndarray,
        district: str = "",
        year_month: str = "",
        lag1: float = 0.0,
    ) -> ForecastPoint:
        if self._model is None:
            raise RuntimeError("Model must be trained before predict")
        x = np.asarray(x, dtype=np.float64).reshape(1, -1)
        pred = float(np.clip(self._model.predict(x)[0], 0, None))
        half_ci = self._rmse * 1.96
        return ForecastPoint(
            district=district,
            year_month=year_month,
            predicted_crime_count=round(pred, 2),
            lower_bound=round(max(pred - half_ci, 0.0), 2),
            upper_bound=round(pred + half_ci, 2),
            trend=_trend(pred, lag1),
        )

    def predict_batch(self, df: pd.DataFrame) -> list[ForecastPoint]:
        from app.ai.features.risk.feature_engineering import FORECAST_FEATURE_COLUMNS
        results = []
        for row in df.itertuples(index=False):
            x = np.array([getattr(row, c) for c in FORECAST_FEATURE_COLUMNS], dtype=np.float64)
            lag1 = float(getattr(row, "lag_1", 0.0))
            results.append(self.predict(
                x,
                district=getattr(row, "district", ""),
                year_month=getattr(row, "year_month", ""),
                lag1=lag1,
            ))
        return results

    def save_model(self, path: str | Path) -> None:
        if self._model is None:
            raise RuntimeError("Model must be trained before save_model")
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, out)
        meta_path = out.parent / (out.stem + "_meta.json")
        meta_path.write_text(
            json.dumps({"feature_names": self.feature_names, "rmse": self._rmse}),
            encoding="utf-8",
        )

    @classmethod
    def load_model(cls, path: str | Path) -> DistrictForecastModel:
        out = Path(path)
        meta_path = out.parent / (out.stem + "_meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        m = cls(feature_names=meta["feature_names"])
        m._model = joblib.load(out)
        m._rmse = float(meta.get("rmse", 1.0))
        return m

    @staticmethod
    def _build_model():
        try:
            from xgboost import XGBRegressor  # lazy
            return XGBRegressor(
                n_estimators=300,
                learning_rate=0.05,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbosity=0,
            )
        except ImportError:
            import lightgbm as lgb  # lazy fallback
            return lgb.LGBMRegressor(
                n_estimators=300,
                learning_rate=0.05,
                num_leaves=63,
                random_state=42,
                verbosity=-1,
            )
