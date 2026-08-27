"""Issue #189: Predictive Intelligence, Network Investigation & AI Intelligence Validation.

Tests cover:
1. Predictive Intelligence — prediction_mode tagging on criminal inference
2. Network Search — real backend search, no matches, multiple matches
3. Network Focus — entity selection, depth expansion, sparse graph handling
4. AI Intelligence Validation — grounding, empty retrieval, provider failure
5. Challenge Capability Classification — honest status reporting
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("APP_DEBUG", "false")

from datetime import datetime, timezone

import pytest

from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.location import Location
from app.models.officer import Officer
from app.models.role import Role
from app.models.user import User
from app.models.victim import Victim
from app.services.network import network_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NET = "/api/v2/network"


@pytest.fixture
def analyst_client(client, db_session):
    role = db_session.query(Role).filter_by(name="crime_analyst").first()
    if role is None:
        role = Role(name="crime_analyst", description="Crime Analyst")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="i189-analyst",
        email="i189-analyst@test.invalid",
        full_name="Issue 189 Analyst",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    client.app.dependency_overrides[app_auth] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(app_auth, None)


@pytest.fixture
def network_data(db_session):
    """Seed minimal real network data: 1 criminal, 1 victim, 1 officer, 1 case, 1 FIR."""
    cat = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="high")
    loc = Location(district="Bengaluru Urban", station="Whitefield", latitude=12.97, longitude=77.75)
    db_session.add_all([cat, loc])
    db_session.flush()

    criminal = Criminal(
        full_name="Test Network Criminal",
        status="at_large",
        gang_affiliation="Test Syndicate",
        mo_summary="Breaks into homes using force.",
    )
    victim = Victim(
        full_name="Test Network Victim",
        contact_number="9876543210",
        gender="female",
        age=35,
        statement="I was robbed at my residence.",
    )
    officer = Officer(
        name="Test Inspector Kumar",
        badge_number="IO-1891",
        rank="Inspector",
        district="Bengaluru Urban",
        station="Whitefield",
    )
    db_session.add_all([criminal, victim, officer])
    db_session.flush()

    case = CrimeCase(
        case_number="CR-2026-I189-001",
        category_id=cat.id,
        location_id=loc.id,
        occurred_at=datetime(2026, 6, 1, 22, 0, tzinfo=timezone.utc),
        reported_at=datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc),
        description="Residential burglary in Whitefield area.",
        status="open",
        priority="high",
    )
    db_session.add(case)
    db_session.flush()

    fir = FIR(
        fir_number="FIR-189/2026",
        crime_case_id=case.id,
        investigating_officer_id=officer.id,
        complainant_name="Test Network Victim",
        sections="IPC 379, IPC 380",
        narrative="Complainant reports break-in at residence.",
        status="registered",
        filed_at=datetime(2026, 6, 2, 8, 30, tzinfo=timezone.utc),
    )
    db_session.add(fir)
    db_session.flush()

    crim_link = FIRCriminalLink(fir_id=fir.id, criminal_id=criminal.id)
    vic_link = FIRVictimLink(fir_id=fir.id, victim_id=victim.id)
    db_session.add_all([crim_link, vic_link])
    db_session.commit()

    return {
        "criminal": criminal,
        "victim": victim,
        "officer": officer,
        "case": case,
        "fir": fir,
        "location": loc,
    }


# We need to import get_current_user at the module level for dependency override
from app.auth.dependencies import get_current_user as app_auth


# ===========================================================================
# 1. PREDICTIVE INTELLIGENCE — prediction_mode tagging
# ===========================================================================

class TestCriminalPredictionMode:
    """Verify criminal inference always returns honest prediction_mode tags."""

    def test_risk_score_returns_prediction_mode(self, db_session, network_data):
        from app.ai.inference.criminal import score_criminal_risk

        result = score_criminal_risk(db_session, str(network_data["criminal"].id))
        assert "prediction_mode" in result
        assert result["prediction_mode"] in ("RULE_BASED", "ML", "FALLBACK")

    def test_repeat_offender_returns_prediction_mode(self, db_session, network_data):
        from app.ai.inference.criminal import predict_repeat_offender

        result = predict_repeat_offender(db_session, str(network_data["criminal"].id))
        assert "prediction_mode" in result
        assert result["prediction_mode"] in ("RULE_BASED", "ML", "FALLBACK")

    def test_cluster_returns_prediction_mode(self, db_session, network_data):
        from app.ai.inference.criminal import cluster_criminal

        result = cluster_criminal(db_session, str(network_data["criminal"].id))
        assert "prediction_mode" in result
        assert result["prediction_mode"] in ("RULE_BASED", "ML", "FALLBACK")

    def test_similar_offenders_returns_prediction_mode(self, db_session, network_data):
        from app.ai.inference.criminal import find_similar_offenders

        result = find_similar_offenders(db_session, str(network_data["criminal"].id), top_k=3)
        assert "prediction_mode" in result
        assert result["prediction_mode"] in ("RULE_BASED", "ML", "FALLBACK")

    def test_recommendations_returns_prediction_mode_and_model_modes(self, db_session, network_data):
        from app.ai.inference.criminal import get_investigation_recommendations

        result = get_investigation_recommendations(db_session, str(network_data["criminal"].id))
        assert "prediction_mode" in result
        assert result["prediction_mode"] in ("RULE_BASED", "ML", "FALLBACK")
        assert "model_modes" in result
        assert isinstance(result["model_modes"], list)
        assert len(result["model_modes"]) > 0

    def test_invalid_criminal_returns_error(self, db_session):
        from app.ai.inference.criminal import score_criminal_risk

        result = score_criminal_risk(db_session, "00000000-0000-0000-0000-000000000000")
        assert "error" in result

    def test_non_uuid_criminal_returns_error(self, db_session):
        from app.ai.inference.criminal import score_criminal_risk

        result = score_criminal_risk(db_session, "not-a-uuid")
        assert "error" in result


# ===========================================================================
# 2. NETWORK SEARCH — real backend search
# ===========================================================================

class TestNetworkSearch:
    """Verify network search uses real database records."""

    def test_search_by_criminal_name(self, client, analyst_client, network_data):
        c, _ = analyst_client
        resp = c.get(f"{NET}/search?q=Test+Network+Criminal")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        names = [r["name"] for r in data["results"]]
        assert "Test Network Criminal" in names

    def test_search_by_victim_name(self, client, analyst_client, network_data):
        c, _ = analyst_client
        resp = c.get(f"{NET}/search?q=Test+Network+Victim")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(r["type"] == "victim" for r in data["results"])

    def test_search_by_fir_number(self, client, analyst_client, network_data):
        c, _ = analyst_client
        resp = c.get(f"{NET}/search?q=FIR-189")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any("FIR-189" in r["name"] for r in data["results"])

    def test_search_by_case_number(self, client, analyst_client, network_data):
        c, _ = analyst_client
        resp = c.get(f"{NET}/search?q=CR-2026-I189")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_search_by_district(self, client, analyst_client, network_data):
        c, _ = analyst_client
        resp = c.get(f"{NET}/search?q=Bengaluru+Urban")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_search_by_station(self, client, analyst_client, network_data):
        c, _ = analyst_client
        resp = c.get(f"{NET}/search?q=Whitefield")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_search_no_matches(self, client, analyst_client, network_data):
        c, _ = analyst_client
        resp = c.get(f"{NET}/search?q=NONEXISTENT_ENTITY_XYZ_999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_search_by_officer_name(self, client, analyst_client, network_data):
        c, _ = analyst_client
        resp = c.get(f"{NET}/search?q=Test+Inspector+Kumar")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(r["type"] == "officer" for r in data["results"])


# ===========================================================================
# 3. NETWORK FOCUS — entity selection and depth expansion
# ===========================================================================

class TestNetworkFocus:
    """Verify focused graph retrieval and progressive expansion."""

    def test_person_graph_returns_focused_nodes(self, client, analyst_client, network_data):
        c, _ = analyst_client
        crim_id = f"criminal-{network_data['criminal'].id}"
        resp = c.get(f"{NET}/person/{crim_id}?depth=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_nodes"] >= 1
        node_ids = [n["id"] for n in data["nodes"]]
        assert crim_id in node_ids

    def test_depth_expansion_increases_nodes(self, client, analyst_client, network_data):
        c, _ = analyst_client
        crim_id = f"criminal-{network_data['criminal'].id}"
        resp1 = c.get(f"{NET}/person/{crim_id}?depth=1")
        resp2 = c.get(f"{NET}/person/{crim_id}?depth=2")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        # Depth 2 should have >= depth 1 nodes
        assert resp2.json()["total_nodes"] >= resp1.json()["total_nodes"]

    def test_unknown_person_returns_empty(self, client, analyst_client, network_data):
        c, _ = analyst_client
        resp = c.get(f"{NET}/person/criminal-00000000-0000-0000-0000-000000000000?depth=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_nodes"] == 0

    def test_exclude_demo_flag(self, client, analyst_client, network_data):
        c, _ = analyst_client
        resp = c.get(f"{NET}/graph?exclude_demo=true")
        assert resp.status_code == 200
        data = resp.json()
        # Seed nodes should be excluded
        seed_nodes = [n for n in data["nodes"] if n.get("isSeed")]
        assert len(seed_nodes) == 0

    def test_graph_provenance_summary_present(self, client, analyst_client, network_data):
        c, _ = analyst_client
        resp = c.get(f"{NET}/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "provenance_summary" in data
        summary = data["provenance_summary"]
        assert "total_nodes" in summary
        assert "verified_relationships" in summary

    def test_graph_entity_counts_present(self, client, analyst_client, network_data):
        c, _ = analyst_client
        resp = c.get(f"{NET}/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "entity_counts" in data
        assert isinstance(data["entity_counts"], dict)


# ===========================================================================
# 4. AI INTELLIGENCE VALIDATION — grounding and safety
# ===========================================================================

class TestAIGrounding:
    """Verify AI response grounding and refusal behavior."""

    def test_empty_retrieval_produces_refusal(self):
        from app.ai.chat.response_validator import ResponseValidator

        validator = ResponseValidator()
        response = "Case CR-2026-XX-999 is linked to gang activity."
        validated = validator.validate(response, [])
        assert "could not find matching records" in validated.lower() or "no verified data" in validated.lower()

    def test_all_failed_sources_produce_refusal(self):
        from app.ai.chat.backend_fetcher import BackendResult
        from app.ai.chat.response_validator import ResponseValidator

        validator = ResponseValidator()
        failed = [BackendResult(source="postgres", data_type="firs", content="", success=False)]
        validated = validator.validate("Here is the answer.", failed)
        assert "could not find matching records" in validated.lower()

    def test_verified_ids_pass_clean(self):
        from app.ai.chat.backend_fetcher import BackendResult
        from app.ai.chat.response_validator import ResponseValidator

        validator = ResponseValidator()
        good = [BackendResult(
            source="postgres", data_type="cases",
            content="Case: CR-2026-BLR-001 | Status: open",
            raw_data={"case_number": "CR-2026-BLR-001"},
        )]
        response = "Case CR-2026-BLR-001 is open."
        assert validator.validate(response, good) == response

    def test_unverified_ids_get_disclaimer(self):
        from app.ai.chat.backend_fetcher import BackendResult
        from app.ai.chat.response_validator import ResponseValidator

        validator = ResponseValidator()
        good = [BackendResult(
            source="postgres", data_type="cases",
            content="Case: CR-2026-BLR-001 | Status: open",
            raw_data={"case_number": "CR-2026-BLR-001"},
        )]
        response = "Records CR-2026-BLR-001 and CR-2026-ZZZ-999 are related."
        validated = validator.validate(response, good)
        assert "could not be verified" in validated

    def test_provenance_refusal_on_empty(self):
        from app.ai.chat.response_validator import ResponseValidator

        validator = ResponseValidator()
        provenance = validator.get_provenance("Some answer", [])
        assert provenance.refusal_issued is True
        assert provenance.has_fabricated_claims is True

    def test_provenance_grounding_score_computed(self):
        from app.ai.chat.backend_fetcher import BackendResult
        from app.ai.chat.response_validator import ResponseValidator

        validator = ResponseValidator()
        good = [BackendResult(
            source="postgres", data_type="cases",
            content="Case: CR-2026-BLR-001",
            raw_data={"case_number": "CR-2026-BLR-001"},
        )]
        provenance = validator.get_provenance("Case CR-2026-BLR-001 is open.", good)
        assert provenance.grounding_score >= 0.0
        assert provenance.refusal_issued is False


class TestAIChatOrchestratorSafety:
    """Verify orchestrator handles edge cases safely."""

    def test_sync_handles_provider_failure(self, db_session, network_data):
        from app.ai.chat.orchestrator import ChatOrchestrator

        orch = ChatOrchestrator()
        # Override LLM generator to raise
        orch.llm_generator._chain = []

        result = orch.process_message_sync(
            message="What crimes occurred in Bengaluru?",
            session_id="test-safety",
            db=db_session,
            history=None,
            current_user=None,
        )
        # Should not raise — should return a bounded response
        assert "answer" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0
        assert "provenance" in result

    def test_sync_empty_db_returns_refusal(self, db_session):
        from app.ai.chat.orchestrator import ChatOrchestrator

        orch = ChatOrchestrator()
        result = orch.process_message_sync(
            message="Tell me about criminals in Mysuru",
            session_id="test-empty",
            db=db_session,
            history=None,
            current_user=None,
        )
        assert "answer" in result
        # Should be a refusal since no data exists
        answer_lower = result["answer"].lower()
        assert "could not find" in answer_lower or "no" in answer_lower or "unavailable" in answer_lower

    def test_platform_question_bypasses_db(self, db_session):
        from app.ai.chat.orchestrator import ChatOrchestrator

        orch = ChatOrchestrator()
        result = orch.process_message_sync(
            message="What is Saksha?",
            session_id="test-platform",
            db=db_session,
            history=None,
            current_user=None,
        )
        assert "answer" in result
        assert isinstance(result["answer"], str)


# ===========================================================================
# 5. CHALLENGE CAPABILITY — honest classification
# ===========================================================================

class TestChallengeCapabilityClassification:
    """Verify capability classifications are honest."""

    def test_criminal_risk_honestly_rule_based(self, db_session, network_data):
        from app.ai.inference.criminal import score_criminal_risk

        result = score_criminal_risk(db_session, str(network_data["criminal"].id))
        # Criminal risk is custom numpy — honestly RULE_BASED
        assert result["prediction_mode"] == "RULE_BASED"

    def test_anomaly_detection_honestly_tagged(self):
        from app.ai.inference.anomaly import run_anomaly_inference

        alerts = run_anomaly_inference([{
            "case_id": "test-1",
            "occurred_at": "2026-06-01T22:00:00Z",
            "lat": 12.97,
            "lon": 77.75,
            "district": "Bengaluru Urban",
            "crime_type": "Theft",
            "officer_id": "off-1",
            "offender_id": "off-1",
        }])
        assert len(alerts) >= 1
        for alert in alerts:
            assert "prediction_mode" in alert
            assert alert["prediction_mode"] in ("ML", "RULE_BASED")

    def test_hotspot_inference_returns_honest_status(self):
        from app.ai.inference.hotspot import get_model_info

        info = get_model_info()
        assert "model_loaded" in info
        assert "prediction_mode" in info
        assert info["prediction_mode"] in ("ML", "FALLBACK", "UNAVAILABLE")

    def test_risk_inference_returns_honest_status(self):
        from app.ai.inference.risk import get_model_info

        info = get_model_info()
        assert "risk_model_loaded" in info
        assert "prediction_mode" in info
        assert info["prediction_mode"] in ("ML", "FALLBACK", "UNAVAILABLE")
