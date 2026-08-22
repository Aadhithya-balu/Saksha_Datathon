"""In-process pub/sub event bus powering real-time Server-Sent Events (SSE).

Sync route handlers run in FastAPI's threadpool, so ``publish`` is thread-safe
and fans out onto the asyncio event loop where SSE subscribers are waiting.
"""
import asyncio
import threading

from app.core.logging_config import logger


class RealtimeBus:
    """Fan-out bus: producers publish typed events, each SSE client owns a queue."""

    def __init__(self) -> None:
        self._subscribers: dict[int, asyncio.Queue] = {}
        self._lock = threading.Lock()
        self._next_id = 0
        self._loop: asyncio.AbstractEventLoop | None = None

    def subscribe(self) -> tuple[int, asyncio.Queue]:
        """Register a new subscriber. Must be called from the event loop."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        loop = asyncio.get_running_loop()
        with self._lock:
            if self._loop is None or self._loop.is_closed():
                self._loop = loop
            self._next_id += 1
            subscriber_id = self._next_id
            self._subscribers[subscriber_id] = queue
        return subscriber_id, queue

    def unsubscribe(self, subscriber_id: int) -> None:
        with self._lock:
            self._subscribers.pop(subscriber_id, None)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    def publish(self, event_type: str, payload: dict) -> None:
        """Thread-safe publish. Safe to call from sync route handlers.

        Best-effort delivery: slow consumers whose queue is full drop events
        rather than blocking producers; a missed event is healed by the next
        dashboard refetch.
        """
        event = {"type": event_type, "data": payload}
        with self._lock:
            loop = self._loop
            queues = list(self._subscribers.values())
        if not queues or loop is None or loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(self._fanout, event, queues)
        except RuntimeError:
            # Loop shut down between check and schedule — nothing to deliver to.
            pass

    def _fanout(self, event: dict, queues: list[asyncio.Queue]) -> None:
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Realtime subscriber queue full — dropping event")


realtime_bus = RealtimeBus()
