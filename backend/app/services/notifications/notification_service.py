"""
Notification service — inter-station communication center logic.

Handles creating, querying, reading, acknowledging, replying to, and
dismissing notifications between officers and stations.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session, joinedload

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


def create_broadcast_notification(
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
    """Get paginated notifications for a user with advanced filtering."""
    query = db.query(Notification).filter(
        or_(
            Notification.user_id == user_id,
            Notification.is_broadcast == True,
        )
    )

    if notification_type:
        query = query.filter(Notification.notification_type == notification_type)
    if severity:
        query = query.filter(Notification.severity == severity)
    if priority:
        query = query.filter(Notification.priority == priority)
    if category:
        query = query.filter(Notification.category == category)
    if status:
        if status == "unread":
            query = query.filter(Notification.is_read == False, Notification.is_dismissed == False)
        elif status == "read":
            query = query.filter(Notification.is_read == True, Notification.is_dismissed == False)
        elif status == "acknowledged":
            query = query.filter(Notification.status == "acknowledged")
        elif status == "resolved":
            query = query.filter(Notification.status == "resolved")
        elif status == "dismissed":
            query = query.filter(Notification.is_dismissed == True)
    if sender_id:
        try:
            sid = uuid.UUID(sender_id)
            query = query.filter(Notification.sender_id == sid)
        except ValueError:
            pass
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Notification.subject.ilike(search_term),
                Notification.message.ilike(search_term),
                Notification.title.ilike(search_term),
                Notification.related_case_number.ilike(search_term),
                Notification.related_fir_number.ilike(search_term),
            )
        )
    if unread_only:
        query = query.filter(Notification.is_read == False, Notification.is_dismissed == False)

    unread_count = db.query(Notification).filter(
        or_(Notification.user_id == user_id, Notification.is_broadcast == True),
        Notification.is_read == False,
        Notification.is_dismissed == False,
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

    enriched = [_enrich_notification(n, db) for n in notifications]

    return NotificationListOut(
        total=total,
        page=page,
        page_size=page_size,
        unread_count=unread_count,
        results=[NotificationOut.model_validate(d) for d in enriched],
    )


def get_unread_count(db: Session, user_id: uuid.UUID) -> NotificationCountOut:
    """Get notification counts for the bell indicator."""
    query = db.query(Notification).filter(
        or_(
            Notification.user_id == user_id,
            Notification.is_broadcast == True,
        ),
        Notification.is_read == False,
        Notification.is_dismissed == False,
    )

    total = query.count()
    critical = query.filter(
        or_(Notification.severity == "critical", Notification.priority == "critical")
    ).count()

    return NotificationCountOut(
        total=total,
        unread=total,
        critical=critical,
    )


def get_dashboard_summary(db: Session, user_id: uuid.UUID) -> NotificationDashboardSummary:
    """Get dashboard summary cards for the communication center."""
    base = db.query(Notification).filter(
        or_(
            Notification.user_id == user_id,
            Notification.is_broadcast == True,
        )
    )

    unread_count = base.filter(
        Notification.is_read == False, Notification.is_dismissed == False
    ).count()

    critical_alerts = base.filter(
        or_(Notification.severity == "critical", Notification.priority == "critical"),
        Notification.is_read == False,
        Notification.is_dismissed == False,
    ).count()

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_messages = base.filter(Notification.created_at >= today_start).count()

    pending_ack = base.filter(
        Notification.status == "unread",
        Notification.category.in_(["evidence_request", "investigation_update", "case_escalation", "officer_assistance"]),
        Notification.is_read == False,
    ).count()

    investigation_requests = base.filter(
        Notification.category.in_(["evidence_request", "investigation_update", "case_escalation", "officer_assistance"]),
        Notification.is_dismissed == False,
    ).count()

    broadcast_messages = base.filter(Notification.is_broadcast == True).count()

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
    """Get the most recent notifications for quick display (bell dropdown)."""
    notifications = (
        db.query(Notification)
        .filter(
            or_(
                Notification.user_id == user_id,
                Notification.is_broadcast == True,
            ),
            Notification.is_dismissed == False,
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_enrich_notification(n, db) for n in notifications]


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
