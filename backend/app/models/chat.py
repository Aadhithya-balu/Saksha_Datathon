"""Persistent AI chat history models — user-owned conversations and messages."""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ChatConversation(Base, UUIDPKMixin, TimestampMixin):
    """A user-owned AI conversation (chat thread)."""

    __tablename__ = "chat_conversations"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="New Chat")
    is_temporary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.seq",
    )

    __table_args__ = (
        Index("ix_chat_conversations_user_id", "user_id"),
        Index("ix_chat_conversations_user_updated", "user_id", "updated_at"),
    )


class ChatMessage(Base, UUIDPKMixin):
    """A single message inside a conversation."""

    __tablename__ = "chat_messages"

    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sources_json: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    citations_json: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[ChatConversation] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_conversation_id", "conversation_id"),
        Index("ux_chat_messages_conv_seq", "conversation_id", "seq", unique=True),
    )
