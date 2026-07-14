"""
SAKSHA – District Crime Risk Scoring Model

Predicts a 0-100 risk score per district for the next month.
Algorithm: RandomForestRegressor (scikit-learn).

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
class RiskPrediction:
    district: str
    year_month: str
    risk_score: float        # 0-100 normalised
    predicted_crime_count: float
    risk_band: str           # LOW / MEDIUM / HIGH / CRITICAL
    confidence: float        # 0-1
    top_factors: list[dict[str, Any]]


def _band(score: float) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


class DistrictRiskModel:
    """RandomForest-based district risk scorer."""

    def __init__(self, feature_names: list[str]) -> None:
        if not feature_names:
            raise ValueError("feature_names must be non-empty")
        self.feature_names = feature_names
        self._model = None
        self._score_min: float = 0.0
        self._score_max: float = 1.0

    # ── mandatory interface ───────────────────────────────────────────────────

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        from sklearn.ensemble import RandomForestRegressor  # lazy import
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        self._model = RandomForestRegressor(
            n_estimators=200,
            max_depth=10,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        )
        self._model.fit(X, y)
        preds = self._model.predict(X)
        self._score_min = float(preds.min())
        self._score_max = float(preds.max())
        logger.info("DistrictRiskModel trained on %d samples.", len(y))

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score  # lazy
        if self._model is None:
            raise RuntimeError("Model must be trained before evaluate")
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        preds = self._model.predict(X)
        return {
            "rmse": float(np.sqrt(mean_squared_error(y, preds))),
            "mae": float(mean_absolute_error(y, preds)),
            "r2": float(r2_score(y, preds)),
        }

    def predict(
        self,
        x: np.ndarray,
        district: str = "",
        year_month: str = "",
    ) -> RiskPrediction:
        if self._model is None:
            raise RuntimeError("Model must be trained before predict")
        x = np.asarray(x, dtype=np.float64).reshape(1, -1)
        raw_pred = float(self._model.predict(x)[0])
        risk_score = self._to_100(raw_pred)

        importances = self._model.feature_importances_
        top_idx = np.argsort(-importances)[:5]
        top_factors = [
            {"feature": self.feature_names[i], "importance": round(float(importances[i]), 4)}
            for i in top_idx
        ]
        confidence = min(1.0, float(np.sum(x[0] != 0) / len(self.feature_names)))

        return RiskPrediction(
            district=district,
            year_month=year_month,
            risk_score=round(risk_score, 2),
            predicted_crime_count=round(max(raw_pred, 0.0), 2),
            risk_band=_band(risk_score),
            confidence=round(confidence, 3),
            top_factors=top_factors,
        )

    def predict_batch(self, df: pd.DataFrame) -> list[RiskPrediction]:
        from app.ai.features.risk.feature_engineering import RISK_FEATURE_COLUMNS
        results = []
        for row in df.itertuples(index=False):
            x = np.array([getattr(row, c) for c in RISK_FEATURE_COLUMNS], dtype=np.float64)
            results.append(self.predict(
                x,
                district=getattr(row, "district", ""),
                year_month=getattr(row, "year_month", ""),
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
            json.dumps({
                "feature_names": self.feature_names,
                "score_min": self._score_min,
                "score_max": self._score_max,
            }),
            encoding="utf-8",
        )

    @classmethod
    def load_model(cls, path: str | Path) -> DistrictRiskModel:
        out = Path(path)
        meta_path = out.parent / (out.stem + "_meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        m = cls(feature_names=meta["feature_names"])
        m._model = joblib.load(out)
        m._score_min = float(meta["score_min"])
        m._score_max = float(meta["score_max"])
        return m

    def _to_100(self, raw: float) -> float:
        span = self._score_max - self._score_min
        if span < 1e-9:
            return 50.0
        return float(np.clip((raw - self._score_min) / span * 100.0, 0.0, 100.0))
