from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from app.ai.prompts.chat import build_answer_prompt, build_summary_prompt
from app.ai.vectorstore.memory import InMemoryVectorStore, VectorDocument


@dataclass(frozen=True)
class RetrievalChunk:
    document_id: str
    title: str
    content: str
    score: float
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ChatCitation:
    source: str
    title: str
    score: float


@dataclass(frozen=True)
class ChatResponse:
    answer: str
    summary: str
    citations: list[ChatCitation]
    entities: list[str]
    classification: str
    sources: list[str]
    chart_suggestion: str | None
    retrievals: list[RetrievalChunk]


class InvestigationChatModel:
    """Lightweight RAG assistant for investigation queries.

    Uses a deterministic local vector store so the assistant works without
    external embedding or database services.
    """

    def __init__(self, vectorstore: InMemoryVectorStore | None = None) -> None:
        self.vectorstore = vectorstore or InMemoryVectorStore()

    def train(self, documents: Iterable[dict[str, Any]]) -> None:
        records = []
        for index, doc in enumerate(documents):
            text = str(doc.get("content") or doc.get("text") or "")
            if not text.strip():
                continue
            records.append(
                VectorDocument(
                    id=str(doc.get("id") or f"doc-{index}"),
                    text=text,
                    title=str(doc.get("title") or doc.get("source") or f"Document {index + 1}"),
                    metadata={k: v for k, v in doc.items() if k not in {"id", "text", "content", "title"}},
                )
            )
        self.vectorstore.index(records)

    def evaluate(self, queries: Iterable[str]) -> dict[str, float]:
        query_list = [q for q in queries if q.strip()]
        if not query_list:
            return {"avg_retrieval_score": 0.0, "queries": 0.0}
        scores = []
        for query in query_list:
            hits = self.vectorstore.search(query, top_k=3)
            if hits:
                scores.append(float(np.mean([hit.score for hit in hits])))
        return {
            "avg_retrieval_score": round(float(np.mean(scores)) if scores else 0.0, 4),
            "queries": float(len(query_list)),
        }

    def predict(self, message: str, *, top_k: int = 4) -> ChatResponse:
        retrievals = self.vectorstore.search(message, top_k=top_k)
        summary = self._build_summary(retrievals, message)
        answer = self._build_answer(message, retrievals, summary)
        citations = [ChatCitation(source=item.metadata.get("source", item.document_id), title=item.title, score=item.score) for item in retrievals]
        entities = self._extract_entities(message, retrievals)
        classification = self._classify_query(message)
        sources = sorted({citation.source for citation in citations})
        chart_suggestion = "bar" if retrievals else None
        return ChatResponse(
            answer=answer,
            summary=summary,
            citations=citations,
            entities=entities,
            classification=classification,
            sources=sources,
            chart_suggestion=chart_suggestion,
            retrievals=retrievals,
        )

    def save_model(self, path: str | Path) -> None:
        self.vectorstore.save(path)

    @classmethod
    def load_model(cls, path: str | Path) -> InvestigationChatModel:
        return cls(vectorstore=InMemoryVectorStore.load(path))

    def _build_summary(self, retrievals: list[RetrievalChunk], message: str) -> str:
        if not retrievals:
            return build_summary_prompt(message, [])
        snippets = [item.content[:240] for item in retrievals[:3]]
        return build_summary_prompt(message, snippets)

    def _build_answer(self, message: str, retrievals: list[RetrievalChunk], summary: str) -> str:
        if not retrievals:
            return build_answer_prompt(message, summary, [])
        evidence_lines = [
            f"{item.title}: {item.content[:180]}"
            for item in retrievals[:3]
        ]
        return build_answer_prompt(message, summary, evidence_lines)

    def _extract_entities(self, message: str, retrievals: list[RetrievalChunk]) -> list[str]:
        tokens = []
        for part in [message, *[item.content for item in retrievals[:3]]]:
            for raw in part.replace("/", " ").replace(",", " ").split():
                token = raw.strip(" .,:;()[]{}\"'").lower()
                if len(token) > 3 and token[0].isalpha():
                    tokens.append(token)
        unique = []
        for token in tokens:
            if token not in unique:
                unique.append(token)
        return unique[:12]

    def _classify_query(self, message: str) -> str:
        lower = message.lower()
        if any(word in lower for word in {"fir", "summary", "summarize"}):
            return "FIR_SUMMARY"
        if any(word in lower for word in {"crime", "offense", "case", "classify"}):
            return "CRIME_CLASSIFICATION"
        if any(word in lower for word in {"entity", "who", "where", "location", "person"}):
            return "ENTITY_EXTRACTION"
        return "GENERAL_INVESTIGATION"
