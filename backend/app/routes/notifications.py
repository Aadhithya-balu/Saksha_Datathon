"""
Notification routes — real-time intelligence & notification center endpoints.

Provides:
- GET /notifications — list notifications (paginated, filterable)
- GET /notifications/count — unread notification counts
- GET /notifications/recent — recent notifications for bell dropdown
- PUT /notifications/{id}/read — mark single notification as read
- PUT /notifications/read-all — mark all notifications as read
- DELETE /notifications/{id} — dismiss a notification
- GET /notifications/activity-feed — unified activity feed
- GET /notifications/live-timeline — live event timeline
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.user import User
from app.schemas.notification import (
    ActivityFeedOut,
    NotificationCountOut,
    NotificationListOut,
    NotificationMarkReadOut,
    NotificationOut,
)
from app.services.notifications import (
    activity_service,
    notification_service,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListOut)
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    notification_type: str | None = Query(None),
    severity: str | None = Query(None),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated notifications for the current user."""
    return notification_service.get_notifications(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        notification_type=notification_type,
        severity=severity,
        unread_only=unread_only,
    )


@router.get("/count", response_model=NotificationCountOut)
def get_notification_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get unread notification counts for the bell indicator."""
    return notification_service.get_unread_count(db, current_user.id)


@router.get("/recent", response_model=list[NotificationOut])
def get_recent_notifications(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent notifications for the bell dropdown."""
    return notification_service.get_recent_notifications(db, current_user.id, limit)


@router.put("/{notification_id}/read", response_model=NotificationMarkReadOut)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a single notification as read."""
    result = notification_service.mark_notification_read(
        db, notification_id, current_user.id
    )
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationMarkReadOut(success=True, message="Notification marked as read")


@router.put("/read-all", response_model=NotificationMarkReadOut)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all unread notifications as read."""
    count = notification_service.mark_all_read(db, current_user.id)
    return NotificationMarkReadOut(
        success=True,
        message=f"{count} notification(s) marked as read",
    )


@router.delete("/{notification_id}", response_model=NotificationMarkReadOut)
def dismiss_notification(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss (soft-delete) a notification."""
    result = notification_service.dismiss_notification(
        db, notification_id, current_user.id
    )
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationMarkReadOut(success=True, message="Notification dismissed")


@router.get("/activity-feed", response_model=ActivityFeedOut)
def get_activity_feed(
    limit: int = Query(50, ge=1, le=200),
    event_type: str | None = Query(None),
    resource_type: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get unified activity feed from audit logs, notifications, and evidence timeline."""
    return activity_service.get_activity_feed(
        db,
        user_id=current_user.id,
        limit=limit,
        event_type=event_type,
        resource_type=resource_type,
    )


@router.get("/live-timeline")
def get_live_timeline(
    case_id: uuid.UUID | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get live event timeline, optionally filtered by case_id."""
    return activity_service.get_live_event_timeline(
        db,
        case_id=case_id,
        limit=limit,
    )

