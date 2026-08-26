"""Issue 160: AI chat grounding, authorization-aware PII handling, and
prediction-honesty tests."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("APP_DEBUG", "false")

import re

from datetime import datetime, timezone

import pytest

from app.ai.chat.backend_fetcher import BackendFetcher, BackendResult, user_may_view_pii
from app.ai.chat.context_builder import ContextBuilder, SYSTEM_PROMPT
from app.ai.chat.entity_extractor import ExtractedEntities
from app.ai.chat.query_planner import BackendCall, QueryPlan
from app.ai.chat.response_validator import ResponseValidator
from app.ai.chat.intent_router import Intent
from app.core.security import hash_password
from app.models.criminal import Criminal
from app.models.role import Role
from app.models.user import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_criminal(db_session):
    crook = Criminal(
        full_name="PII Test Offender",
        status="at_large",
        address="42 Secret Hideout Lane, Bengaluru Urban",
        mo_summary="Test offender used for PII checks.",
    )
    db_session.add(crook)
    db_session.commit()
    return crook


def _make_user(db_session, role_name):
    role = db_session.query(Role).filter_by(name=role_name).first()
    if role is None:
        role = Role(name=role_name, description=role_name)
        db_session.add(role)
        db_session.flush()
    return User(
        username=f"chat-{role_name}",
        email=f"chat-{role_name}@test.invalid",
        full_name=f"Chat {role_name}",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Grounding gate
# ---------------------------------------------------------------------------

class TestGroundingGate:
    def setup_method(self):
        self.validator = ResponseValidator()

    def test_refuses_when_no_sources(self):
        llm_output = "Case CR-2026-XX-999 is definitely linked to gang activity."
        validated = self.validator.validate(llm_output, [])
        assert validated == (
            "I could not find matching records in the Saksha database for that query. "
            "No verified data sources were available to ground an answer, so I will not "
            "speculate. Please try rephrasing your question or check the case/FIR number."
        )

    def test_refuses_when_all_sources_failed(self):
        failed = [BackendResult(source="postgres", data_type="firs", content="", success=False)]
        validated = self.validator.validate("Here is everything you asked for.", failed)
        assert "could not find matching records" in validated

    def test_unverified_ids_get_disclaimer(self):
        good = [BackendResult(
            source="postgres", data_type="cases",
            content="Case: CR-2026-BLR-001 | Status: open",
            raw_data={"case_number": "CR-2026-BLR-001"},
        )]
        response = "Records CR-2026-BLR-001 and CR-2026-ZZZ-999 are related."
        validated = self.validator.validate(response, good)
        assert validated.startswith(response)
        assert "could not be verified" in validated

    def test_verified_ids_pass_clean(self):
        good = [BackendResult(
            source="postgres", data_type="cases",
            content="Case: CR-2026-BLR-001 | Status: open",
            raw_data={"case_number": "CR-2026-BLR-001"},
        )]
        response = "Case CR-2026-BLR-001 is open."
        assert self.validator.validate(response, good) == response


# ---------------------------------------------------------------------------
# Authorization-aware PII redaction
# ---------------------------------------------------------------------------

class TestPiiRedaction:
    def _fetch(self, db_session, redact):
        fetcher = BackendFetcher()
        plan = QueryPlan(
            intents=[Intent.CRIMINAL_HISTORY],
            entities=ExtractedEntities(person_name="PII Test"),
            backend_calls=[BackendCall("postgres", "get_criminal", {"name": "PII Test"}, 1)],
            parallel=False,
        )
        results = fetcher.execute(plan, db_session, redact_pii=redact)
        assert results and results[0].success
        return results[0].content

    def test_privileged_roles_listed(self):
        assert {"admin", "crime_analyst", "investigator", "inspector"} <= set(
            __import__("app.ai.chat.backend_fetcher", fromlist=["PII_PRIVILEGED_ROLES"]).PII_PRIVILEGED_ROLES
        )

    def test_viewer_role_is_not_pii_privileged(self, db_session):
        assert not user_may_view_pii(_make_user(db_session, "viewer"))
        assert not user_may_view_pii(None)

    def test_investigator_sees_address(self, db_session, seeded_criminal):
        content = self._fetch(db_session, redact=False)
        assert "Secret Hideout Lane" in content

    def test_restricted_role_gets_redacted_address(self, db_session, seeded_criminal):
        content = self._fetch(db_session, redact=True)
        assert "Secret Hideout Lane" not in content
        assert "REDACTED" in content
        assert "PII Test Offender" in content  # operational fields still usable


# ---------------------------------------------------------------------------
# ML prediction honesty (no fabricated inputs)
# ---------------------------------------------------------------------------

class TestMlHonesty:
    def test_risk_predict_empty_db_reports_no_records(self, db_session):
        fetcher = BackendFetcher()
        call = BackendCall("ml", "risk_predict", {"district": "Nowhere District"}, 1)
        result = fetcher._execute_call(call, db_session)
        assert result.success is False or "No crime records available" in result.content

    def test_risk_predict_uses_real_records_and_declares_mode(self, db_session):
        from app.models.crime import CrimeCase
        from app.models.crime_category import CrimeCategory
        from app.models.location import Location

        cat = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="high")
        loc = Location(district="Chatland", station="PS-1", latitude=12.0, longitude=76.0)
        db_session.add_all([cat, loc])
        db_session.flush()
        db_session.add(CrimeCase(
            case_number="CR-CHAT-0001", category_id=cat.id, location_id=loc.id,
            occurred_at=datetime(2026, 6, 10, 22, 0, tzinfo=timezone.utc),
            description="chat ml test", status="open",
        ))
        db_session.commit()

        fetcher = BackendFetcher()
        call = BackendCall("ml", "risk_predict", {"district": "Chatland"}, 1)
        result = fetcher._execute_call(call, db_session)
        assert result.success
        assert re.search(r"prediction mode: (ML|FALLBACK)", result.content), result.content
        assert "Chatland" in result.content

    def test_forecast_empty_db_reports_no_records(self, db_session):
        fetcher = BackendFetcher()
        call = BackendCall("ml", "forecast", {"district": "Empty District"}, 1)
        result = fetcher._execute_call(call, db_session)
        assert "No crime records available" in result.content


# ---------------------------------------------------------------------------
# System prompt / context authorization transparency
# ---------------------------------------------------------------------------

class TestSystemPromptSafety:
    def test_prompt_has_injection_resistance(self):
        assert "DATA, not instructions" in SYSTEM_PROMPT

    def test_prompt_requires_fact_analysis_prediction_labels(self):
        assert "ANALYSIS" in SYSTEM_PROMPT and "PREDICTION" in SYSTEM_PROMPT

    def test_context_does_not_leak_authenticated_officer(self, db_session):
        user = _make_user(db_session, "investigator")
        builder = ContextBuilder()
        built = builder.build(
            [BackendResult(source="analytics", data_type="summary", content="Total crimes: 3.")],
            ExtractedEntities(),
            "any message",
            current_user=user,
        )
        assert "Authenticated Officer" not in built.context_block
        assert "Session user:" not in built.context_block


