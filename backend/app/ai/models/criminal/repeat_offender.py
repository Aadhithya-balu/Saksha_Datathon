"""Repeat offender prediction model.

Predicts whether a criminal is likely to re-offend based on their feature
vector.  Uses a threshold-based logistic approximation (no external ML lib).

Interface: train / evaluate / predict / save_model / load_model
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.ai.models.criminal._metrics import binary_auc


@dataclass(frozen=True)
class RepeatOffenderPrediction:
    criminal_id: str
    will_reoffend: bool
    probability: float          # 0-1
    risk_factors: list[dict[str, Any]]


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


class RepeatOffenderPredictor:
    """Logistic-style repeat-offender predictor.

    Coefficients are estimated during train() using a single-step gradient
    update (sufficient for the feature scale used here).
    """

    def __init__(self, feature_names: list[str]) -> None:
        if not feature_names:
            raise ValueError("feature_names must be non-empty")
        self.feature_names = feature_names
        self._coef: np.ndarray | None = None
        self._intercept: float = 0.0
        self.threshold: float = 0.5

    # ── mandatory interface ───────────────────────────────────────────────────

    def train(self, X: np.ndarray, y: np.ndarray | None = None) -> None:
        """Fit coefficients.

        If y (binary labels) is provided, uses gradient descent.
        Otherwise derives a heuristic from feature correlations with
        high-activity indicators (fir_count, open_fir_count).
        """
        X = np.asarray(X, dtype=np.float64)
        n, d = X.shape
        if d != len(self.feature_names):
            raise ValueError("X column count must match feature_names")

        if y is not None:
            y = np.asarray(y, dtype=np.float64)
            self._coef, self._intercept = self._fit_gd(X, y)
        else:
            # Heuristic: weight features by their correlation with fir_count
            fir_idx = self.feature_names.index("fir_count") if "fir_count" in self.feature_names else 0
            target = X[:, fir_idx]
            corrs = np.array([
                float(np.corrcoef(X[:, i], target)[0, 1])
                if (X[:, i].std() > 1e-9 and target.std() > 1e-9) else 0.0
                for i in range(d)
            ])
            self._coef = np.nan_to_num(np.clip(corrs, 0, None), nan=0.0)
            self._coef /= (self._coef.sum() + 1e-12)
            self._intercept = -0.5

    def evaluate(self, X: np.ndarray, y_true: np.ndarray | None = None) -> dict[str, float]:
        if self._coef is None:
            raise RuntimeError("Model must be trained before evaluate")
        X = np.asarray(X, dtype=np.float64)
        probs = _sigmoid(X @ self._coef + self._intercept)
        metrics: dict[str, float] = {"mean_probability": float(probs.mean())}
        if y_true is not None:
            y = np.asarray(y_true, dtype=np.float64)
            preds = (probs >= self.threshold).astype(float)
            tp = float(np.sum((preds == 1) & (y == 1)))
            fp = float(np.sum((preds == 1) & (y == 0)))
            fn = float(np.sum((preds == 0) & (y == 1)))
            precision = tp / (tp + fp + 1e-12)
            recall = tp / (tp + fn + 1e-12)
            metrics["precision"] = round(precision, 4)
            metrics["recall"] = round(recall, 4)
            metrics["f1"] = round(2 * precision * recall / (precision + recall + 1e-12), 4)
            metrics["auc"] = round(binary_auc(probs, y.astype(bool)), 4)
        return metrics

    def predict(self, x: np.ndarray, criminal_id: str = "") -> RepeatOffenderPrediction:
        if self._coef is None:
            raise RuntimeError("Model must be trained before predict")
        x = np.asarray(x, dtype=np.float64)
        if x.ndim != 1 or x.shape[0] != len(self.feature_names):
            raise ValueError("x must be 1-D with length == n_features")

        prob = float(_sigmoid(np.array([x @ self._coef + self._intercept]))[0])
        will_reoffend = prob >= self.threshold

        contributions = np.abs(x * self._coef)
        k = min(5, len(self.feature_names))
        top_idx = np.argsort(-contributions)[:k]
        risk_factors = [
            {"feature": self.feature_names[i], "weight": float(self._coef[i]), "value": float(x[i])}
            for i in top_idx
        ]

        return RepeatOffenderPrediction(
            criminal_id=criminal_id,
            will_reoffend=will_reoffend,
            probability=round(prob, 4),
            risk_factors=risk_factors,
        )

    def save_model(self, path: str | Path) -> None:
        if self._coef is None:
            raise RuntimeError("Model must be trained before save_model")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps({
                "feature_names": self.feature_names,
                "coef": self._coef.tolist(),
                "intercept": self._intercept,
                "threshold": self.threshold,
            }),
            encoding="utf-8",
        )

    @classmethod
    def load_model(cls, path: str | Path) -> RepeatOffenderPredictor:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        m = cls(feature_names=payload["feature_names"])
        m._coef = np.asarray(payload["coef"], dtype=np.float64)
        m._intercept = float(payload["intercept"])
        m.threshold = float(payload["threshold"])
        return m

    # ── private ───────────────────────────────────────────────────────────────

    def _fit_gd(self, X: np.ndarray, y: np.ndarray, lr: float = 0.1, epochs: int = 200) -> tuple[np.ndarray, float]:
        n, d = X.shape
        coef = np.zeros(d, dtype=np.float64)
        intercept = 0.0
        for _ in range(epochs):
            logits = X @ coef + intercept
            probs = _sigmoid(logits)
            err = probs - y
            coef -= lr * (X.T @ err) / n
            intercept -= lr * err.mean()
        return coef, float(intercept)
