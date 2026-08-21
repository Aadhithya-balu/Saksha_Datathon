from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("APP_DEBUG", "false")

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import Base, engine, SessionLocal
from app.services.rag.rag_service import build_rag_documents
from app.services.chat.chat_service import InvestigationChatService
from app.main import app


class DummyRole:
    name = "crime_analyst"


class DummyUser:
    id = "00000000-0000-0000-0000-000000000001"
    username = "testuser"
    email = "test@saksha.gov"
    role = DummyRole()
    badge_id = "TEST-0001"


def mock_user():
    return DummyUser()


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_build_rag_documents_extracts_entities():
    db: Session = SessionLocal()
    try:
        docs = build_rag_documents(db)
        assert isinstance(docs, list)
    finally:
        db.close()


def test_chat_service_process_query():
    db: Session = SessionLocal()
    try:
        service = InvestigationChatService(db)
        res = service.process_query("What are the active crime statistics?")
        assert res.answer
        assert res.summary
        assert isinstance(res.citations, list)
    finally:
        db.close()


def test_chat_api_streaming_endpoint(client: TestClient):
    app.dependency_overrides[get_current_user] = mock_user
    try:
        response = client.post(
            "/api/v2/ai/chat",
            json={"message": "Summarize top crime categories", "stream": True},
        )
        assert response.status_code == 200
        assert "application/x-ndjson" in response.headers.get("content-type", "")
        lines = [line for line in response.text.split("\n") if line.strip()]
        assert len(lines) >= 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
