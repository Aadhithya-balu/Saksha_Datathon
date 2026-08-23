"""REST endpoints for persistent AI chat history.

All endpoints derive ownership from the authenticated user (JWT), never from
client-supplied ids. Users can only ever see and mutate their own conversations.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, require_roles
from app.core.exceptions import AppException
from app.database.postgres import get_db
from app.models.user import User
from app.schemas.chat_history import (
    ConversationCreate,
    ConversationDetailOut,
    ConversationListOut,
    ConversationOut,
    ConversationUpdate,
    MessageIn,
    MessageOut,
)
from app.services.chat import history_service

router = APIRouter(
    prefix="/ai/chat-history",
    tags=["AI Chat History"],
    dependencies=[Depends(require_roles(*ALL_ROLES))],
)


def _message_out(m) -> MessageOut:
    return MessageOut(
        id=m.id,
        role=m.role,
        content=m.content,
        classification=m.classification,
        sources=m.sources_json or [],
        citations=m.citations_json or [],
        created_at=m.created_at,
    )


@router.get("/conversations", response_model=ConversationListOut)
def list_conversations(
    q: str | None = Query(None, max_length=120, description="Search conversation titles"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_temporary: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = history_service.list_conversations(
        db, current_user.id, search=q, limit=limit, offset=offset,
        include_temporary=include_temporary,
    )
    return ConversationListOut(
        items=[ConversationOut.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/conversations", response_model=ConversationDetailOut, status_code=201)
def create_conversation(
    payload: ConversationCreate | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = history_service.create_conversation(db, current_user, payload)
    return ConversationDetailOut(
        **ConversationOut.model_validate(conv).model_dump(),
        messages=[],
        total_messages=conv.message_count or 0,
    )


@router.delete("/conversations")
def delete_all_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = history_service.delete_all_conversations(db, current_user)
    return {"deleted": deleted}


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: uuid.UUID,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv, messages, total = history_service.get_conversation_detail(
        db, current_user.id, conversation_id, limit=limit, offset=offset,
    )
    return ConversationDetailOut(
        **ConversationOut.model_validate(conv).model_dump(),
        messages=[_message_out(m) for m in messages],
        total_messages=total,
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = history_service.update_conversation(db, current_user, conversation_id, payload)
    return ConversationOut.model_validate(conv)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history_service.delete_conversation(db, current_user, conversation_id)


@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut, status_code=201)
def add_message(
    conversation_id: uuid.UUID,
    payload: MessageIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _, created = history_service.add_messages(
        db, current_user, conversation_id,
        [payload.model_dump(exclude_none=True)],
    )
    if not created:
        raise AppException("Failed to persist message", code="PERSIST_ERROR", status_code=500)
    return _message_out(created[0])
