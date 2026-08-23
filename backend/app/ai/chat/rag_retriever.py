"""Vector retrieval augmentation for the AI chat pipeline (issue #122).

Bridges the database-grounded RAG stack (`build_rag_documents` + in-memory
vector store) into `ChatOrchestrator`, so free-text questions recall relevant
FIRs, criminals, evidence, and cases even when intent routing has no exact
structured match. Stateless by design: the index is rebuilt per query from
live database rows, so results never go stale and tests stay isolated.
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.ai.chat.backend_fetcher import BackendResult
from app.ai.vectorstore.memory import InMemoryVectorStore, VectorDocument

_TOP_K = 5
# Cheap first-pass floor; real filtering happens via the shared-stem rule
# below, which kills SHA-256 hashing-trick collision noise.
_MIN_SCORE = 0.1
_SNIPPET_LIMIT = 280
_MIN_SHARED_STEMS = 2
# Validator-known identifier keys so IDs cited from retrieved documents are
# treated as grounded by ResponseValidator.
_ID_METADATA_KEYS = ("id", "fir_number", "case_number", "name")


class RagRetriever:
    """Retrieves database records relevant to a free-text question."""

    def fetch(self, db: Session, message: str, *, top_k: int = _TOP_K) -> BackendResult | None:
        try:
            from app.services.rag.rag_service import build_rag_documents

            documents = build_rag_documents(db)
            if not documents:
                return None

            store = InMemoryVectorStore()
            store.index(self._to_vector_documents(documents))
            # Over-fetch: cosine on hash embeddings is noisy, so genuine
            # matches must be filtered/ranked AFTER retrieval, not truncated
            # away by top_k beforehand.
            query_stems = self._word_stems(message)
            overlaps: list[tuple[int, float, Any]] = []
            for hit in store.search(self._normalize(message), top_k=max(top_k * 8, 40)):
                if hit.score < _MIN_SCORE:
                    continue
                shared = query_stems & self._word_stems(self._display_text(hit))
                if len(shared) >= _MIN_SHARED_STEMS:
                    overlaps.append((len(shared), hit.score, hit))
            if not overlaps:
                return None
            overlaps.sort(key=lambda item: (-item[0], -item[1]))
            hits = [item[2] for item in overlaps[:top_k]]

            lines = [self._display_text(hit)[:_SNIPPET_LIMIT] for hit in hits]
            known_ids = []
            for hit in hits:
                entry = {key: str(hit.metadata[key]) for key in _ID_METADATA_KEYS if hit.metadata.get(key)}
                if entry:
                    known_ids.append(entry)

            return BackendResult(
                source="postgres",
                data_type="vector_retrieval",
                content="\n".join(lines),
                raw_data=known_ids or None,
            )
        except Exception:
            # Retrieval augmentation must never break the chat pipeline.
            return None

    @staticmethod
    def _to_vector_documents(documents: list[dict]) -> list[VectorDocument]:
        records: list[VectorDocument] = []
        for index, doc in enumerate(documents):
            original_text = str(doc.get("content") or "")
            if not original_text.strip():
                continue
            records.append(
                VectorDocument(
                    id=str(doc.get("id") or f"doc-{index}"),
                    # Hyphens/slashes become spaces so IDs like FIR-2026-001
                    # and queries like "FIR 2026/001" share real tokens.
                    text=RagRetriever._normalize(original_text),
                    title=str(doc.get("title") or f"Document {index + 1}"),
                    metadata={
                        **{k: v for k, v in doc.items() if k not in {"id", "content"}},
                        "_display": original_text,
                    },
                )
            )
        return records

    @staticmethod
    def _display_text(hit) -> str:
        return str(hit.metadata.get("_display", hit.content))

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[-/]+", " ", text.lower())

    @staticmethod
    def _word_stems(text: str) -> set[str]:
        words = re.findall(r"[a-z0-9]{3,}", RagRetriever._normalize(text))
        return {
            word[:-1] if len(word) > 3 and word.endswith("s") else word
            for word in words
        }
