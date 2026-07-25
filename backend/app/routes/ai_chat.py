"""Conversational AI assistant endpoints — backend-grounded via the Chat Orchestrator."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.chat.orchestrator import ChatOrchestrator
from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, require_roles
from app.database.postgres import get_db
from app.models.user import User

router = APIRouter(prefix="/ai/chat", tags=["AI Chat"], dependencies=[Depends(require_roles(*ALL_ROLES))])

_orchestrator = ChatOrchestrator()


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


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    if payload.stream:
        async def event_stream() -> AsyncIterator[bytes]:
            async for chunk in _orchestrator.process_message(
                payload.message, payload.session_id, db,
            ):
                yield chunk
        return StreamingResponse(event_stream(), media_type="application/x-ndjson")

    result = _orchestrator.process_message_sync(payload.message, payload.session_id, db)
    return _build_response(result)


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    try:
        result = _orchestrator.process_message_sync(payload.message, payload.session_id, db)
        return _build_response(result)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/investigation-chat", response_model=ChatResponse)
async def investigation_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    try:
        result = _orchestrator.process_message_sync(payload.message, payload.session_id, db)
        return _build_response(result)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def _build_response(result: dict[str, Any]) -> ChatResponse:
    return ChatResponse(
        answer=result.get("answer", ""),
        summary=result.get("summary", ""),
        entities=result.get("entities", []),
        classification=result.get("classification", "general"),
        sources=result.get("sources", []),
        chart_suggestion=result.get("chart_suggestion"),
        citations=[
            ChatCitationOut(**c) for c in result.get("citations", [])
            if isinstance(c, dict)
        ],
        data=[{
            "classification": result.get("classification", "general"),
            "entities": result.get("entities", []),
        }],
    )
