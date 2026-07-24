"""In-memory conversation memory for session-based chat continuity."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str           # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


class ChatMemory:
    """Thread-safe in-memory session store for conversation history."""

    def __init__(self, max_sessions: int = 100, max_messages: int = 20, ttl_seconds: int = 3600) -> None:
        self.max_sessions = max_sessions
        self.max_messages = max_messages
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, list[ChatMessage]] = {}
        self._last_access: dict[str, float] = {}

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        self._cleanup()
        if session_id not in self._sessions:
            return []
        self._last_access[session_id] = time.time()
        messages = self._sessions[session_id]
        return [{"role": m.role, "content": m.content} for m in messages[-self.max_messages:]]

    def add(self, session_id: str, user_message: str, ai_response: str) -> None:
        self._cleanup()
        if session_id not in self._sessions:
            if len(self._sessions) >= self.max_sessions:
                self._evict_oldest()
            self._sessions[session_id] = []

        now = time.time()
        self._sessions[session_id].append(ChatMessage(role="user", content=user_message, timestamp=now))
        self._sessions[session_id].append(ChatMessage(role="assistant", content=ai_response, timestamp=now))
        self._last_access[session_id] = now

        if len(self._sessions[session_id]) > self.max_messages * 2:
            self._sessions[session_id] = self._sessions[session_id][-self.max_messages * 2:]

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._last_access.pop(session_id, None)

    def _cleanup(self) -> None:
        now = time.time()
        expired = [
            sid for sid, last in self._last_access.items()
            if now - last > self.ttl_seconds
        ]
        for sid in expired:
            self._sessions.pop(sid, None)
            self._last_access.pop(sid, None)

    def _evict_oldest(self) -> None:
        if not self._last_access:
            return
        oldest = min(self._last_access, key=self._last_access.get)  # type: ignore[arg-type]
        self._sessions.pop(oldest, None)
        self._last_access.pop(oldest, None)


memory = ChatMemory()
