"""Tests for RagRetriever — vector retrieval augmentation over database records (issue #122)."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("APP_DEBUG", "false")

from app.ai.chat.backend_fetcher import BackendResult
from app.ai.chat.orchestrator import ChatOrchestrator
from app.ai.chat.rag_retriever import RagRetriever
from app.models.criminal import Criminal


def _seed_criminal(db, name: str, mo: str) -> Criminal:
    criminal = Criminal(
        full_name=name,
        aliases="",
        status="at_large",
        mo_summary=mo,
    )
    db.add(criminal)
    db.commit()
    db.refresh(criminal)
    return criminal


class TestRagRetriever:
    def test_returns_none_on_empty_database(self, db_session):
        assert RagRetriever().fetch(db_session, "any question") is None

    def test_retrieves_criminal_by_free_text(self, db_session):
        _seed_criminal(
            db_session,
            "Zorro Khan",
            "Poses as an insurance agent to enter homes and then commits burglary",
        )
        result = RagRetriever().fetch(db_session, "insurance agent fraud cases")
        assert isinstance(result, BackendResult)
        assert result.success
        assert result.data_type == "vector_retrieval"
        assert "Zorro Khan" in result.content
        assert result.raw_data and any(entry.get("name") == "Zorro Khan" for entry in result.raw_data)

    def test_irrelevant_question_returns_no_hits(self, db_session):
        _seed_criminal(db_session, "Zorro Khan", "Commits burglary at construction sites")
        assert RagRetriever().fetch(db_session, "quarterly budget allocation report") is None

    def test_orchestrator_includes_rag_context_in_answer(self, db_session):
        """Free-text recall must surface DB records even when structured
        intent-based fetching has no exact match (issue #122)."""
        _seed_criminal(
            db_session,
            "Zorro Khan",
            "Poses as an insurance agent to enter homes and then commits burglary",
        )
        orchestrator = ChatOrchestrator()
        result = orchestrator.process_message_sync(
            "Any suspects linked to insurance agent fraud?",
            session_id="rag-test",
            db=db_session,
        )
        answer = result["answer"].lower()
        assert "zorro khan" in answer

    def test_retrieval_covers_records_beyond_legacy_cap(self, db_session):
        """The RAG index must cover every record — the old build_rag_documents
        limit(40) silently dropped criminals past the first 40 (issue #122)."""
        fillers = [
            Criminal(full_name=f"Filler Crook {i:03d}", aliases="", status="at_large")
            for i in range(60)
        ]
        db_session.add_all(fillers)
        target = Criminal(
            full_name="Zaphod Beeblebrox",
            aliases="Two-Headed Thief",
            status="at_large",
            mo_summary="Steals rare purple umbrellas from museum exhibits during night tours",
        )
        db_session.add(target)
        db_session.commit()

        result = RagRetriever().fetch(db_session, "purple umbrella museum thief")
        assert isinstance(result, BackendResult)
        assert "Zaphod Beeblebrox" in result.content
        assert any(entry.get("name") == "Zaphod Beeblebrox" for entry in (result.raw_data or []))

