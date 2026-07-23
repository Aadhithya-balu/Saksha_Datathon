from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("APP_DEBUG", "false")

from fastapi.testclient import TestClient

from app.ai.models.rag.chat_model import InvestigationChatModel
from app.ai.vectorstore.memory import InMemoryVectorStore, VectorDocument
from app.core.security import hash_password
from app.main import app
from app.models.role import Role
from app.models.user import User


def test_vector_store_search_ranks_relevant_docs():
    store = InMemoryVectorStore()
    store.index(
        [
            VectorDocument(id="1", text="Robbery incident in Bengaluru East district", title="A", metadata={"source": "fir"}),
            VectorDocument(id="2", text="Traffic violation near Mysuru station", title="B", metadata={"source": "report"}),
        ]
    )

    hits = store.search("robbery in Bengaluru", top_k=2)

    assert hits
    assert hits[0].document_id == "1"


def test_chat_model_returns_summary_and_entities():
    model = InvestigationChatModel()
    model.train(
        [
            {"id": "summary", "title": "Summary", "source": "dashboard", "content": "FIRs indicate repeated robbery incidents in Kalaburagi."},
            {"id": "district", "title": "District", "source": "districts", "content": "Kalaburagi has 12 cases."},
        ]
    )

    result = model.predict("Summarize the robbery pattern in Kalaburagi")

    assert result.answer
    assert result.summary
    assert "kalaburagi" in result.entities
    assert result.classification in {"FIR_SUMMARY", "CRIME_CLASSIFICATION", "ENTITY_EXTRACTION", "GENERAL_INVESTIGATION"}
    assert result.citations


def test_chat_api_query_endpoint(client: TestClient, db_session):
    role = Role(name="crime_analyst", description="Crime Analyst")
    db_session.add(role)
    db_session.flush()
    db_session.add(
        User(
            username="analyst",
            email="analyst@example.com",
            full_name="Test Analyst",
            hashed_password=hash_password("Password123!"),
            role_id=role.id,
            is_active=True,
        )
    )
    db_session.commit()

    login_response = client.post("/api/v1/auth/login", json={"username": "analyst", "password": "Password123!"})
    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/ai/chat/query",
        json={"message": "What are the top districts?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert "summary" in body
    assert "citations" in body
