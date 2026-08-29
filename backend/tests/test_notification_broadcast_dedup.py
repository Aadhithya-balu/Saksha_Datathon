"""Broadcast notification deduplication (NOTIFICATION_BROADCAST_DEDUP_HOURS).

Client-side flows (e.g. the Hotspots page spike alerts) fire a broadcast on
page load; per-tab sessionStorage is not enough when users open several tabs
or reload. The service must refuse to fan out an identical broadcast again
within the dedup window so the notification center is not flooded.
"""
from app.core.config import settings
from app.core.security import hash_password
from app.models.notification import Notification
from app.models.role import Role
from app.models.user import User
from app.schemas.notification import NotificationCreate
from app.services.notifications.notification_service import (
    create_broadcast_notification,
)


def _role(db_session, name: str = "officer") -> Role:
    role = db_session.query(Role).filter_by(name=name).first()
    if role is None:
        role = Role(name=name, description=name.title())
        db_session.add(role)
        db_session.flush()
    return role


def _active_user(db_session, username: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username.title(),
        hashed_password=hash_password("Password123!"),
        role_id=_role(db_session).id,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _broadcast_payload() -> NotificationCreate:
    return NotificationCreate(
        sender_id=None,
        recipient_id=None,
        subject="CRITICAL CRIME SURGE: Theft & Burglaries",
        notification_type="alert",
        category="SPIKE_ALERT",
        title="Critical Crime Surge in Theft & Burglaries",
        message="Crime volume doubled or worse (+400%: 5 recent vs 1 baseline).",
        priority="urgent",
        severity="critical",
        is_broadcast=True,
    )


def test_identical_broadcast_deduplicated(db_session):
    _active_user(db_session, "USER-A")
    _active_user(db_session, "USER-B")
    db_session.commit()

    payload = _broadcast_payload()
    first = create_broadcast_notification(db_session, payload)
    db_session.commit()
    assert len(first) == 2  # one row per active user

    second = create_broadcast_notification(db_session, payload)
    db_session.commit()
    assert len(second) == 1  # duplicate: existing broadcast returned, none created
    assert second[0].id == first[0].id

    total = db_session.query(Notification).filter(Notification.is_broadcast.is_(True)).count()
    assert total == 2


def test_distinct_broadcasts_not_deduplicated(db_session):
    _active_user(db_session, "USER-A")
    db_session.commit()

    first = create_broadcast_notification(db_session, _broadcast_payload())
    distinct = _broadcast_payload().model_copy(
        update={
            "subject": "CRITICAL CRIME SURGE: Narcotics",
            "title": "Critical Crime Surge in Narcotics",
        }
    )
    second = create_broadcast_notification(db_session, distinct)
    db_session.commit()

    assert first[0].id != second[0].id
    assert db_session.query(Notification).filter(Notification.is_broadcast.is_(True)).count() == 2


def test_broadcast_dedup_disabled_via_setting(db_session, monkeypatch):
    _active_user(db_session, "USER-A")
    db_session.commit()

    monkeypatch.setattr(settings, "NOTIFICATION_BROADCAST_DEDUP_HOURS", 0)
    first = create_broadcast_notification(db_session, _broadcast_payload())
    second = create_broadcast_notification(db_session, _broadcast_payload())
    db_session.commit()

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].id != second[0].id
    assert db_session.query(Notification).filter(Notification.is_broadcast.is_(True)).count() == 2


# ---------------------------------------------------------------------------
# Read-side dedup: broadcast fan-out must not flood the bell with copies.
# ---------------------------------------------------------------------------

def test_broadcast_shown_once_per_user_in_lists(db_session):
    """A broadcast fans out one row per user; lists/counts must show it once."""
    from app.services.notifications.notification_service import (
        get_dashboard_summary,
        get_notifications,
        get_recent_notifications,
        get_unread_count,
    )

    user_a = _active_user(db_session, "USER-A")
    _active_user(db_session, "USER-B")
    db_session.commit()

    payload = _broadcast_payload()
    create_broadcast_notification(db_session, payload)
    db_session.commit()

    listed = get_notifications(db_session, user_a.id)
    matching = [n for n in listed.results if n.subject == payload.subject]
    assert len(matching) == 1  # exactly one copy of the broadcast for user A

    count = get_unread_count(db_session, user_a.id)
    assert count.total == 1  # not one-per-recipient copies

    recent = get_recent_notifications(db_session, user_a.id)
    assert [n["subject"] for n in recent].count(payload.subject) == 1

    dash = get_dashboard_summary(db_session, user_a.id)
    assert dash.broadcast_messages == 1
    assert dash.unread_count == 1


def test_recipient_scoped_notifications_not_collapsed(db_session):
    """Two users with the same direct message keep both (no broadcast collapsing)."""
    from app.services.notifications.notification_service import (
        create_notification,
        get_notifications,
    )

    user_a = _active_user(db_session, "USER-A")
    user_b = _active_user(db_session, "USER-B")
    db_session.commit()

    for user in (user_a, user_b):
        create_notification(
            db_session,
            NotificationCreate(
                recipient_id=user.id,
                notification_type="message",
                category="system_notification",
                subject="Direct intel",
                title="Direct intel",
                message="personal",
            ),
        )
    db_session.commit()

    listed = get_notifications(db_session, user_a.id)
    assert sum(1 for n in listed.results if n.subject == "Direct intel") == 1
    assert get_notifications(db_session, user_b.id).total == 1