"""
Persistent AI chat history service.

Every operation is scoped to the authenticated user's id: ownership is enforced
at the query level (never by frontend filtering), and conversations belonging
to other users are indistinguishable from non-existent ones (404 either way).

Message bodies of an exchange (user prompt + assistant answer) are written
atomically after successful AI generation only — failed generations never
leave partial records behind.
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NotFoundException
from app.models.chat import ChatConversation, ChatMessage
from app.models.user import User
from app.schemas.chat_history import ConversationCreate, ConversationUpdate

logger = logging.getLogger("saksha")

DEFAULT_TITLE = "New Chat"
MAX_TITLE_LENGTH = 200
MAX_CONTEXT_MESSAGES = 12  # messages sent to the LLM as conversational context


def derive_title(text: str) -> str:
    """Short, meaningful title derived from the first user message."""
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return DEFAULT_TITLE
    if len(cleaned) <= 48:
        return cleaned
    cut = cleaned[:48]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return f"{cut.strip()}..."


def _as_uuid(value: Any) -> uuid.UUID:
    """Accept UUID or canonical string forms of a user/conversation id."""
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def get_owned_conversation(db: Session, user_id: Any, conversation_id: Any) -> ChatConversation:
    """Return the conversation only if it exists AND belongs to the user."""
    conv = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == _as_uuid(conversation_id),
            ChatConversation.user_id == _as_uuid(user_id),
        )
        .first()
    )
    if conv is None:
        # Same response for missing and foreign conversations — no existence leak.
        raise NotFoundException("Conversation not found")
    return conv


def list_conversations(
    db: Session,
    user_id: Any,
    *,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    include_temporary: bool = False,
) -> tuple[list[ChatConversation], int]:
    """List the user's conversation metadata (titles only), newest activity first."""
    user_id = _as_uuid(user_id)
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))

    query = db.query(ChatConversation).filter(ChatConversation.user_id == user_id)
    if not include_temporary:
        query = query.filter(ChatConversation.is_temporary.is_(False))
    if search:
        query = query.filter(ChatConversation.title.ilike(f"%{search.strip()[:120]}%"))

    total = query.count()
    items = (
        query.order_by(ChatConversation.updated_at.desc(), ChatConversation.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def get_conversation_detail(
    db: Session,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    *,
    limit: int = 200,
    offset: int = 0,
) -> tuple[ChatConversation, list[ChatMessage], int]:
    """Conversation + one lazy page of its messages (oldest first)."""
    conv = get_owned_conversation(db, user_id, conversation_id)
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    total = conv.message_count or (
        db.query(sa_func.count(ChatMessage.id))
        .filter(ChatMessage.conversation_id == conv.id)
        .scalar()
        or 0
    )
    messages: list[ChatMessage] = []
    if total > 0:
        # Page from the END so the newest context is returned even for huge threads.
        page_query = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conv.id)
            .order_by(ChatMessage.seq.desc())
        )
        if offset == 0:
            rows = page_query.limit(limit).all()
        else:
            rows = page_query.offset(offset).limit(limit).all()
        messages = list(reversed(rows))
    return conv, messages, int(total)


def create_conversation(
    db: Session,
    user: User,
    payload: ConversationCreate | None = None,
) -> ChatConversation:
    """Create a conversation owned by the authenticated user, optionally seeding messages."""
    payload = payload or ConversationCreate()
    title = (payload.title or DEFAULT_TITLE).strip()[:MAX_TITLE_LENGTH] or DEFAULT_TITLE
    conv = ChatConversation(
        user_id=_as_uuid(user.id),
        title=title,
        is_temporary=bool(payload.temporary),
        message_count=0,
    )
    db.add(conv)
    db.flush()

    if payload.messages:
        _append_messages(db, conv, [m.model_dump(exclude_none=True) for m in payload.messages])
    db.commit()
    db.refresh(conv)
    return conv


def add_messages(
    db: Session,
    user: User,
    conversation_id: uuid.UUID,
    messages: list[dict[str, Any]],
) -> tuple[ChatConversation, list[ChatMessage]]:
    """Append a validated batch of messages to the user's own conversation (atomic)."""
    conv = get_owned_conversation(db, user.id, conversation_id)
    created = _append_messages(db, conv, messages)
    db.commit()
    db.refresh(conv)
    return conv, created


def rename_conversation(db: Session, user: User, conversation_id: uuid.UUID, title: str) -> ChatConversation:
    conv = get_owned_conversation(db, user.id, conversation_id)
    clean = re.sub(r"\s+", " ", (title or "").strip())[:MAX_TITLE_LENGTH]
    if not clean:
        raise AppException("Title must not be empty", code="VALIDATION_ERROR", status_code=422)
    conv.title = clean
    db.commit()
    db.refresh(conv)
    return conv


def update_conversation(
    db: Session,
    user: User,
    conversation_id: uuid.UUID,
    payload: ConversationUpdate,
) -> ChatConversation:
    """Rename and/or toggle saved/temporary state of the user's own conversation."""
    conv = get_owned_conversation(db, user.id, conversation_id)
    changed = False
    if payload.title is not None:
        clean = re.sub(r"\s+", " ", payload.title.strip())[:MAX_TITLE_LENGTH]
        if not clean:
            raise AppException("Title must not be empty", code="VALIDATION_ERROR", status_code=422)
        conv.title = clean
        changed = True
    if payload.is_temporary is not None:
        conv.is_temporary = bool(payload.is_temporary)
        changed = True
    if changed:
        db.commit()
        db.refresh(conv)
    return conv


def delete_conversation(db: Session, user: User, conversation_id: uuid.UUID) -> None:
    conv = get_owned_conversation(db, user.id, conversation_id)
    db.delete(conv)
    db.commit()


def delete_all_conversations(db: Session, user: User, *, include_temporary: bool = True) -> int:
    """Delete every conversation owned by the user. Returns the number removed."""
    query = db.query(ChatConversation).filter(ChatConversation.user_id == _as_uuid(user.id))
    if not include_temporary:
        query = query.filter(ChatConversation.is_temporary.is_(False))
    count = query.count()
    if count:
        for conv in query.all():
            db.delete(conv)
        db.commit()
    return count


def load_llm_context(db: Session, conversation_id: uuid.UUID, max_messages: int = MAX_CONTEXT_MESSAGES) -> list[dict[str, str]]:
    """Last N messages as [{role, content}] for LLM context. Never logs content."""
    rows = (
        db.query(ChatMessage.role, ChatMessage.content)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.seq.desc())
        .limit(max(1, min(max_messages, 50)))
        .all()
    )
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


def discard_if_empty(db: Session, user: User, conversation: ChatConversation) -> bool:
    """Remove a conversation that still holds zero messages (auto-created but never used)."""
    db.refresh(conversation)
    if (conversation.message_count or 0) > 0:
        return False
    try:
        db.delete(conversation)
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Failed to discard empty conversation %s", conversation.id, exc_info=True)
        return False
    return True


def _append_messages(db: Session, conv: ChatConversation, messages: list[dict[str, Any]]) -> list[ChatMessage]:
    """Validate + append messages. Returns the created ORM rows (not yet committed)."""
    created: list[ChatMessage] = []
    first_user_content = None
    base = (
        db.query(sa_func.max(ChatMessage.seq))
        .filter(ChatMessage.conversation_id == conv.id)
        .scalar()
        or 0
    )
    for offset, item in enumerate(messages):
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role not in ("user", "assistant"):
            raise AppException(
                f"Invalid message role: {role!r}", code="VALIDATION_ERROR", status_code=422
            )
        if not content:
            continue
        if first_user_content is None and role == "user":
            first_user_content = content
        msg = ChatMessage(
            conversation_id=conv.id,
            role=role,
            content=content[:50000],
            classification=item.get("classification"),
            sources_json=item.get("sources"),
            citations_json=item.get("citations"),
            seq=base + len(created) + 1,
        )
        db.add(msg)
        created.append(msg)

    if not created:
        return []

    conv.message_count = (conv.message_count or 0) + len(created)
    conv.last_message_at = sa_func.now()

    # Auto-title once, from the very first user message.
    if first_user_content and conv.title in (None, "", DEFAULT_TITLE):
        conv.title = derive_title(first_user_content)[:MAX_TITLE_LENGTH]

    db.flush()
    return created
