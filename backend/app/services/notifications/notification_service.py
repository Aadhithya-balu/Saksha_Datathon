"""
Notification service — CRUD and business logic for platform notifications.

Handles creating, querying, reading, dismissing notifications, and
providing aggregate counts for the notification bell indicator.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationListOut,
    NotificationOut,
    NotificationCountOut,
)


def create_notification(
    db: Session,
    payload: NotificationCreate,
) -> Notification:
    """Create a new notification in the database."""
    notification = Notification(
        user_id=payload.user_id,
        notification_type=payload.notification_type,
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
    )
    db.add(notification)
    db.flush()
    return notification


def create_notifications_broadcast(
    db: Session,
    payload: NotificationCreate,
    exclude_user_id: uuid.UUID | None = None,
) -> list[Notification]:
    """Create notifications for all active users (broadcast)."""
    query = db.query(User).filter(User.is_active == True)
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)

    users = query.all()
    notifications = []
    for user in users:
        notification = Notification(
            user_id=user.id,
            notification_type=payload.notification_type,
            title=payload.title,
            message=payload.message,
            severity=payload.severity,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
        )
        db.add(notification)
        notifications.append(notification)

    db.flush()
    return notifications


def get_notifications(
    db: Session,
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    notification_type: str | None = None,
    severity: str | None = None,
    unread_only: bool = False,
) -> NotificationListOut:
    """Get paginated notifications for a user."""
    query = db.query(Notification).filter(
        or_(
            Notification.user_id == user_id,
            Notification.user_id.is_(None),  # broadcast notifications
        )
    )

    if notification_type:
        query = query.filter(Notification.notification_type == notification_type)
    if severity:
        query = query.filter(Notification.severity == severity)
    if unread_only:
        query = query.filter(Notification.is_read == False, Notification.is_dismissed == False)

    # Get unread count for batch
    unread_count = query.filter(
        Notification.is_read == False, Notification.is_dismissed == False
    ).count()

    total = query.count()
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    notifications = (
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return NotificationListOut(
        total=total,
        page=page,
        page_size=page_size,
        unread_count=unread_count,
        results=[NotificationOut.model_validate(n) for n in notifications],
    )


def get_unread_count(db: Session, user_id: uuid.UUID) -> NotificationCountOut:
    """Get notification counts for the bell indicator."""
    query = db.query(Notification).filter(
        or_(
            Notification.user_id == user_id,
            Notification.user_id.is_(None),
        ),
        Notification.is_read == False,
        Notification.is_dismissed == False,
    )

    total = query.count()
    critical = query.filter(Notification.severity == "critical").count()

    return NotificationCountOut(
        total=total,
        unread=total,
        critical=critical,
    )


def mark_notification_read(
    db: Session,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification | None:
    """Mark a single notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        or_(
            Notification.user_id == user_id,
            Notification.user_id.is_(None),
        ),
    ).first()

    if notification:
        notification.mark_read()
        db.flush()

    return notification


def mark_all_read(db: Session, user_id: uuid.UUID) -> int:
    """Mark all unread notifications as read for a user."""
    now = datetime.now(timezone.utc)
    result = (
        db.query(Notification)
        .filter(
            or_(
                Notification.user_id == user_id,
                Notification.user_id.is_(None),
            ),
            Notification.is_read == False,
            Notification.is_dismissed == False,
        )
        .update({"is_read": True, "read_at": now})
    )
    db.flush()
    return result


def dismiss_notification(
    db: Session,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification | None:
    """Dismiss a notification (soft-delete from view)."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        or_(
            Notification.user_id == user_id,
            Notification.user_id.is_(None),
        ),
    ).first()

    if notification:
        notification.mark_dismissed()
        db.flush()

    return notification


def get_recent_notifications(
    db: Session, user_id: uuid.UUID, limit: int = 5
) -> list[NotificationOut]:
    """Get the most recent notifications for quick display (bell dropdown)."""
    notifications = (
        db.query(Notification)
        .filter(
            or_(
                Notification.user_id == user_id,
                Notification.user_id.is_(None),
            ),
            Notification.is_dismissed == False,
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    return [NotificationOut.model_validate(n) for n in notifications]


def create_system_health_notification(
    db: Session,
    service_name: str,
    status: str,
    details: str | None = None,
) -> Notification | None:
    """Create a system health notification if a service is degraded/down."""
    if status not in ("degraded", "down"):
        return None

    severity = "critical" if status == "down" else "high"
    title = f"System Alert: {service_name} is {status}"
    message = details or f"The {service_name} service is currently {status}. Investigate immediately."

    payload = NotificationCreate(
        user_id=None,  # broadcast
        notification_type="system_health",
        title=title,
        message=message,
        severity=severity,
        resource_type="system",
        resource_id=service_name,
    )
    return create_notification(db, payload)

