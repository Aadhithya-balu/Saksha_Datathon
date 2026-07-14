from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np


@dataclass(frozen=True)
class VectorDocument:
    id: str
    text: str
    title: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class VectorHit:
    document_id: str
    title: str
    score: float
    content: str
    metadata: dict[str, Any]


class InMemoryVectorStore:
    def __init__(self, dimensions: int = 128) -> None:
        self.dimensions = dimensions
        self._documents: list[VectorDocument] = []
        self._embeddings: np.ndarray | None = None

    def index(self, documents: Iterable[VectorDocument]) -> None:
        self._documents = list(documents)
        if not self._documents:
            self._embeddings = np.zeros((0, self.dimensions), dtype=np.float64)
            return
        self._embeddings = np.vstack([self._embed(doc.text) for doc in self._documents])

    def search(self, query: str, top_k: int = 4) -> list[VectorHit]:
        if self._embeddings is None:
            return []
        if not query.strip() or not len(self._documents):
            return []
        query_vec = self._embed(query)
        scores = self._cosine_similarity(self._embeddings, query_vec)
        top_idx = np.argsort(-scores)[:top_k]
        hits = []
        for idx in top_idx:
            if scores[idx] <= 0:
                continue
            doc = self._documents[idx]
            hits.append(
                VectorHit(
                    document_id=doc.id,
                    title=doc.title,
                    score=round(float(scores[idx]), 4),
                    content=doc.text,
                    metadata=doc.metadata,
                )
            )
        return hits

    def save(self, path: str | Path) -> None:
        payload = {
            "dimensions": self.dimensions,
            "documents": [
                {"id": doc.id, "text": doc.text, "title": doc.title, "metadata": doc.metadata}
                for doc in self._documents
            ],
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> InMemoryVectorStore:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        store = cls(dimensions=int(payload.get("dimensions", 128)))
        documents = [
            VectorDocument(
                id=item["id"],
                text=item["text"],
                title=item["title"],
                metadata=dict(item.get("metadata", {})),
            )
            for item in payload.get("documents", [])
        ]
        store.index(documents)
        return store

    def _embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dimensions, dtype=np.float64)
        for token in self._tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            slot = int.from_bytes(digest[:8], "big") % self.dimensions
            vec[slot] += 1.0
        norm = float(np.linalg.norm(vec))
        return vec if norm < 1e-12 else vec / norm

    def _cosine_similarity(self, matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
        if matrix.size == 0:
            return np.zeros(0, dtype=np.float64)
        return matrix @ vector

    def _tokenize(self, text: str) -> list[str]:
        return [
            token.strip(".,:;!?()[]{}\"'").lower()
            for token in text.split()
            if token.strip(".,:;!?()[]{}\"'")
        ]
