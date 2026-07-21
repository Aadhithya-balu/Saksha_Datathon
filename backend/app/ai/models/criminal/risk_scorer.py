"""Criminal risk scoring model.

Produces a 0-100 risk score for each criminal based on their feature vector.
Uses a learned weighted linear model trained on the feature matrix.

Interface: train / evaluate / predict / save_model / load_model
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class RiskPrediction:
    criminal_id: str
    risk_score: float          # 0-100
    risk_band: str             # LOW / MEDIUM / HIGH / CRITICAL
    top_factors: list[dict[str, Any]]
    confidence: float          # 0-1


def _band(score: float) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


class CriminalRiskScorer:
    """Weighted linear risk scorer.

    Weights are learned during train() by computing the mean contribution of
    each feature to the overall variance, then normalised so the output is
    always in [0, 100].
    """

    def __init__(self, feature_names: list[str]) -> None:
        if not feature_names:
            raise ValueError("feature_names must be non-empty")
        self.feature_names = feature_names
        self._weights: np.ndarray | None = None
        self._min: float = 0.0
        self._max: float = 1.0

    # ── mandatory interface ───────────────────────────────────────────────────

    def train(self, X: np.ndarray) -> None:
        """Fit weights from the training matrix (n_samples × n_features)."""
        X = np.asarray(X, dtype=np.float64)
        if X.ndim != 2 or X.shape[1] != len(self.feature_names):
            raise ValueError("X must be (n_samples, n_features)")

        # Weight = normalised variance contribution of each feature.
        variances = X.var(axis=0)
        total = variances.sum()
        self._weights = variances / (total + 1e-12)

        raw_scores = X @ self._weights
        self._min = float(raw_scores.min())
        self._max = float(raw_scores.max())

    def evaluate(self, X: np.ndarray, y_true: np.ndarray | None = None) -> dict[str, float]:
        """Return evaluation metrics.  Without labels, returns score statistics."""
        if self._weights is None:
            raise RuntimeError("Model must be trained before evaluate")
        X = np.asarray(X, dtype=np.float64)
        scores = self._raw_to_100(X @ self._weights)
        metrics: dict[str, float] = {
            "mean_risk_score": float(scores.mean()),
            "std_risk_score": float(scores.std()),
            "high_risk_fraction": float((scores >= 60).mean()),
        }
        if y_true is not None:
            y = np.asarray(y_true, dtype=np.float64)
            # Treat y_true as binary repeat-offender label; measure AUC proxy.
            from app.ai.models.criminal._metrics import binary_auc
            metrics["auc_proxy"] = binary_auc(scores / 100.0, y)
        return metrics

    def predict(self, x: np.ndarray, criminal_id: str = "") -> RiskPrediction:
        """Score a single criminal feature vector."""
        if self._weights is None:
            raise RuntimeError("Model must be trained before predict")
        x = np.asarray(x, dtype=np.float64)
        if x.ndim != 1 or x.shape[0] != len(self.feature_names):
            raise ValueError("x must be 1-D with length == n_features")

        raw = float(x @ self._weights)
        score = float(self._raw_to_100(np.array([raw]))[0])

        # Top contributing factors
        contributions = np.abs(x * self._weights)
        k = min(5, len(self.feature_names))
        top_idx = np.argsort(-contributions)[:k]
        top_factors = [
            {"feature": self.feature_names[i], "contribution": float(contributions[i])}
            for i in top_idx
        ]

        confidence = min(1.0, float(np.sum(x != 0) / len(self.feature_names)))

        return RiskPrediction(
            criminal_id=criminal_id,
            risk_score=round(score, 2),
            risk_band=_band(score),
            top_factors=top_factors,
            confidence=round(confidence, 3),
        )

    def save_model(self, path: str | Path) -> None:
        if self._weights is None:
            raise RuntimeError("Model must be trained before save_model")
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps({
                "feature_names": self.feature_names,
                "weights": self._weights.tolist(),
                "min": self._min,
                "max": self._max,
            }),
            encoding="utf-8",
        )

    @classmethod
    def load_model(cls, path: str | Path) -> CriminalRiskScorer:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        m = cls(feature_names=payload["feature_names"])
        m._weights = np.asarray(payload["weights"], dtype=np.float64)
        m._min = float(payload["min"])
        m._max = float(payload["max"])
        return m

    # ── helpers ───────────────────────────────────────────────────────────────

    def _raw_to_100(self, raw: np.ndarray) -> np.ndarray:
        span = self._max - self._min
        if span < 1e-12:
            return np.full_like(raw, 50.0)
        return np.clip((raw - self._min) / span * 100.0, 0.0, 100.0)
