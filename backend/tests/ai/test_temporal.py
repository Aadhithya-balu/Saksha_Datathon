"""Temporal awareness: 'any crime today?' style questions.

Covers the planner hook (recent_activity call), the System Clock context
section, the analytics service window query, and local-template answers that
must report today's activity instead of dumping timeless dossiers.
"""
from __future__ import annotations

from datetime import datetime, timedelta


from app.ai.chat.context_builder import ContextBuilder
from app.ai.chat.backend_fetcher import BackendResult
from app.ai.chat.entity_extractor import EntityExtractor, ExtractedEntities
from app.ai.chat.intent_router import Intent
from app.ai.chat.query_planner import QueryPlanner
from app.core.config import settings
from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.fir import FIR
from app.services.analytics_service import recent_activity

from tests.ai.test_llm_generator import _collect_local


# ---------------------------------------------------------------------------
# Planner: temporal entities must schedule a recent_activity fetch first.
# ---------------------------------------------------------------------------

class TestTemporalPlanner:
    def test_today_plans_recent_activity_first(self):
        plan = QueryPlanner().plan([Intent.CRIMINAL_HISTORY], ExtractedEntities(date_range_days=0))
        activity = [c for c in plan.backend_calls if c.method == "recent_activity"]
        assert len(activity) == 1
        assert activity[0].params["days"] == 0
        assert plan.backend_calls[0].method == "recent_activity"

    def test_last_week_uses_window(self):
        plan = QueryPlanner().plan([Intent.DASHBOARD_ANALYTICS], ExtractedEntities(date_range_days=7))
        activity = [c for c in plan.backend_calls if c.method == "recent_activity"]
        assert len(activity) == 1
        assert activity[0].params["days"] == 7

    def test_extractor_flags_today(self):
        entities = EntityExtractor().extract("is there any criminal records today?")
        assert entities.date_range_days == 0

    def test_no_temporal_entity_skips_hook(self):
        plan = QueryPlanner().plan([Intent.CRIMINAL_HISTORY], ExtractedEntities())
        assert all(c.method != "recent_activity" for c in plan.backend_calls)


# ---------------------------------------------------------------------------
# Context builder: System Clock section grounds every successful answer.
# ---------------------------------------------------------------------------

class TestSystemClockContext:
    def test_clock_section_prepended(self):
        result = BackendResult(source="postgres", data_type="dossiers", content="Ramu Swamy: Status=ACTIVE")
        built = ContextBuilder().build([result], ExtractedEntities(), "test question")
        assert built.context_block.startswith("### System Clock")
        assert "Current date and time:" in built.context_block
        assert "Ramu Swamy" in built.context_block

    def test_empty_results_have_no_clock(self):
        failed = BackendResult(source="postgres", data_type="x", content="", success=False, error="boom")
        built = ContextBuilder().build([failed], ExtractedEntities(), "test question")
        assert "System Clock" not in built.context_block


# ---------------------------------------------------------------------------
# Analytics service: recent_activity counts by created_at window.
# ---------------------------------------------------------------------------

class TestRecentActivity:
    def _make_case(self, db_session, case_number: str) -> CrimeCase:
        from app.models.crime_category import CrimeCategory
        from app.models.location import Location
        category = CrimeCategory(name=f"Temporal Test {case_number}")
        location = Location(district="Bengaluru Urban", latitude=12.97, longitude=77.59)
        db_session.add_all([category, location])
        db_session.flush()
        case = CrimeCase(case_number=case_number, description="temporal test",
                         status="OPEN", priority="MEDIUM", progress=0,
                         occurred_at=datetime.now(),
                         category_id=category.id, location_id=location.id)
        db_session.add(case)
        db_session.flush()
        return case

    def test_counts_today_only(self, db_session):
        case = self._make_case(db_session, "CR-TEMPORAL-001")
        db_session.add(FIR(fir_number="FIR-TEST-001", crime_case_id=case.id,
                           complainant_name="Test Complainant",
                           filed_at=datetime.now(), created_at=datetime.now()))
        db_session.add(FIR(fir_number="FIR-TEST-OLD", crime_case_id=case.id,
                           complainant_name="Old Complainant",
                           filed_at=datetime.now() - timedelta(days=30),
                           created_at=datetime.now() - timedelta(days=30)))
        db_session.add(Criminal(full_name="New Crook", status="ACTIVE",
                                created_at=datetime.now() - timedelta(days=2)))
        db_session.commit()

        data = recent_activity(db_session, days=0)
        assert data["new_firs"] == 1
        assert data["new_criminals"] == 0  # created 2 days ago is not 'today'
        assert "today" in data["period_label"]
        assert "FIR-TEST-001" in data["latest_fir"]

    def test_rolling_window(self, db_session):
        db_session.add(Criminal(full_name="Week Crook", status="ACTIVE",
                                created_at=datetime.now() - timedelta(days=2)))
        db_session.commit()
        data = recent_activity(db_session, days=7)
        assert data["new_criminals"] >= 1


# ---------------------------------------------------------------------------
# Local generator: temporal question must answer from recency facts.
# ---------------------------------------------------------------------------

_CLOCK = "### System Clock\nCurrent date and time: 2026-08-23 14:05 (Sunday)"

_RECENCY = (
    "### Saksha Analytics Engine — Recent Activity\n"
    "System date/time now: 2026-08-23 14:05\n"
    "Period analyzed: today (2026-08-23)\n"
    "New crime cases registered: 0\n"
    "New FIRs filed: 0\n"
    "New evidence items added: 1\n"
    "Most recent FIR on file: FIR-793/MYS/2026 filed 2026-07-24 15:34"
)

_DOSSIERS = (
    "### Saksha PostgreSQL Database — Offender Dossiers\n"
    "Ramu Swamy: Status=ACTIVE, Classification=A-CATEGORY, Risk=100, "
    "Active Districts=Belagavi, Bengaluru Urban, Gang=Theft & Burglaries"
)


class TestLocalTemporalAnswers:
    def _gen(self, monkeypatch):
        from app.ai.chat.llm_generator import LLMGenerator
        monkeypatch.setattr(settings, "GROQ_API_KEY", None)
        monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
        monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
        monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
        return LLMGenerator()

    def test_today_question_reports_activity_not_dossiers(self, monkeypatch):
        context = f"{_CLOCK}\n\n{_RECENCY}\n\n{_DOSSIERS}"
        gen = self._gen(monkeypatch)
        answer = _collect_local(gen, "is there any criminal records today?", context, "sys")
        assert "could not find" not in answer.lower()
        assert "New FIRs filed: 0" in answer
        # timeless dossiers must not drown out the temporal facts
        assert "Ramu Swamy" not in answer

    def test_non_temporal_question_hides_clock(self, monkeypatch):
        context = f"{_CLOCK}\n\n{_DOSSIERS}"
        gen = self._gen(monkeypatch)
        answer = _collect_local(
            gen, "list active criminals in Bengaluru Urban", context, "sys",
        )
        assert "Current date and time" not in answer
        assert "Ramu Swamy" in answer
