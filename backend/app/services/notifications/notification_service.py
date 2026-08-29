"""
Notification service — inter-station communication center logic.

Handles creating, querying, reading, acknowledging, replying to, and
dismissing notifications between officers and stations.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationListOut,
    NotificationOut,
    NotificationCountOut,
    NotificationDashboardSummary,
)


def _enrich_notification(notif: Notification, db: Session) -> dict[str, Any]:
    """Build a dict with sender/recipient names resolved."""
    data = notif.to_dict()
    if notif.sender_id:
        sender = db.query(User).filter(User.id == notif.sender_id).first()
        if sender:
            data["sender_name"] = sender.full_name
            data["sender_badge"] = sender.username
    if notif.user_id:
        recipient = db.query(User).filter(User.id == notif.user_id).first()
        if recipient:
            data["recipient_name"] = recipient.full_name
    return data


def _resolve_aware_created(value: datetime | None) -> datetime | None:
    """TZ-normalise a row's created_at for safe comparisons (SQLite is naive)."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _dedupe_notifications(rows: list[Notification]) -> list[Notification]:
    """Collapse duplicate rows of the same broadcast.

    A broadcast fans out one row per active user, but every copy is marked
    ``is_broadcast=True`` so the list/unread/recent queries previously showed
    each user N copies of the same alert (one per recipient). Broadcast copies
    share the same notification_type + subject + title and were created in a
    single transaction (identical ``created_at``), so that triple acts as a
    reliable group key. Recipient-scoped rows (user_id == current user) are
    never collapsed.
    """
    seen_broadcasts: set[tuple] = set()
    deduped: list[Notification] = []
    for row in rows:
        if row.is_broadcast:
            key = (row.notification_type, row.subject, row.title, row.created_at)
            if key in seen_broadcasts:
                continue
            seen_broadcasts.add(key)
        deduped.append(row)
    return deduped


def _resolve_recipient_id(recipient_id, db: Session):
    """Resolve a recipient_id that may be a UUID or a username string to a UUID."""
    if recipient_id is None:
        return None
    if isinstance(recipient_id, uuid.UUID):
        return recipient_id
    user = db.query(User).filter(User.username == str(recipient_id)).first()
    return user.id if user else None


def create_notification(
    db: Session,
    payload: NotificationCreate,
) -> Notification:
    """Create a new notification in the database."""
    resolved_recipient = _resolve_recipient_id(payload.recipient_id, db)
    notification = Notification(
        user_id=resolved_recipient,
        sender_id=payload.sender_id,
        subject=payload.subject,
        notification_type=payload.notification_type,
        category=payload.category,
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        priority=payload.priority,
        status="unread",
        resource_type=None,
        resource_id=None,
        related_case_number=payload.related_case_number,
        related_fir_number=payload.related_fir_number,
        is_broadcast=payload.is_broadcast,
        parent_id=payload.parent_id,
        attachment_url=payload.attachment_url,
    )
    db.add(notification)
    db.flush()
    return notification


def _recent_broadcast_duplicate(
    db: Session,
    payload: NotificationCreate,
    now: datetime,
) -> Notification | None:
    """Find an identical broadcast created within the dedup window.

    Keyed on notification_type + category + subject + title. When present, the
    caller returns the existing row instead of creating a fresh copy for every
    user, so reload/tab/retry loops cannot flood the notification center.
    """
    window_hours = settings.NOTIFICATION_BROADCAST_DEDUP_HOURS
    if window_hours <= 0:
        return None
    threshold = now - timedelta(hours=window_hours)
    return (
        db.query(Notification)
        .filter(
            Notification.is_broadcast == True,
            Notification.notification_type == payload.notification_type,
            Notification.category == payload.category,
            Notification.subject == payload.subject,
            Notification.title == payload.title,
            Notification.created_at >= threshold,
        )
        .order_by(Notification.created_at.desc())
        .first()
    )


def create_broadcast_notification(
    db: Session,
    payload: NotificationCreate,
    exclude_user_id: uuid.UUID | None = None,
) -> list[Notification]:
    """Create notifications for all active users (broadcast).

    Deduplicated: an identical broadcast created within the configured window
    returns the existing notification instead of fanning out another copy to
    every user.
    """
    now = datetime.now(timezone.utc)
    duplicate = _recent_broadcast_duplicate(db, payload, now)
    if duplicate is not None:
        return [duplicate]

    query = db.query(User).filter(User.is_active == True)
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)

    users = query.all()
    notifications = []
    for user in users:
        notification = Notification(
            user_id=user.id,
            sender_id=payload.sender_id,
            subject=payload.subject,
            notification_type=payload.notification_type,
            category=payload.category,
            title=payload.title,
            message=payload.message,
            severity=payload.severity,
            priority=payload.priority,
            status="unread",
            related_case_number=payload.related_case_number,
            related_fir_number=payload.related_fir_number,
            is_broadcast=True,
            parent_id=payload.parent_id,
            attachment_url=payload.attachment_url,
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
    priority: str | None = None,
    category: str | None = None,
    status: str | None = None,
    sender_id: str | None = None,
    search: str | None = None,
    unread_only: bool = False,
) -> NotificationListOut:
    """Get paginated notifications for a user with advanced filtering.

    Broadcast notifications are returned once per broadcast, even though they
    fan out one row per recipient (no duplicate copies of the same alert).
    """
    rows = (
        db.query(Notification)
        .filter(
            or_(
                Notification.user_id == user_id,
                Notification.is_broadcast == True,
            )
        )
        .all()
    )
    rows = _dedupe_notifications(rows)

    unread_count = sum(1 for r in rows if not r.is_read and not r.is_dismissed)

    if notification_type:
        rows = [r for r in rows if r.notification_type == notification_type]
    if severity:
        rows = [r for r in rows if r.severity == severity]
    if priority:
        rows = [r for r in rows if r.priority == priority]
    if category:
        rows = [r for r in rows if r.category == category]
    if status:
        if status == "unread":
            rows = [r for r in rows if not r.is_read and not r.is_dismissed]
        elif status == "read":
            rows = [r for r in rows if r.is_read and not r.is_dismissed]
        elif status == "acknowledged":
            rows = [r for r in rows if r.status == "acknowledged"]
        elif status == "resolved":
            rows = [r for r in rows if r.status == "resolved"]
        elif status == "dismissed":
            rows = [r for r in rows if r.is_dismissed]
    if sender_id:
        try:
            sid = uuid.UUID(sender_id)
            rows = [r for r in rows if r.sender_id == sid]
        except ValueError:
            pass
    if search:
        term = search.lower()
        rows = [
            r
            for r in rows
            if term in (r.subject or "").lower()
            or term in (r.message or "").lower()
            or term in (r.title or "").lower()
            or term in (r.related_case_number or "").lower()
            or term in (r.related_fir_number or "").lower()
        ]
    if unread_only:
        rows = [r for r in rows if not r.is_read and not r.is_dismissed]

    rows.sort(key=lambda r: r.created_at or datetime.min, reverse=True)

    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = len(rows)
    start = (page - 1) * page_size
    notifications = rows[start:start + page_size]

    enriched = [_enrich_notification(n, db) for n in notifications]

    return NotificationListOut(
        total=total,
        page=page,
        page_size=page_size,
        unread_count=unread_count,
        results=[NotificationOut.model_validate(d) for d in enriched],
    )


def get_unread_count(db: Session, user_id: uuid.UUID) -> NotificationCountOut:
    """Get notification counts for the bell indicator (broadcast deduped)."""
    rows = (
        db.query(Notification)
        .filter(
            or_(
                Notification.user_id == user_id,
                Notification.is_broadcast == True,
            )
        )
        .all()
    )
    rows = _dedupe_notifications(rows)

    unread = [r for r in rows if not r.is_read and not r.is_dismissed]
    critical = [r for r in unread if r.severity == "critical" or r.priority == "critical"]

    return NotificationCountOut(
        total=len(unread),
        unread=len(unread),
        critical=len(critical),
    )


def get_dashboard_summary(db: Session, user_id: uuid.UUID) -> NotificationDashboardSummary:
    """Get dashboard summary cards for the communication center."""
    rows = (
        db.query(Notification)
        .filter(
            or_(
                Notification.user_id == user_id,
                Notification.is_broadcast == True,
            )
        )
        .all()
    )
    rows = _dedupe_notifications(rows)

    unread = [r for r in rows if not r.is_read and not r.is_dismissed]
    unread_count = len(unread)

    critical_alerts = len(
        [r for r in unread if r.severity == "critical" or r.priority == "critical"]
    )

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_messages = len(
        [r for r in rows if _resolve_aware_created(r.created_at) and _resolve_aware_created(r.created_at) >= today_start]
    )

    ack_categories = ["evidence_request", "investigation_update", "case_escalation", "officer_assistance"]
    pending_ack = len(
        [
            r
            for r in rows
            if r.status == "unread"
            and r.category in ack_categories
            and not r.is_read
        ]
    )

    investigation_requests = len(
        [r for r in rows if r.category in ack_categories and not r.is_dismissed]
    )

    broadcast_messages = len([r for r in rows if r.is_broadcast])

    return NotificationDashboardSummary(
        unread_count=unread_count,
        critical_alerts=critical_alerts,
        today_messages=today_messages,
        pending_acknowledgements=pending_ack,
        investigation_requests=investigation_requests,
        broadcast_messages=broadcast_messages,
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
            Notification.is_broadcast == True,
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
                Notification.is_broadcast == True,
            ),
            Notification.is_read == False,
            Notification.is_dismissed == False,
        )
        .update({"is_read": True, "read_at": now, "status": "read"})
    )
    db.flush()
    return result


def acknowledge_notification(
    db: Session,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification | None:
    """Acknowledge a notification."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        or_(
            Notification.user_id == user_id,
            Notification.is_broadcast == True,
        ),
    ).first()

    if notification:
        notification.mark_read()
        notification.mark_acknowledged()
        db.flush()

    return notification


def resolve_notification(
    db: Session,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification | None:
    """Resolve a notification."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        or_(
            Notification.user_id == user_id,
            Notification.is_broadcast == True,
        ),
    ).first()

    if notification:
        notification.mark_read()
        notification.mark_resolved()
        db.flush()

    return notification


def dismiss_notification(
    db: Session,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification | None:
    """Dismiss (soft-delete) a notification."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        or_(
            Notification.user_id == user_id,
            Notification.is_broadcast == True,
        ),
    ).first()

    if notification:
        notification.mark_dismissed()
        db.flush()

    return notification


def get_recent_notifications(
    db: Session, user_id: uuid.UUID, limit: int = 5
) -> list[dict[str, Any]]:
    """Get the most recent notifications for quick display (bell dropdown).

    Broadcast copies are collapsed so repeated fan-out of one alert shows once.
    """
    rows = (
        db.query(Notification)
        .filter(
            or_(
                Notification.user_id == user_id,
                Notification.is_broadcast == True,
            ),
            Notification.is_dismissed == False,
        )
        .all()
    )
    rows = _dedupe_notifications(rows)
    rows.sort(key=lambda r: r.created_at or datetime.min, reverse=True)
    return [_enrich_notification(n, db) for n in rows[:limit]]


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
        recipient_id=None,
        sender_id=None,
        subject=title,
        notification_type="system_health",
        category="system_notification",
        title=title,
        message=message,
        severity=severity,
        priority=severity,
        is_broadcast=True,
    )
    return create_notification(db, payload)
