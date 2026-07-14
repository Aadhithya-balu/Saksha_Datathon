"""Conversational AI assistant endpoints for investigation queries."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.user import User
from app.services.analytics_service import category_breakdown, dashboard_summary, district_comparison

from app.ai.models.rag import InvestigationChatModel

router = APIRouter(prefix="/ai/chat", tags=["AI Chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    stream: bool = False


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


def _build_documents(db: Session) -> list[dict[str, Any]]:
    summary = dashboard_summary(db)
    districts = district_comparison(db)
    categories = category_breakdown(db)
    return [
        {
            "id": "dashboard-summary",
            "title": "Dashboard Summary",
            "source": "dashboard",
            "content": (
                f"Total crimes: {summary['total_crimes']}. Open cases: {summary['open_crimes']}. "
                f"FIRs: {summary['total_firs']}. Resolution rate: {summary['resolution_rate_percent']} percent."
            ),
        },
        {
            "id": "district-comparison",
            "title": "District Comparison",
            "source": "districts",
            "content": ", ".join(f"{row['district']} has {row['count']} cases" for row in districts[:8]) or "No district data available.",
        },
        {
            "id": "category-breakdown",
            "title": "Crime Categories",
            "source": "categories",
            "content": ", ".join(f"{row['category']} has {row['count']} cases" for row in categories[:8]) or "No category data available.",
        },
    ]


def _assistant_response(db: Session, message: str) -> ChatResponse:
    model = InvestigationChatModel()
    model.train(_build_documents(db))
    result = model.predict(message)
    return ChatResponse(
        answer=result.answer,
        summary=result.summary,
        entities=result.entities,
        classification=result.classification,
        sources=result.sources,
        chart_suggestion=result.chart_suggestion,
        citations=[ChatCitationOut(**citation.__dict__) for citation in result.citations],
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
    try:
        response = _assistant_response(db, payload.message)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if payload.stream:
        async def event_stream() -> AsyncIterator[bytes]:
            chunks = [
                {"type": "summary", "content": response.summary},
                {"type": "answer", "content": response.answer},
                {"type": "final", "content": response.model_dump()},
            ]
            for chunk in chunks:
                yield (json.dumps(chunk) + "\n").encode("utf-8")

        return StreamingResponse(event_stream(), media_type="application/x-ndjson")
    return response


@router.post("/query", response_model=ChatResponse)
def chat_query(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    return _assistant_response(db, payload.message)
