"""Criminal clustering model.

Groups criminals into behavioural clusters using k-means.
Each cluster receives a human-readable label derived from its centroid.

Interface: train / evaluate / predict / save_model / load_model
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ClusterPrediction:
    criminal_id: str
    cluster_id: int
    cluster_label: str
    distance_to_centroid: float
    cluster_profile: dict[str, Any]


class CriminalClusteringModel:
    """Mini k-means clustering for criminal behavioural profiling."""

    def __init__(self, feature_names: list[str], n_clusters: int = 4) -> None:
        if not feature_names:
            raise ValueError("feature_names must be non-empty")
        self.feature_names = feature_names
        self.n_clusters = n_clusters
        self._centroids: np.ndarray | None = None
        self._labels: list[str] = []

    # ── mandatory interface ───────────────────────────────────────────────────

    def train(self, X: np.ndarray, max_iter: int = 100) -> None:
        X = np.asarray(X, dtype=np.float64)
        n, d = X.shape
        if d != len(self.feature_names):
            raise ValueError("X column count must match feature_names")

        k = min(self.n_clusters, n)
        rng = np.random.default_rng(42)
        centroids = X[rng.choice(n, k, replace=False)].copy()

        for _ in range(max_iter):
            dists = np.linalg.norm(X[:, None, :] - centroids[None, :, :], axis=2)
            assignments = dists.argmin(axis=1)
            new_centroids = np.array([
                X[assignments == c].mean(axis=0) if (assignments == c).any() else centroids[c]
                for c in range(k)
            ])
            if np.allclose(centroids, new_centroids, atol=1e-6):
                break
            centroids = new_centroids

        self._centroids = centroids
        self._labels = [self._label_cluster(centroids[c]) for c in range(k)]

    def evaluate(self, X: np.ndarray, y_true: np.ndarray | None = None) -> dict[str, float]:
        if self._centroids is None:
            raise RuntimeError("Model must be trained before evaluate")
        X = np.asarray(X, dtype=np.float64)
        dists = np.linalg.norm(X[:, None, :] - self._centroids[None, :, :], axis=2)
        assignments = dists.argmin(axis=1)
        inertia = float(sum(
            float(np.linalg.norm(X[i] - self._centroids[assignments[i]]) ** 2)
            for i in range(len(X))
        ))
        return {
            "inertia": round(inertia, 4),
            "n_clusters": float(len(self._centroids)),
            "mean_cluster_size": round(float(len(X) / len(self._centroids)), 3),
        }

    def predict(self, x: np.ndarray, criminal_id: str = "") -> ClusterPrediction:
        if self._centroids is None:
            raise RuntimeError("Model must be trained before predict")
        x = np.asarray(x, dtype=np.float64)
        if x.ndim != 1 or x.shape[0] != len(self.feature_names):
            raise ValueError("x must be 1-D with length == n_features")

        dists = np.linalg.norm(self._centroids - x, axis=1)
        cluster_id = int(dists.argmin())
        centroid = self._centroids[cluster_id]
        profile = {fn: round(float(centroid[i]), 3) for i, fn in enumerate(self.feature_names)}

        return ClusterPrediction(
            criminal_id=criminal_id,
            cluster_id=cluster_id,
            cluster_label=self._labels[cluster_id],
            distance_to_centroid=round(float(dists[cluster_id]), 4),
            cluster_profile=profile,
        )

    def save_model(self, path: str | Path) -> None:
        if self._centroids is None:
            raise RuntimeError("Model must be trained before save_model")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps({
                "feature_names": self.feature_names,
                "n_clusters": self.n_clusters,
                "centroids": self._centroids.tolist(),
                "labels": self._labels,
            }),
            encoding="utf-8",
        )

    @classmethod
    def load_model(cls, path: str | Path) -> CriminalClusteringModel:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        m = cls(feature_names=payload["feature_names"], n_clusters=payload["n_clusters"])
        m._centroids = np.asarray(payload["centroids"], dtype=np.float64)
        m._labels = list(payload["labels"])
        return m

    # ── private ───────────────────────────────────────────────────────────────

    def _label_cluster(self, centroid: np.ndarray) -> str:
        fn = self.feature_names
        get = lambda name: float(centroid[fn.index(name)]) if name in fn else 0.0  # noqa: E731
        fir_val = get("fir_count")
        multi_val = get("multi_district_flag")
        high_val = get("high_severity_count")
        status_val = get("status_encoded")

        if fir_val >= 3 and multi_val >= 0.5:
            return "ORGANISED_NETWORK"
        if fir_val >= 2 and high_val >= 1:
            return "HIGH_SEVERITY_REPEAT"
        if status_val >= 1.8:
            return "ACTIVE_FUGITIVE"
        return "LOW_ACTIVITY"
