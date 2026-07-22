"""Conversational AI assistant endpoints for investigation queries."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.user import User
from app.services.chat.chat_service import InvestigationChatService

router = APIRouter(prefix="/ai/chat", tags=["AI Chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    stream: bool = False
    fir_id: str | None = None
    criminal_id: str | None = None
    evidence_id: str | None = None
    case_id: str | None = None


class ChatCitationOut(BaseModel):
    source: str
    title: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    summary: str
    entities: list[str]
    classification: str
    sources: list[str]
    chart_suggestion: str | None = None
    citations: list[ChatCitationOut] = Field(default_factory=list)
    data: list[dict[str, Any]] = Field(default_factory=list)


def _assistant_response(
    db: Session,
    message: str,
    *,
    fir_id: str | None = None,
    criminal_id: str | None = None,
    evidence_id: str | None = None,
    case_id: str | None = None,
) -> ChatResponse:
    """Internal assistant response builder for backwards compatibility."""
    service = InvestigationChatService(db)
    result = service.process_query(
        message,
        fir_id=fir_id,
        criminal_id=criminal_id,
        evidence_id=evidence_id,
        case_id=case_id,
    )
    return ChatResponse(
        answer=result.answer,
        summary=result.summary,
        entities=result.entities,
        classification=result.classification,
        sources=result.sources,
        chart_suggestion=result.chart_suggestion,
        citations=[
            ChatCitationOut(source=c.source, title=c.title, score=c.score)
            for c in result.citations
        ],
        data=[
            {
                "query": message,
                "retrievals": [
                    {"document_id": item.document_id, "title": item.title, "score": item.score}
                    for item in result.retrievals
                ],
            }
        ],
    )


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    service = InvestigationChatService(db)
    try:
        if payload.stream:
            stream_gen = service.stream_response(
                payload.message,
                fir_id=payload.fir_id,
                criminal_id=payload.criminal_id,
                evidence_id=payload.evidence_id,
                case_id=payload.case_id,
            )
            return StreamingResponse(stream_gen, media_type="application/x-ndjson")

        return _assistant_response(
            db,
            payload.message,
            fir_id=payload.fir_id,
            criminal_id=payload.criminal_id,
            evidence_id=payload.evidence_id,
            case_id=payload.case_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/query", response_model=ChatResponse)
def chat_query(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    try:
        return _assistant_response(
            db,
            payload.message,
            fir_id=payload.fir_id,
            criminal_id=payload.criminal_id,
            evidence_id=payload.evidence_id,
            case_id=payload.case_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
