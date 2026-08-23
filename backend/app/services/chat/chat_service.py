"""Investigation Chat Service handling model prediction and streaming NDJSON generator."""
from __future__ import annotations

import json
from typing import AsyncIterator
from sqlalchemy.orm import Session

from app.ai.models.rag.chat_model import InvestigationChatModel, ChatResponse
from app.services.rag.rag_service import build_rag_documents


class InvestigationChatService:
    """Service encapsulating RAG context building, prediction, and streaming."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def process_query(
        self,
        message: str,
        *,
        fir_id: str | None = None,
        criminal_id: str | None = None,
        evidence_id: str | None = None,
        case_id: str | None = None,
    ) -> ChatResponse:
        """Fetch RAG documents and perform model prediction."""
        docs = build_rag_documents(
            self.db,
            fir_id=fir_id,
            criminal_id=criminal_id,
            evidence_id=evidence_id,
            case_id=case_id,
        )
        model = InvestigationChatModel()
        model.train(docs)
        return model.predict(message)

    async def stream_response(
        self,
        message: str,
        *,
        fir_id: str | None = None,
        criminal_id: str | None = None,
        evidence_id: str | None = None,
        case_id: str | None = None,
    ) -> AsyncIterator[bytes]:
        """Stream chunks as newline-delimited JSON (NDJSON) events."""
        result = self.process_query(
            message,
            fir_id=fir_id,
            criminal_id=criminal_id,
            evidence_id=evidence_id,
            case_id=case_id,
        )

        # 1. Summary chunk
        summary_payload = {"type": "summary", "content": result.summary}
        yield (json.dumps(summary_payload) + "\n").encode("utf-8")

        # 2. Tokenized text streaming chunks for real-time typing effect
        words = result.answer.split(" ")
        chunk_size = max(1, len(words) // 8)
        for i in range(0, len(words), chunk_size):
            token_text = " ".join(words[i : i + chunk_size]) + (" " if i + chunk_size < len(words) else "")
            chunk_payload = {"type": "token", "content": token_text}
            yield (json.dumps(chunk_payload) + "\n").encode("utf-8")

        # 3. Citations chunk
        citations_data = [
            {"source": c.source, "title": c.title, "score": c.score}
            for c in result.citations
        ]
        citations_payload = {"type": "citations", "content": citations_data}
        yield (json.dumps(citations_payload) + "\n").encode("utf-8")

        # 4. Final payload chunk
        final_payload = {
            "type": "final",
            "content": {
                "answer": result.answer,
                "summary": result.summary,
                "entities": result.entities,
                "classification": result.classification,
                "sources": result.sources,
                "chart_suggestion": result.chart_suggestion,
                "citations": citations_data,
            },
        }
        yield (json.dumps(final_payload) + "\n").encode("utf-8")
