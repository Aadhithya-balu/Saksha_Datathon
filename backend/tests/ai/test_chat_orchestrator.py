"""Tests for the Saksha AI Chat Orchestrator pipeline components."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("APP_DEBUG", "false")

import json
import pytest
from unittest.mock import MagicMock, patch

from app.ai.chat.intent_router import IntentRouter, Intent, IntentResult
from app.ai.chat.entity_extractor import EntityExtractor, ExtractedEntities
from app.ai.chat.query_planner import QueryPlanner, QueryPlan, BackendCall
from app.ai.chat.backend_fetcher import BackendFetcher, BackendResult
from app.ai.chat.context_builder import ContextBuilder, BuiltContext
from app.ai.chat.response_validator import ResponseValidator
from app.ai.chat.memory import ChatMemory, memory
from app.ai.chat.orchestrator import ChatOrchestrator


# ── Intent Router Tests ──────────────────────────────────────────────

class TestIntentRouter:
    def setup_method(self):
        self.router = IntentRouter()

    def test_fir_lookup_direct(self):
        result = self.router.detect("Show me FIR 2026/104")
        assert Intent.FIR_LOOKUP in result.intents
        assert result.confidence > 0

    def test_fir_lookup_by_keyword(self):
        result = self.router.detect("Search for FIRs filed last week")
        assert Intent.FIR_LOOKUP in result.intents

    def test_case_details_exact_id(self):
        result = self.router.detect("Show case CR-2026-BLR-001")
        assert Intent.CASE_DETAILS in result.intents

    def test_case_details_keyword(self):
        result = self.router.detect("What is the case status?")
        assert Intent.CASE_DETAILS in result.intents

    def test_criminal_history(self):
        result = self.router.detect("Tell me about criminal Ramu Swamy")
        assert Intent.CRIMINAL_HISTORY in result.intents

    def test_criminal_network(self):
        result = self.router.detect("Who is connected to Vikram Yadav?")
        assert Intent.CRIMINAL_NETWORK in result.intents

    def test_crime_statistics(self):
        result = self.router.detect("What are the total crime statistics?")
        assert Intent.CRIME_STATISTICS in result.intents

    def test_hotspot_analysis(self):
        result = self.router.detect("Show me crime hotspots in Bengaluru")
        assert Intent.HOTSPOT_ANALYSIS in result.intents

    def test_predictions(self):
        result = self.router.detect("Predict crime risk in Mysuru district")
        assert Intent.PREDICTIONS in result.intents

    def test_notifications(self):
        result = self.router.detect("Show me recent alerts and notifications")
        assert Intent.NOTIFICATIONS in result.intents

    def test_dashboard_analytics(self):
        result = self.router.detect("Give me a dashboard overview")
        assert Intent.DASHBOARD_ANALYTICS in result.intents

    def test_officer_info(self):
        result = self.router.detect("Tell me about officer Ravi Kumar")
        assert Intent.OFFICER_INFO in result.intents

    def test_similar_cases(self):
        result = self.router.detect("Find similar cases with same modus operandi")
        assert Intent.SIMILAR_CASES in result.intents

    def test_general_fallback(self):
        result = self.router.detect("hello")
        assert Intent.GENERAL in result.intents

    def test_compound_query_multi_intent(self):
        result = self.router.detect("Show crime statistics and identify hotspots")
        assert len(result.intents) >= 2

    def test_confidence_range(self):
        result = self.router.detect("Show FIR 2026/104")
        assert 0 <= result.confidence <= 1.0

    def test_scores_dict_populated(self):
        result = self.router.detect("Show FIR 2026/104")
        assert len(result.scores) > 0


# ── Entity Extractor Tests ───────────────────────────────────────────

class TestEntityExtractor:
    def setup_method(self):
        self.extractor = EntityExtractor()

    def test_case_id_extraction(self):
        entities = self.extractor.extract("Show me case CR-2026-BLR-001")
        assert entities.case_id == "CR-2026-BLR-001"

    def test_fir_number_with_prefix(self):
        entities = self.extractor.extract("Show FIR 2026/104")
        assert entities.fir_number == "2026/104"

    def test_fir_number_bare(self):
        entities = self.extractor.extract("Show me FIR 2024/089")
        assert entities.fir_number is not None

    def test_person_name_extraction(self):
        entities = self.extractor.extract("Tell me about accused Ramu Swamy")
        assert entities.person_name is not None
        assert "Ramu" in entities.person_name

    def test_person_name_who_is(self):
        entities = self.extractor.extract("Who is Vikram Yadav")
        assert entities.person_name is not None

    def test_district_extraction(self):
        entities = self.extractor.extract("Crimes in Bengaluru Urban district")
        assert entities.district == "Bengaluru Urban"

    def test_district_mysuru(self):
        entities = self.extractor.extract("Hotspots in Mysuru")
        assert entities.district == "Mysuru"

    def test_station_extraction(self):
        entities = self.extractor.extract("FIRs from Whitefield station")
        assert entities.station == "Whitefield"

    def test_crime_category_extraction(self):
        entities = self.extractor.extract("Cyber crime cases in the city")
        assert entities.crime_category == "Cyber Crime"

    def test_date_extraction_dmy(self):
        entities = self.extractor.extract("Crimes on 15/01/2026")
        assert entities.date == "15/01/2026"

    def test_date_extraction_ymd(self):
        entities = self.extractor.extract("Events on 2026-03-15")
        assert entities.date == "2026-03-15"

    def test_date_range_last_week(self):
        entities = self.extractor.extract("Crimes from last week")
        assert entities.date_range_days == 7

    def test_date_range_last_month(self):
        entities = self.extractor.extract("Show me last month data")
        assert entities.date_range_days == 30

    def test_vehicle_number(self):
        entities = self.extractor.extract("Vehicle KA-01-AB-1234 was spotted")
        assert entities.vehicle_number is not None
        assert "KA" in entities.vehicle_number

    def test_phone_number(self):
        entities = self.extractor.extract("Call +91 94420-12891")
        assert entities.phone_number is not None

    def test_risk_level(self):
        entities = self.extractor.extract("Show high risk offenders")
        assert entities.risk_level is not None

    def test_to_dict(self):
        entities = self.extractor.extract("Show FIR 2026/104 in Bengaluru")
        d = entities.to_dict()
        assert isinstance(d, dict)
        assert "fir_number" in d
        assert "district" in d

    def test_no_entities(self):
        entities = self.extractor.extract("hello world")
        assert entities.case_id is None
        assert entities.fir_number is None
        assert entities.person_name is None

    def test_multiple_entities(self):
        entities = self.extractor.extract("Show CR-2026-BLR-001 case in Bengaluru Urban from last month")
        assert entities.case_id is not None
        assert entities.district is not None
        assert entities.date_range_days is not None


# ── Query Planner Tests ──────────────────────────────────────────────

class TestQueryPlanner:
    def setup_method(self):
        self.planner = QueryPlanner()

    def test_fir_lookup_with_number(self):
        entities = ExtractedEntities(fir_number="2026/104")
        plan = self.planner.plan([Intent.FIR_LOOKUP], entities)
        assert any(c.method == "get_fir" for c in plan.backend_calls)
        assert plan.backend_calls[0].service == "postgres"

    def test_fir_lookup_without_number(self):
        entities = ExtractedEntities(person_name="Ramu")
        plan = self.planner.plan([Intent.FIR_LOOKUP], entities)
        assert any(c.method == "search_firs" for c in plan.backend_calls)

    def test_case_details_with_id(self):
        entities = ExtractedEntities(case_id="CR-2026-001")
        plan = self.planner.plan([Intent.CASE_DETAILS], entities)
        assert any(c.method == "get_case" for c in plan.backend_calls)

    def test_criminal_history_plan(self):
        entities = ExtractedEntities(person_name="Vikram Yadav")
        plan = self.planner.plan([Intent.CRIMINAL_HISTORY], entities)
        services = {c.service for c in plan.backend_calls}
        assert "postgres" in services
        assert "neo4j" in services

    def test_crime_statistics_plan(self):
        entities = ExtractedEntities()
        plan = self.planner.plan([Intent.CRIME_STATISTICS], entities)
        assert len(plan.backend_calls) >= 3
        assert all(c.service in ("analytics", "postgres") for c in plan.backend_calls)

    def test_hotspot_plan(self):
        entities = ExtractedEntities(district="Bengaluru Urban")
        plan = self.planner.plan([Intent.HOTSPOT_ANALYSIS], entities)
        services = {c.service for c in plan.backend_calls}
        assert "analytics" in services

    def test_network_plan(self):
        entities = ExtractedEntities(person_name="Ramu Swamy")
        plan = self.planner.plan([Intent.CRIMINAL_NETWORK], entities)
        assert any(c.service == "neo4j" for c in plan.backend_calls)

    def test_predictions_plan(self):
        entities = ExtractedEntities(district="Mysuru")
        plan = self.planner.plan([Intent.PREDICTIONS], entities)
        assert any(c.service == "ml" for c in plan.backend_calls)

    def test_notifications_plan(self):
        entities = ExtractedEntities()
        plan = self.planner.plan([Intent.NOTIFICATIONS], entities)
        assert any(c.method == "list_notifications" for c in plan.backend_calls)

    def test_dashboard_plan(self):
        entities = ExtractedEntities()
        plan = self.planner.plan([Intent.DASHBOARD_ANALYTICS], entities)
        assert len(plan.backend_calls) >= 3

    def test_general_plan(self):
        entities = ExtractedEntities()
        plan = self.planner.plan([Intent.GENERAL], entities)
        assert len(plan.backend_calls) >= 1

    def test_deduplication(self):
        entities = ExtractedEntities()
        plan = self.planner.plan([Intent.CRIME_STATISTICS, Intent.DASHBOARD_ANALYTICS], entities)
        seen = set()
        for c in plan.backend_calls:
            key = (c.service, c.method)
            assert key not in seen
            seen.add(key)

    def test_parallel_flag(self):
        entities = ExtractedEntities()
        plan = self.planner.plan([Intent.CRIME_STATISTICS], entities)
        assert plan.parallel is True

    def test_plan_description(self):
        entities = ExtractedEntities()
        plan = self.planner.plan([Intent.CRIME_STATISTICS], entities)
        assert isinstance(plan.description, str)
        assert len(plan.description) > 0


# ── Backend Fetcher Tests ────────────────────────────────────────────

class TestBackendFetcher:
    def setup_method(self):
        self.fetcher = BackendFetcher()

    def test_execute_returns_list(self, db_session):
        plan = QueryPlan(
            intents=[Intent.GENERAL],
            entities=ExtractedEntities(),
            backend_calls=[BackendCall("analytics", "dashboard_summary", {}, 1)],
        )
        results = self.fetcher.execute(plan, db_session)
        assert isinstance(results, list)
        assert len(results) == 1

    def test_analytics_dashboard_summary(self, db_session):
        plan = QueryPlan(
            intents=[Intent.CRIME_STATISTICS],
            entities=ExtractedEntities(),
            backend_calls=[BackendCall("analytics", "dashboard_summary", {}, 1)],
        )
        results = self.fetcher.execute(plan, db_session)
        assert results[0].success is True
        assert results[0].content  # should have some text

    def test_analytics_category_breakdown(self, db_session):
        plan = QueryPlan(
            intents=[Intent.CRIME_STATISTICS],
            entities=ExtractedEntities(),
            backend_calls=[BackendCall("analytics", "category_breakdown", {}, 1)],
        )
        results = self.fetcher.execute(plan, db_session)
        assert results[0].success is True

    def test_analytics_district_comparison(self, db_session):
        plan = QueryPlan(
            intents=[Intent.CRIME_STATISTICS],
            entities=ExtractedEntities(),
            backend_calls=[BackendCall("analytics", "district_comparison", {}, 1)],
        )
        results = self.fetcher.execute(plan, db_session)
        assert results[0].success is True

    def test_analytics_hotspots(self, db_session):
        plan = QueryPlan(
            intents=[Intent.HOTSPOT_ANALYSIS],
            entities=ExtractedEntities(),
            backend_calls=[BackendCall("analytics", "hotspots", {}, 1)],
        )
        results = self.fetcher.execute(plan, db_session)
        assert results[0].success is True

    def test_postgres_list_firs(self, db_session):
        plan = QueryPlan(
            intents=[Intent.FIR_LOOKUP],
            entities=ExtractedEntities(),
            backend_calls=[BackendCall("postgres", "list_firs", {"limit": 5}, 1)],
        )
        results = self.fetcher.execute(plan, db_session)
        assert results[0].success is True

    def test_postgres_list_cases(self, db_session):
        plan = QueryPlan(
            intents=[Intent.CASE_DETAILS],
            entities=ExtractedEntities(),
            backend_calls=[BackendCall("postgres", "list_cases", {"limit": 5}, 1)],
        )
        results = self.fetcher.execute(plan, db_session)
        assert results[0].success is True

    def test_postgres_list_officers(self, db_session):
        plan = QueryPlan(
            intents=[Intent.OFFICER_INFO],
            entities=ExtractedEntities(),
            backend_calls=[BackendCall("postgres", "list_officers", {"limit": 5}, 1)],
        )
        results = self.fetcher.execute(plan, db_session)
        assert results[0].success is True

    def test_unknown_service_returns_error(self, db_session):
        plan = QueryPlan(
            intents=[Intent.GENERAL],
            entities=ExtractedEntities(),
            backend_calls=[BackendCall("unknown_service", "unknown_method", {}, 1)],
        )
        results = self.fetcher.execute(plan, db_session)
        assert results[0].success is False

    def test_graceful_failure_on_bad_method(self, db_session):
        plan = QueryPlan(
            intents=[Intent.GENERAL],
            entities=ExtractedEntities(),
            backend_calls=[BackendCall("analytics", "nonexistent_method_xyz", {}, 1)],
        )
        results = self.fetcher.execute(plan, db_session)
        assert results[0].success is True  # returns "not found" message, doesn't crash


# ── Context Builder Tests ────────────────────────────────────────────

class TestContextBuilder:
    def setup_method(self):
        self.builder = ContextBuilder()

    def test_build_with_results(self):
        results = [
            BackendResult(source="postgres", data_type="fir", content="FIR 2026/104: Complainant Test", success=True),
            BackendResult(source="neo4j", data_type="network", content="Ramu -> Vikram (associate)", success=True),
        ]
        entities = ExtractedEntities(fir_number="2026/104")
        ctx = self.builder.build(results, entities, "Show FIR 2026/104")
        assert "FIR 2026/104" in ctx.context_block
        assert "Saksha PostgreSQL" in ctx.context_block
        assert "Saksha Neo4j" in ctx.context_block
        assert len(ctx.sources) == 2
        assert len(ctx.citations) == 2

    def test_build_empty_results(self):
        results = []
        entities = ExtractedEntities()
        ctx = self.builder.build(results, entities, "hello")
        assert "No relevant data" in ctx.context_block
        assert len(ctx.sources) == 0

    def test_build_failed_results(self):
        results = [
            BackendResult(source="ml", data_type="risk", content="", success=False, error="timeout"),
        ]
        entities = ExtractedEntities()
        ctx = self.builder.build(results, entities, "predict")
        assert "No relevant data" in ctx.context_block

    def test_system_prompt_present(self):
        ctx = self.builder.build([], ExtractedEntities(), "test")
        assert "SAKSHA AI" in ctx.system_prompt
        assert "NEVER fabricate" in ctx.system_prompt

    def test_summary_includes_entities(self):
        results = [
            BackendResult(source="postgres", data_type="fir", content="test", success=True),
        ]
        entities = ExtractedEntities(fir_number="2026/104", district="Bengaluru Urban")
        ctx = self.builder.build(results, entities, "query")
        assert "FIR #2026/104" in ctx.summary
        assert "Bengaluru Urban" in ctx.summary


# ── Response Validator Tests ─────────────────────────────────────────

class TestResponseValidator:
    def setup_method(self):
        self.validator = ResponseValidator()

    def test_validate_passes_clean_response(self):
        response = "The FIR status is open."
        results = [BackendResult(source="postgres", data_type="fir", content="status: open", raw_data={"fir_number": "2026/104"})]
        validated = self.validator.validate(response, results)
        assert "Note:" not in validated

    def test_validate_flags_unverified_id(self):
        response = "Case CR-2026-BLR-999 has been filed."
        results = [BackendResult(source="postgres", data_type="fir", content="data", raw_data={"fir_number": "2026/104"})]
        validated = self.validator.validate(response, results)
        assert "Note:" in validated or "could not be verified" in validated

    def test_validate_passes_with_no_results(self):
        response = "Hello there"
        validated = self.validator.validate(response, [])
        assert validated == response

    def test_validate_preserves_clean_response(self):
        response = "Based on the database, total crimes: 11."
        results = [BackendResult(source="analytics", data_type="summary", content="total crimes: 11", raw_data={"total_crimes": 11})]
        validated = self.validator.validate(response, results)
        assert "total crimes: 11" in validated


# ── Chat Memory Tests ────────────────────────────────────────────────

class TestChatMemory:
    def setup_method(self):
        self.mem = ChatMemory(max_sessions=5, max_messages=10, ttl_seconds=3600)

    def test_add_and_get(self):
        self.mem.add("s1", "hello", "hi there")
        history = self.mem.get_history("s1")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_get_empty_session(self):
        history = self.mem.get_history("nonexistent")
        assert history == []

    def test_max_messages_limit(self):
        for i in range(20):
            self.mem.add("s1", f"q{i}", f"a{i}")
        history = self.mem.get_history("s1")
        assert len(history) <= 20

    def test_clear_session(self):
        self.mem.add("s1", "hello", "hi")
        self.mem.clear("s1")
        assert self.mem.get_history("s1") == []

    def test_max_sessions_eviction(self):
        for i in range(10):
            self.mem.add(f"session-{i}", "q", "a")
        # Should have evicted oldest
        assert len(self.mem._sessions) <= 5

    def test_multiple_sessions_independent(self):
        self.mem.add("s1", "q1", "a1")
        self.mem.add("s2", "q2", "a2")
        h1 = self.mem.get_history("s1")
        h2 = self.mem.get_history("s2")
        assert h1[0]["content"] == "q1"
        assert h2[0]["content"] == "q2"


# ── Orchestrator Integration Test ────────────────────────────────────

class TestChatOrchestrator:
    def setup_method(self):
        self.orchestrator = ChatOrchestrator()

    def test_intent_detection_pipeline(self):
        result = self.orchestrator.intent_router.detect("Show FIR 2026/104")
        assert Intent.FIR_LOOKUP in result.intents

    def test_entity_extraction_pipeline(self):
        result = self.orchestrator.entity_extractor.extract("Show FIR 2026/104")
        assert result.fir_number == "2026/104"

    def test_full_sync_pipeline(self, db_session):
        result = self.orchestrator.process_message_sync(
            "What are the crime statistics?",
            session_id="test-session",
            db=db_session,
        )
        assert "answer" in result
        assert "summary" in result
        assert "entities" in result
        assert "classification" in result
        assert "sources" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0

    def test_sync_pipeline_fir_query(self, db_session):
        result = self.orchestrator.process_message_sync(
            "Show me all FIRs",
            session_id="test-fir",
            db=db_session,
        )
        assert "answer" in result
        assert isinstance(result["citations"], list)

    def test_sync_pipeline_criminal_query(self, db_session):
        result = self.orchestrator.process_message_sync(
            "Tell me about Ramu Swamy criminal record",
            session_id="test-criminal",
            db=db_session,
        )
        assert "answer" in result
        assert result["classification"] in ("criminal_history", "criminal_network")

    def test_sync_pipeline_general(self, db_session):
        result = self.orchestrator.process_message_sync(
            "hello",
            session_id="test-general",
            db=db_session,
        )
        assert "answer" in result

    def test_memory_integration(self, db_session):
        self.orchestrator.process_message_sync("Show FIR 2026/104", "mem-test", db_session)
        history = memory.get_history("mem-test")
        assert len(history) >= 2
        memory.clear("mem-test")

    def test_chart_suggestion(self, db_session):
        result = self.orchestrator.process_message_sync(
            "What are the crime statistics?",
            session_id="chart-test",
            db=db_session,
        )
        assert result.get("chart_suggestion") == "bar"

    def test_context_builder_integration(self):
        results = [
            BackendResult(source="analytics", data_type="summary", content="Total crimes: 11", success=True),
        ]
        entities = ExtractedEntities()
        ctx = self.orchestrator.context_builder.build(results, entities, "stats")
        assert "11" in ctx.context_block
