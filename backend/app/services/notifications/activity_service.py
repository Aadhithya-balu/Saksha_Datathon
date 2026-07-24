"""
Activity feed service — provides a unified activity feed by aggregating
notifications, audit logs, and case events into a chronological stream.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.models.crime import CrimeCase
from app.models.evidence import Evidence
from app.models.fir import FIR
from app.models.notification import Notification
from app.schemas.notification import ActivityEvent, ActivityFeedOut


def get_activity_feed(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 50,
    event_type: str | None = None,
    resource_type: str | None = None,
) -> ActivityFeedOut:
    """
    Build a unified activity feed from multiple sources:
    - Recent audit logs (case/FIR/evidence updates)
    - Recent notifications
    - Recent case timeline events
    """
    activities: list[ActivityEvent] = []

    # ── 1. Recent Audit Logs ─────────────────────────────────────
    audit_query = (
        db.query(AuditLog)
        .options(joinedload(AuditLog.user))
        .filter(
            AuditLog.timestamp >= datetime.now(timezone.utc) - timedelta(days=7)
        )
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )

    audit_logs = audit_query.all()
    for log in audit_logs:
        event_type_map = {
            "CREATE": "case_created" if log.resource_type == "CrimeCase"
                      else "fir_registered" if log.resource_type == "FIR"
                      else "evidence_added" if log.resource_type == "Evidence"
                      else "resource_created",
            "UPDATE": "status_changed" if log.resource_type == "CrimeCase"
                      else "resource_updated",
            "DELETE": "resource_deleted",
        }
        mapped_type = event_type_map.get(log.action, "system_event")

        # Filter by event_type if specified
        if event_type and mapped_type != event_type:
            continue
        if resource_type and log.resource_type.lower() != resource_type.lower():
            continue

        activities.append(ActivityEvent(
            id=f"audit-{log.id}",
            timestamp=log.timestamp.isoformat() if log.timestamp else "",
            event_type=mapped_type,
            title=f"{log.action} {log.resource_type}",
            description=log.details or f"{log.action} operation on {log.resource_type}",
            actor=log.user.full_name if log.user else None,
            actor_badge=log.user.username if log.user else None,
            resource_type=log.resource_type or "unknown",
            resource_id=log.resource_id,
            severity="info",
        ))

    # ── 2. Recent Critical Notifications ─────────────────────────
    notif_query = (
        db.query(Notification)
        .filter(
            or_(
                Notification.user_id == user_id,
                Notification.user_id.is_(None),
            ),
            Notification.created_at >= datetime.now(timezone.utc) - timedelta(days=7),
            Notification.is_dismissed == False,
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )

    notifications = notif_query.all()
    for notif in notifications:
        if event_type and notif.notification_type != event_type:
            continue
        if resource_type and notif.resource_type and notif.resource_type.lower() != resource_type.lower():
            continue

        severity_map = {
            "critical": "error",
            "high": "warning",
            "medium": "info",
            "low": "info",
        }

        activities.append(ActivityEvent(
            id=f"notif-{notif.id}",
            timestamp=notif.created_at.isoformat() if notif.created_at else "",
            event_type=notif.notification_type,
            title=notif.title,
            description=notif.message,
            actor=None,
            actor_badge=None,
            resource_type=notif.resource_type or "notification",
            resource_id=notif.resource_id,
            severity=severity_map.get(notif.severity, "info"),
        ))

    # ── 3. Recent Evidence Updates (from evidence_timeline) ─────
    try:
        from app.models.evidence_timeline import EvidenceTimeline
        timeline_entries = (
            db.query(EvidenceTimeline)
            .order_by(EvidenceTimeline.created_at.desc())
            .limit(limit)
            .all()
        )
        for entry in timeline_entries:
            if event_type and "evidence" not in event_type:
                continue
            activities.append(ActivityEvent(
                id=f"ev-tl-{entry.id}",
                timestamp=entry.created_at.isoformat() if entry.created_at else "",
                event_type="evidence_added",
                title=f"Evidence: {entry.action}",
                description=entry.remarks or f"Evidence timeline event: {entry.action}",
                actor=entry.actor,
                actor_badge=None,
                resource_type="Evidence",
                resource_id=str(entry.evidence_id) if entry.evidence_id else None,
                severity="info",
            ))
    except Exception:
        pass

    # ── Sort all activities by timestamp (newest first) ──────────
    activities.sort(key=lambda a: a.timestamp, reverse=True)

    return ActivityFeedOut(
        total=len(activities),
        results=activities[:limit],
    )


def get_live_event_timeline(
    db: Session,
    case_id: uuid.UUID | None = None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """
    Get a real-time event timeline for the live event timeline component.
    Aggregates from audit logs, notifications, and evidence timeline.
    Optionally filtered by case_id.
    """
    events: list[dict[str, Any]] = []

    # Audit logs
    audit_query = (
        db.query(AuditLog)
        .options(joinedload(AuditLog.user))
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )
    if case_id:
        audit_query = audit_query.filter(AuditLog.resource_id == str(case_id))

    for log in audit_query.all():
        events.append({
            "id": str(log.id),
            "timestamp": log.timestamp.isoformat() if log.timestamp else "",
            "type": "audit",
            "action": log.action,
            "resource_type": log.resource_type,
            "details": log.details,
            "actor": log.user.full_name if log.user else None,
            "actor_badge": log.user.username if log.user else None,
        })

    # Notifications
    notif_query = (
        db.query(Notification)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if case_id:
        notif_query = notif_query.filter(Notification.resource_id == str(case_id))

    for notif in notif_query.all():
        events.append({
            "id": str(notif.id),
            "timestamp": notif.created_at.isoformat() if notif.created_at else "",
            "type": "notification",
            "action": notif.title,
            "resource_type": notif.notification_type,
            "details": notif.message,
            "actor": None,
            "actor_badge": None,
        })

    # Sort by timestamp descending
    events.sort(key=lambda e: e["timestamp"], reverse=True)

    return events[:limit]

