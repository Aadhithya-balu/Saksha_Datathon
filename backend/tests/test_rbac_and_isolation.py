"""RBAC enforcement and notification ownership isolation tests."""
import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User

NOTIF = "/api/v2/notifications"
USERS = "/api/v2/users"


def _role(db_session, name: str) -> Role:
    role = db_session.query(Role).filter_by(name=name).first()
    if role is None:
        role = Role(name=name, description=name.title())
        db_session.add(role)
        db_session.flush()
    return role


def _make_user(db_session, username: str, role_name: str = "investigator") -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username.replace("-", " ").title(),
        hashed_password=hash_password("Password123!"),
        role_id=_role(db_session, role_name).id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def as_user(client, db_session):
    """Return a helper binding the client to an arbitrary user."""

    def _bind(username: str, role_name: str = "investigator"):
        user = _make_user(db_session, username, role_name)
        client.app.dependency_overrides[get_current_user] = lambda: user
        return user

    yield _bind
    client.app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# RBAC authorization
# ---------------------------------------------------------------------------


def test_endpoints_require_authentication(client):
    assert client.get(f"{USERS}").status_code == 401
    assert client.get(f"{NOTIF}").status_code == 401
    assert client.get("/api/v2/dashboard/summary").status_code == 401


def test_user_listing_admin_only(client, db_session, as_user):
    admin = _make_user(db_session, "chief-admin", "admin")
    investigator = _make_user(db_session, "street-io", "investigator")

    client.app.dependency_overrides[get_current_user] = lambda: investigator
    denied = client.get(f"{USERS}")
    assert denied.status_code in (403,)

    client.app.dependency_overrides[get_current_user] = lambda: admin
    allowed = client.get(f"{USERS}")
    assert allowed.status_code == 200

    client.app.dependency_overrides.pop(get_current_user, None)


def test_notifications_open_to_all_authenticated_roles(client, db_session, as_user):
    for username, role in [("analyst-one", "crime_analyst"), ("viewer-one", "viewer")]:
        as_user(username, role)
        assert client.get(f"{NOTIF}/count").status_code == 200


# ---------------------------------------------------------------------------
# Notification CRUD + cross-user isolation
# ---------------------------------------------------------------------------


def _create_notification(client, subject="Intel drop", recipient_id=None):
    payload = {
        "subject": subject,
        "title": subject,
        "message": "Surveillance update",
        "notification_type": "message",
    }
    if recipient_id is not None:
        payload["recipient_id"] = str(recipient_id)
    r = client.post(f"{NOTIF}", json=payload)
    assert r.status_code in (200, 201), r.text
    return r.json()


def _private_notification(client, owner):
    """Create a notification addressed specifically to `owner`."""
    return _create_notification(client, subject="Owner only intel", recipient_id=owner.username)


def test_create_list_and_count(client, db_session, as_user):
    owner = as_user("notif-owner")
    created = _private_notification(client, owner)

    listed = client.get(f"{NOTIF}").json()
    assert listed["total"] >= 1
    assert any(n["id"] == created["id"] for n in listed["results"])

    count = client.get(f"{NOTIF}/count").json()
    assert count["total"] >= 1 and count["unread"] >= 1

    read = client.put(f"{NOTIF}/{created['id']}/read")
    assert read.status_code == 200 and read.json()["success"] is True


def test_notification_isolation_between_users(client, db_session, as_user):
    owner = as_user("notif-owner-a")
    _private_notification(client, owner)

    intruder = _make_user(db_session, "notif-intruder-b")
    client.app.dependency_overrides[get_current_user] = lambda: intruder
    other_view = client.get(f"{NOTIF}?page_size=100").json()
    assert all(n["subject"] != "Owner only intel" for n in other_view["results"])
    assert str(owner.id) != str(intruder.id)


def test_intruder_cannot_mutate_foreign_notification(client, db_session, as_user):
    owner = as_user("notif-owner-c")
    created = _private_notification(client, owner)

    intruder = _make_user(db_session, "notif-intruder-d")
    client.app.dependency_overrides[get_current_user] = lambda: intruder

    mutate = client.put(f"{NOTIF}/{created['id']}/read")
    assert mutate.status_code in (403, 404)

    delete = client.delete(f"{NOTIF}/{created['id']}")
    assert delete.status_code in (403, 404)


def test_malformed_notification_payload_rejected(client, db_session, as_user):
    as_user("notif-validator")
    r = client.post(f"{NOTIF}", json={"message": "missing required fields"})
    assert r.status_code == 422

