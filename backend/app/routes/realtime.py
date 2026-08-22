"""Server-Sent Events endpoint streaming real-time case intelligence to the UI.

Events emitted:
  event: connected     — sent immediately after the stream opens
  event: heartbeat     — comment keep-alive every HEARTBEAT_SECONDS
  event: case_created  — payload mirrors GET /dashboard/recent-incidents items
"""
import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, require_roles
from app.models.user import User
from app.services.realtime.bus import realtime_bus

router = APIRouter(
    prefix="/realtime",
    tags=["Real-Time Stream"],
    dependencies=[Depends(require_roles(*ALL_ROLES))],
)

HEARTBEAT_SECONDS = 15


async def _event_stream(request: Request, username: str):
    subscriber_id, queue = realtime_bus.subscribe()
    try:
        connected = json.dumps({"status": "connected", "user": username})
        yield f"event: connected\ndata: {connected}\n\n"

        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
                continue
            data = json.dumps(event["data"], default=str)
            yield f"event: {event['type']}\ndata: {data}\n\n"
    finally:
        realtime_bus.unsubscribe(subscriber_id)


@router.get("/events")
async def stream_events(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Long-lived SSE stream of real-time platform events for the current user."""
    # Capture ORM attributes now — the DB session closes before streaming begins.
    username = current_user.username
    return StreamingResponse(
        _event_stream(request, username),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
