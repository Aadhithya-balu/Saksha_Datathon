"""Similar offender search model.

Builds an in-memory nearest-neighbour index over criminal feature vectors
using cosine similarity.  No external vector DB required.

Interface: train / evaluate / predict / save_model / load_model
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class SimilarOffender:
    criminal_id: str
    similarity: float   # 0-1 (1 = identical)
    rank: int


@dataclass(frozen=True)
class SimilarityPrediction:
    query_id: str
    similar: list[SimilarOffender]


class SimilarOffenderModel:
    """Cosine-similarity nearest-neighbour search over criminal feature vectors."""

    def __init__(self, feature_names: list[str]) -> None:
        if not feature_names:
            raise ValueError("feature_names must be non-empty")
        self.feature_names = feature_names
        self._index: np.ndarray | None = None   # (n, d) normalised
        self._ids: list[str] = []

    # ── mandatory interface ───────────────────────────────────────────────────

    def train(self, X: np.ndarray, ids: list[str] | None = None) -> None:
        """Index the training matrix.  ids must align with rows of X."""
        X = np.asarray(X, dtype=np.float64)
        if X.ndim != 2 or X.shape[1] != len(self.feature_names):
            raise ValueError("X must be (n_samples, n_features)")
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms = np.where(norms < 1e-12, 1.0, norms)
        self._index = X / norms
        self._ids = ids if ids is not None else [str(i) for i in range(len(X))]

    def evaluate(self, X: np.ndarray, y_true: np.ndarray | None = None) -> dict[str, float]:
        """Return mean self-similarity (sanity check) and index size."""
        if self._index is None:
            raise RuntimeError("Model must be trained before evaluate")
        # Each row should have similarity 1.0 with itself
        sims = self._index @ self._index.T
        np.fill_diagonal(sims, 0.0)
        return {
            "index_size": float(len(self._ids)),
            "mean_max_similarity": float(sims.max(axis=1).mean()),
        }

    def predict(self, x: np.ndarray, query_id: str = "", top_k: int = 5) -> SimilarityPrediction:
        """Return top-k most similar criminals to query vector x."""
        if self._index is None:
            raise RuntimeError("Model must be trained before predict")
        x = np.asarray(x, dtype=np.float64)
        if x.ndim != 1 or x.shape[0] != len(self.feature_names):
            raise ValueError("x must be 1-D with length == n_features")

        norm = float(np.linalg.norm(x))
        x_norm = x / (norm if norm > 1e-12 else 1.0)
        sims = self._index @ x_norm

        # Exclude the query itself if it's in the index
        if query_id in self._ids:
            sims[self._ids.index(query_id)] = -1.0

        k = min(top_k, len(self._ids))
        top_idx = np.argsort(-sims)[:k]

        similar = [
            SimilarOffender(
                criminal_id=self._ids[i],
                similarity=round(float(sims[i]), 4),
                rank=rank + 1,
            )
            for rank, i in enumerate(top_idx)
            if sims[i] > 0
        ]

        return SimilarityPrediction(query_id=query_id, similar=similar)

    def save_model(self, path: str | Path) -> None:
        if self._index is None:
            raise RuntimeError("Model must be trained before save_model")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps({
                "feature_names": self.feature_names,
                "index": self._index.tolist(),
                "ids": self._ids,
            }),
            encoding="utf-8",
        )

    @classmethod
    def load_model(cls, path: str | Path) -> SimilarOffenderModel:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        m = cls(feature_names=payload["feature_names"])
        m._index = np.asarray(payload["index"], dtype=np.float64)
        m._ids = list(payload["ids"])
        return m
