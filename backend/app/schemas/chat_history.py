"""Pydantic schemas for persistent AI chat history (conversations + messages)."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=50000)
    classification: str | None = None
    sources: list[Any] | None = None
    citations: list[Any] | None = None


class ConversationCreate(BaseModel):
    title: str | None = Field(None, max_length=200)
    temporary: bool = Field(False, description="Mark as temporary (excluded from saved history)")
    messages: list[ConversationMessageIn] = Field(
        default_factory=list,
        description="Optional seed messages (used when saving a temporary chat).",
    )


class ConversationUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    is_temporary: bool | None = Field(
        None,
        description="Toggle saved/temporary state. Temporary conversations are hidden from history.",
    )


class MessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=50000)
    classification: str | None = None
    sources: list[Any] | None = None
    citations: list[Any] | None = None

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be blank")
        return v


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    classification: str | None = None
    sources: list[Any] | None = None
    citations: list[Any] | None = None
    created_at: datetime


class ConversationOut(BaseModel):
    """Conversation metadata only — no message bodies (list view stays lightweight)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    is_temporary: bool
    message_count: int
    last_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = Field(default_factory=list)
    total_messages: int = 0


class ConversationListOut(BaseModel):
    items: list[ConversationOut]
    total: int
    limit: int
    offset: int
