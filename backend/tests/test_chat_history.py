"""Persistent AI chat history tests: CRUD, auto-titling, ownership security, persistence wiring."""
import uuid

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User

HIST = "/api/v2/ai/chat-history"


def _make_user(db_session, username: str) -> User:
    role = db_session.query(Role).filter_by(name="investigator").first()
    if role is None:
        role = Role(name="investigator", description="Investigator")
        db_session.add(role)
        db_session.flush()
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username.replace("-", " ").title(),
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth(client, db_session):
    """Client bound to a fixed authenticated test user."""
    user = _make_user(db_session, "officer-one")
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    app.dependency_overrides.pop(get_current_user, None)


def _bind(client, user):
    client.app.dependency_overrides[get_current_user] = lambda: user


def test_requires_authentication(client):
    assert client.get(f"{HIST}/conversations").status_code == 401


def test_create_list_and_detail(auth):
    c, _ = auth
    r = c.post(f"{HIST}/conversations", json={})
    assert r.status_code == 201
    conv = r.json()
    assert conv["title"] == "New Chat"
    assert conv["message_count"] == 0

    listed = c.get(f"{HIST}/conversations").json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == conv["id"]
    assert "messages" not in listed["items"][0]

    detail = c.get(f"{HIST}/conversations/{conv['id']}").json()
    assert detail["messages"] == []
    assert detail["total_messages"] == 0


def test_add_message_and_auto_title(auth):
    c, _ = auth
    cid = c.post(f"{HIST}/conversations", json={}).json()["id"]
    r = c.post(f"{HIST}/conversations/{cid}/messages", json={
        "role": "user",
        "content": "Show case CR-2026-MYS-001 details and suspects",
    })
    assert r.status_code == 201

    detail = c.get(f"{HIST}/conversations/{cid}").json()
    assert detail["title"] == "Show case CR-2026-MYS-001 details and suspects"
    assert detail["total_messages"] == 1
    assert detail["messages"][0]["role"] == "user"


def test_auto_title_truncates_long_first_message(auth):
    c, _ = auth
    cid = c.post(f"{HIST}/conversations", json={}).json()["id"]
    long_msg = "Investigate the network of Vikram Yadav across Bengaluru Urban and Ballari districts immediately"
    c.post(f"{HIST}/conversations/{cid}/messages", json={"role": "user", "content": long_msg})
    title = c.get(f"{HIST}/conversations/{cid}").json()["title"]
    assert title.endswith("...")
    assert len(title) <= 52


def test_rename_conversation(auth):
    c, _ = auth
    cid = c.post(f"{HIST}/conversations", json={}).json()["id"]
    r = c.patch(f"{HIST}/conversations/{cid}", json={"title": "Intelligence Analysis"})
    assert r.status_code == 200
    assert r.json()["title"] == "Intelligence Analysis"
    assert c.get(f"{HIST}/conversations/{cid}").json()["title"] == "Intelligence Analysis"

    bad = c.patch(f"{HIST}/conversations/{cid}", json={"title": "   "})
    assert bad.status_code == 422


def test_detail_pagination_returns_newest_window(auth):
    c, _ = auth
    cid = c.post(f"{HIST}/conversations", json={}).json()["id"]
    for i in range(5):
        c.post(f"{HIST}/conversations/{cid}/messages", json={
            "role": "user", "content": f"question number {i}",
        })
    page = c.get(f"{HIST}/conversations/{cid}", params={"limit": 2}).json()
    assert page["total_messages"] == 5
    assert [m["content"] for m in page["messages"]] == ["question number 3", "question number 4"]


def test_delete_single_conversation(auth):
    c, _ = auth
    cid = c.post(f"{HIST}/conversations", json={}).json()["id"]
    c.post(f"{HIST}/conversations/{cid}/messages", json={"role": "user", "content": "hi"})
    r = c.delete(f"{HIST}/conversations/{cid}")
    assert r.status_code == 204
    assert c.get(f"{HIST}/conversations/{cid}").status_code == 404
    assert c.get(f"{HIST}/conversations").json()["total"] == 0


def test_delete_all_history(auth):
    c, _ = auth
    for _ in range(3):
        c.post(f"{HIST}/conversations", json={})
    r = c.delete(f"{HIST}/conversations")
    assert r.status_code == 200
    assert r.json()["deleted"] == 3
    assert c.get(f"{HIST}/conversations").json()["total"] == 0


def test_temporary_flag_excludes_from_saved_history(auth):
    c, _ = auth
    seeded = [{
        "role": "user", "content": "sensitive question",
    }, {
        "role": "assistant", "content": "sensitive answer",
    }]
    cid = c.post(f"{HIST}/conversations", json={"temporary": True, "messages": seeded}).json()
    assert cid["is_temporary"] is True
    assert cid["total_messages"] == 2

    assert c.get(f"{HIST}/conversations").json()["total"] == 0
    assert c.get(f"{HIST}/conversations", params={"include_temporary": True}).json()["total"] == 1

    saved = c.patch(f"{HIST}/conversations/{cid['id']}", json={"is_temporary": False})
    assert saved.status_code == 200
    assert c.get(f"{HIST}/conversations").json()["total"] == 1


def test_search_filters_titles(auth):
    c, _ = auth
    a = c.post(f"{HIST}/conversations", json={"title": "Case Analysis Discussion"}).json()
    c.post(f"{HIST}/conversations", json={"title": "Weekly Briefing"})
    hits = c.get(f"{HIST}/conversations", params={"q": "case analysis"}).json()
    assert hits["total"] == 1
    assert hits["items"][0]["id"] == a["id"]


class TestOwnershipSecurity:
    def test_other_user_cannot_read(self, client, db_session):
        owner = _make_user(db_session, "owner-alice")
        intruder = _make_user(db_session, "intruder-bob")

        _bind(client, owner)
        cid = client.post(f"{HIST}/conversations", json={}).json()["id"]

        _bind(client, intruder)
        assert client.get(f"{HIST}/conversations/{cid}").status_code == 404
        listed = client.get(f"{HIST}/conversations").json()
        assert all(item["id"] != cid for item in listed["items"])

    def test_other_user_cannot_modify_or_delete(self, client, db_session):
        owner = _make_user(db_session, "owner-carol")
        intruder = _make_user(db_session, "intruder-dave")

        _bind(client, owner)
        cid = client.post(f"{HIST}/conversations", json={}).json()["id"]

        _bind(client, intruder)
        assert client.patch(f"{HIST}/conversations/{cid}", json={"title": "hijacked"}).status_code == 404
        assert client.post(
            f"{HIST}/conversations/{cid}/messages", json={"role": "user", "content": "x"}
        ).status_code == 404
        assert client.delete(f"{HIST}/conversations/{cid}").status_code == 404
        # Owner data untouched.
        _bind(client, owner)
        assert client.get(f"{HIST}/conversations/{cid}").status_code == 200

    def test_intruder_delete_all_leaves_owner_intact(self, client, db_session):
        owner = _make_user(db_session, "owner-eve")
        intruder = _make_user(db_session, "intruder-frank")

        _bind(client, owner)
        cid = client.post(f"{HIST}/conversations", json={}).json()["id"]

        _bind(client, intruder)
        client.post(f"{HIST}/conversations", json={})
        deleted = client.delete(f"{HIST}/conversations").json()["deleted"]
        assert deleted == 1

        _bind(client, owner)
        assert client.get(f"{HIST}/conversations/{cid}").status_code == 200

    def test_chat_endpoint_rejects_foreign_conversation(self, client, db_session, monkeypatch):
        from app.routes import ai_chat as ai_chat_route

        class FakeOrch:
            def process_message_sync(self, message, sid, db, history=None):
                return {"answer": "ok", "summary": "", "entities": [], "classification": "general"}

        monkeypatch.setattr(ai_chat_route, "_orchestrator", FakeOrch())

        owner = _make_user(db_session, "owner-gina")
        intruder = _make_user(db_session, "intruder-hank")

        _bind(client, owner)
        cid = client.post(f"{HIST}/conversations", json={}).json()["id"]

        _bind(client, intruder)
        r = client.post("/api/v2/ai/chat", json={"message": "hello", "conversation_id": cid})
        assert r.status_code == 404


class TestChatPersistenceWiring:
    @staticmethod
    def _fake_orch(answer="Mocked analysis.", capture=None):
        class FakeOrch:
            def process_message_sync(self, message, sid, db, history=None):
                if capture is not None:
                    capture.append(history)
                return {
                    "answer": answer, "summary": "", "entities": [],
                    "classification": "crime_statistics",
                    "sources": ["dashboard"], "citations": [],
                }

        return FakeOrch()

    def test_sync_chat_persists_exchange_and_titles(self, auth, monkeypatch):
        from app.routes import ai_chat as ai_chat_route

        c, _ = auth
        monkeypatch.setattr(ai_chat_route, "_orchestrator", self._fake_orch())

        r = c.post("/api/v2/ai/chat", json={"message": "Show crime statistics", "stream": False, "persist": True})
        assert r.status_code == 200
        body = r.json()
        cid = body["conversation_id"]
        assert cid

        detail = c.get(f"{HIST}/conversations/{cid}").json()
        assert detail["total_messages"] == 2
        roles = [m["role"] for m in detail["messages"]]
        contents = [m["content"] for m in detail["messages"]]
        assert roles == ["user", "assistant"]
        assert contents[0] == "Show crime statistics"
        assert contents[1] == "Mocked analysis."
        assert detail["title"].startswith("Show crime statistics")
        assert detail["messages"][1]["classification"] == "crime_statistics"

    def test_second_exchange_receives_db_history(self, auth, monkeypatch):
        from app.routes import ai_chat as ai_chat_route

        c, _ = auth
        seen: list = []
        monkeypatch.setattr(ai_chat_route, "_orchestrator", self._fake_orch(capture=seen))

        c.post("/api/v2/ai/chat", json={"message": "first question", "persist": True})
        r = c.post("/api/v2/ai/chat", json={"message": "second question", "conversation_id": None, "persist": True})
        cid = r.json()["conversation_id"]
        # Continue the same conversation explicitly.
        c.post("/api/v2/ai/chat", json={"message": "third question", "conversation_id": cid, "persist": True})

        second_hist, third_hist = seen[1], seen[2]
        assert [(m["role"], m["content"]) for m in third_hist] == [
            ("user", "second question"),
            ("assistant", "Mocked analysis."),
        ]
        assert second_hist == []

    def test_failed_generation_leaves_no_records(self, auth, monkeypatch):
        from app.routes import ai_chat as ai_chat_route

        c, _ = auth

        class FailingOrch:
            def process_message_sync(self, message, sid, db, history=None):
                raise RuntimeError("llm unavailable")

        monkeypatch.setattr(ai_chat_route, "_orchestrator", FailingOrch())
        # ServerErrorMiddleware re-raises unhandled errors through the TestClient;
        # what matters is that nothing was persisted.
        with pytest.raises(RuntimeError):
            c.post("/api/v2/ai/chat", json={"message": "this will fail", "persist": True})
        # Auto-created shell conversation must have been discarded.
        assert c.get(f"{HIST}/conversations").json()["total"] == 0

    def test_temporary_chat_persists_nothing(self, auth, monkeypatch):
        from app.routes import ai_chat as ai_chat_route

        c, _ = auth
        monkeypatch.setattr(ai_chat_route, "_orchestrator", self._fake_orch())
        r = c.post("/api/v2/ai/chat", json={"message": "off the record", "persist": False})
        assert r.status_code == 200
        assert r.json().get("conversation_id") is None
        assert c.get(f"{HIST}/conversations").json()["total"] == 0

    def test_stream_persists_after_final_event(self, auth, monkeypatch):
        from app.routes import ai_chat as ai_chat_route

        c, _ = auth

        class FakeStreamOrch:
            async def process_message(self, message, sid, db, history=None):
                yield b'{"type": "token", "content": "Hel"}\n'
                yield b'{"type": "token", "content": "lo"}\n'
                yield (
                    b'{"type": "final", "content": {"answer": "Hello officer", '
                    b'"classification": "general", "sources": [], "citations": []}}\n'
                )

        monkeypatch.setattr(ai_chat_route, "_orchestrator", FakeStreamOrch())
        r = c.post("/api/v2/ai/chat", json={"message": "greet me", "stream": True, "persist": True})
        assert r.status_code == 200
        events = [line for line in r.text.splitlines() if line.strip()]
        types = [__import__("json").loads(e)["type"] for e in events]
        assert types[0] == "meta"
        assert types[-1] == "meta"
        meta_id = __import__("json").loads(events[0])["content"]["conversation_id"]
        assert uuid.UUID(meta_id)

        detail = c.get(f"{HIST}/conversations/{meta_id}").json()
        assert detail["total_messages"] == 2
        assert detail["messages"][-1]["content"] == "Hello officer"

