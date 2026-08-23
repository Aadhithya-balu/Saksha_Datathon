from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class AnomalyExplanation:
    top_features: list[dict[str, Any]]
    score: float
    threshold: float
    is_anomaly: bool


@dataclass(frozen=True)
class AnomalyPrediction:
    score: float
    is_anomaly: bool
    threshold: float
    explanation: AnomalyExplanation


class AnomalyDetectorModel:
    """Lightweight anomaly detector with train/evaluate/predict/save/load interface.

    Implementation intentionally avoids adding new dependencies.
    Scoring is based on standardized feature deviation magnitude.
    """

    def __init__(self, feature_names: list[str], *, zscore_eps: float = 1e-8):
        if not feature_names:
            raise ValueError("feature_names must be non-empty")
        self.feature_names = feature_names
        self.zscore_eps = float(zscore_eps)

        self._mean: np.ndarray | None = None
        self._std: np.ndarray | None = None
        self.threshold: float | None = None

    def train(self, X: np.ndarray) -> None:
        X = np.asarray(X, dtype=np.float64)
        if X.ndim != 2:
            raise ValueError("X must be 2D array")
        self._mean = X.mean(axis=0)
        self._std = X.std(axis=0)
        # avoid divide by zero
        self._std = np.where(self._std < self.zscore_eps, 1.0, self._std)

    def evaluate(self, X: np.ndarray, y_true: np.ndarray | None = None) -> dict[str, float]:
        if self._mean is None or self._std is None:
            raise RuntimeError("Model must be trained before evaluate")

        scores = self._score_array(X)
        metrics: dict[str, float] = {}

        if y_true is None:
            # default threshold as 95th percentile
            self.threshold = float(np.percentile(scores, 95))
            metrics["threshold"] = self.threshold
            return metrics

        y_true = np.asarray(y_true).astype(bool)
        if y_true.shape[0] != scores.shape[0]:
            raise ValueError("y_true must match number of rows in X")

        # brute-force threshold search over candidate percentiles
        best_f1 = -1.0
        best_threshold = None
        for p in range(80, 100):
            t = float(np.percentile(scores, p))
            y_pred = scores >= t
            tp = float(np.sum(y_pred & y_true))
            fp = float(np.sum(y_pred & ~y_true))
            fn = float(np.sum(~y_pred & y_true))
            precision = tp / (tp + fp + 1e-12)
            recall = tp / (tp + fn + 1e-12)
            f1 = 2 * precision * recall / (precision + recall + 1e-12)
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = t

        self.threshold = float(best_threshold if best_threshold is not None else np.percentile(scores, 95))
        metrics["threshold"] = self.threshold
        metrics["f1"] = float(best_f1)
        return metrics

    def predict(self, x: np.ndarray) -> AnomalyPrediction:
        if self._mean is None or self._std is None:
            raise RuntimeError("Model must be trained before predict")
        if self.threshold is None:
            # fallback default
            self.threshold = float(np.percentile(self._score_array(np.expand_dims(x, axis=0)), 95))

        x = np.asarray(x, dtype=np.float64)
        if x.ndim != 1:
            raise ValueError("x must be 1D")
        if x.shape[0] != len(self.feature_names):
            raise ValueError("x feature dimension mismatch")

        score, per_feature = self._score_vector(x)
        is_anomaly = bool(score >= float(self.threshold))

        # explainability: top-k standardized absolute deviations
        abs_dev = per_feature
        k = min(5, abs_dev.shape[0])
        top_idx = np.argsort(-abs_dev)[:k]
        top_features = [
            {
                "feature": self.feature_names[i],
                "abs_deviation": float(abs_dev[i]),
            }
            for i in top_idx
        ]

        explanation = AnomalyExplanation(
            top_features=top_features,
            score=float(score),
            threshold=float(self.threshold),
            is_anomaly=is_anomaly,
        )
        return AnomalyPrediction(
            score=float(score),
            is_anomaly=is_anomaly,
            threshold=float(self.threshold),
            explanation=explanation,
        )

    def save_model(self, path: str | Path) -> None:
        if self._mean is None or self._std is None:
            raise RuntimeError("Model must be trained before save_model")
        if self.threshold is None:
            raise RuntimeError("Model threshold must be set before save_model")

        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "feature_names": self.feature_names,
            "mean": self._mean.tolist(),
            "std": self._std.tolist(),
            "threshold": float(self.threshold),
        }
        out_path.write_text(json.dumps(payload), encoding="utf-8")

    @classmethod
    def load_model(cls, path: str | Path) -> AnomalyDetectorModel:
        in_path = Path(path)
        payload = json.loads(in_path.read_text(encoding="utf-8"))

        model = cls(feature_names=list(payload["feature_names"]))
        model._mean = np.asarray(payload["mean"], dtype=np.float64)
        model._std = np.asarray(payload["std"], dtype=np.float64)
        model.threshold = float(payload["threshold"])
        return model

    def _score_vector(self, x: np.ndarray) -> tuple[float, np.ndarray]:
        # per-feature standardized deviation magnitude
        z = (x - self._mean) / (self._std + self.zscore_eps)
        abs_dev = np.abs(z)

        # overall score is L2 magnitude of z deviations
        score = float(np.linalg.norm(z, ord=2))
        return score, abs_dev

    def _score_array(self, X: np.ndarray) -> np.ndarray:
        if self._mean is None or self._std is None:
            raise RuntimeError("Model must be trained")

        z = (X - self._mean) / (self._std + self.zscore_eps)
        scores = np.linalg.norm(z, axis=1)
        return scores

