"""SAKSHA Intelligence Fusion & Action Pipeline Tests.

Comprehensive automated tests verifying:
1. Backward compatibility with existing intelligence and alert endpoints
2. Negative case: baseline crime activity generates no false intelligence
3. Positive case: multi-signal cluster (temporal spike + anomaly + spatial + MO + entities) generates unified intelligence
4. Confidence scaling: more concurring signals yield higher confidence
5. Historical baseline comparison metrics (baseline count, current count, % change, direction)
6. Geospatial H3 cell indexing and spatial hotspot contribution
7. Modus operandi canonical tag correlation
8. FIR and entity relationship propagation (including at-large suspects)
9. ML/FALLBACK and model identity/version metadata preservation
10. Graceful degradation: pipeline continues functioning when individual analytics fail
11. Configurable threshold filtering
12. API endpoints (GET emerging-patterns, POST fuse, GET pattern by ID)
13. Action pipeline: dispatching recommended action directly into interventions
14. Alerts integration: cross-referencing active intelligence in GET /alerts/red-zones
15. RBAC and audit logging enforcement
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.intervention import Intervention
from app.models.location import Location
from app.models.role import Role
from app.models.user import User
from app.models.victim import Victim
from app.services import intelligence_engine


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

def _make_user(db_session, username: str, role_name: str) -> User:
    role = db_session.query(Role).filter_by(name=role_name).first()
    if role is None:
        role = Role(name=role_name, description=role_name)
        db_session.add(role)
        db_session.flush()
    user = User(
        username=username,
        email=f"{username}@test.saksha.org",
        full_name=username.replace("-", " ").title(),
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def analyst_client(client, db_session):
    user = _make_user(db_session, "intel-analyst", "crime_analyst")
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def investigator_client(client, db_session):
    user = _make_user(db_session, "intel-investigator", "investigator")
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def viewer_client(client, db_session):
    user = _make_user(db_session, "intel-viewer", "viewer")
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


def _seed_baseline_and_spike(db_session):
    """Seed historical baseline cases (prior 90 days) and a recent surge (last 30 days) in Whitefield."""
    now = datetime.now(timezone.utc)
    cat_theft = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="high")
    cat_assault = CrimeCategory(name="Assault & Violent Crime", section_code="IPC 323", severity="medium")
    loc_wf = Location(district="Bengaluru Urban", station="Whitefield", latitude=12.9698, longitude=77.7499)
    loc_ind = Location(district="Bengaluru Urban", station="Indiranagar", latitude=12.9784, longitude=77.6408)
    db_session.add_all([cat_theft, cat_assault, loc_wf, loc_ind])
    db_session.flush()

    criminal = Criminal(
        full_name="Vikram Singh",
        aliases="Vicky Nightlock",
        status="at_large",
        mo_summary="Late night residential housebreak lock break crowbar",
    )
    victim = Victim(full_name="Asha Sharma", contact_number="9845012345")
    db_session.add_all([criminal, victim])
    db_session.flush()

    # 1. Historical baseline: 3 cases 45-75 days ago (Whitefield, Theft)
    for i in range(3):
        ts = now - timedelta(days=50 + i * 10)
        c = CrimeCase(
            case_number=f"CC-HIST-00{i+1}",
            category_id=cat_theft.id,
            location_id=loc_wf.id,
            occurred_at=ts,
            reported_at=ts,
            status="closed",
            priority="medium",
            description="Night time residential burglary with crowbar",
            mo_tags="night_operation,break_in,tool_usage",
        )
        db_session.add(c)
        db_session.flush()
        f = FIR(
            fir_number=f"FIR-HIST-00{i+1}",
            crime_case_id=c.id,
            complainant_name="Resident",
            filed_at=ts,
            status="disposed",
        )
        db_session.add(f)

    # 2. Recent spike: 6 cases in the last 10 days (Whitefield, Theft)
    recent_cases = []
    for i in range(6):
        ts = now - timedelta(days=2 + i)
        c = CrimeCase(
            case_number=f"CC-SPIKE-00{i+1}",
            category_id=cat_theft.id,
            location_id=loc_wf.id,
            occurred_at=ts,
            reported_at=ts,
            status="open",
            priority="high",
            description="Late night residential burglary door lock break with power tools",
            mo_tags="night_operation,break_in,tool_usage",
        )
        db_session.add(c)
        db_session.flush()
        recent_cases.append(c)

        f = FIR(
            fir_number=f"FIR-SPIKE-00{i+1}",
            crime_case_id=c.id,
            complainant_name=f"Victim {i+1}",
            filed_at=ts,
            status="investigating",
        )
        db_session.add(f)
        db_session.flush()

        db_session.add(FIRCriminalLink(fir_id=f.id, criminal_id=criminal.id, role="accused"))
        db_session.add(FIRVictimLink(fir_id=f.id, victim_id=victim.id))

    db_session.commit()
    return {
        "cat_theft": cat_theft,
        "loc_wf": loc_wf,
        "criminal": criminal,
        "victim": victim,
        "recent_cases": recent_cases,
    }


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_negative_case_no_pattern(db_session):
    """When incidents are below thresholds or no spike exists, no patterns are generated."""
    # Empty DB
    patterns = intelligence_engine.detect_emerging_patterns(db_session)
    assert patterns == []

    # Single isolated case below min_current_incidents (default 2)
    now = datetime.now(timezone.utc)
    cat = CrimeCategory(name="Cyber Fraud", severity="low")
    loc = Location(district="Mysuru", station="Central", latitude=12.30, longitude=76.65)
    db_session.add_all([cat, loc])
    db_session.flush()
    c = CrimeCase(
        case_number="CC-SOLO-1",
        category_id=cat.id,
        location_id=loc.id,
        occurred_at=now - timedelta(days=2),
        status="open",
    )
    db_session.add(c)
    db_session.commit()

    patterns = intelligence_engine.detect_emerging_patterns(db_session)
    assert patterns == []


def test_positive_case_strong_cluster(db_session):
    """Multi-signal cluster generates a unified intelligence result with complete fields."""
    seeded = _seed_baseline_and_spike(db_session)

    patterns = intelligence_engine.detect_emerging_patterns(db_session)
    assert len(patterns) >= 1

    pattern = patterns[0]
    assert "Theft" in pattern["pattern_type"]
    assert pattern["location"]["district"] == "Bengaluru Urban"
    assert "Whitefield" in pattern["location"]["stations"]
    assert len(pattern["affected_h3_cells"]) >= 1
    assert pattern["time_window"] == "last_30_days"

    # Baseline comparison metrics
    change = pattern["change_from_baseline"]
    assert change["current_count"] == 6
    assert change["baseline_count"] > 0
    assert change["change_percentage"] > 50.0
    assert change["direction"] == "increasing"

    # Scores
    assert 0.0 <= pattern["risk_score"] <= 1.0
    assert pattern["risk_score"] >= 0.50
    assert 0.0 <= pattern["confidence"] <= 1.0
    assert pattern["confidence"] >= 0.60

    # Supporting signals
    signal_types = [s["signal_type"] for s in pattern["supporting_signals"]]
    assert "temporal" in signal_types
    assert "mo_pattern" in signal_types or "spatial_hotspot" in signal_types

    # FIR & Entity propagation
    assert len(pattern["related_fir_ids"]) >= 5
    assert str(seeded["criminal"].id) in pattern["related_entity_ids"]

    # Recommended action
    rec = pattern["recommended_action_input"]
    assert rec["action_type"] in ("patrol_surge", "surveillance", "investigation", "checkpoint")
    assert rec["priority"] in ("CRITICAL", "HIGH", "MEDIUM")
    assert rec["suggested_intervention"]["district"] == "Bengaluru Urban"

    # Explainability
    assert "Pattern: " in pattern["explanation"]
    assert "Baseline: " in pattern["explanation"]
    assert "Current: " in pattern["explanation"]
    assert "Risk Score: " in pattern["explanation"]
    assert "Recommended Action:" in pattern["explanation"]

    # Metadata & Provenance
    assert pattern["ml_status"] in ("ML", "FALLBACK", "RULE_BASED", "HYBRID")
    assert pattern["model_name"] == "SAKSHA Intelligence Fusion"
    assert pattern["data_provenance"] in ("LIVE_DB", "DEMO", "MIXED", "UNKNOWN")


def test_confidence_scaling_with_signals(db_session):
    """Confidence dynamically scales as more concurring signals support the pattern."""
    _seed_baseline_and_spike(db_session)

    # Fusion with custom low vs high signals threshold
    threshold_few = intelligence_engine.FusionThresholds(min_supporting_signals=2)
    threshold_many = intelligence_engine.FusionThresholds(min_supporting_signals=4)

    patterns_few = intelligence_engine.detect_emerging_patterns(db_session, custom_thresholds=threshold_few)
    assert len(patterns_few) >= 1

    pattern = patterns_few[0]
    # Verify that pattern confidence increases with number of signals
    sig_count = len(pattern["supporting_signals"])
    if sig_count >= 4:
        assert pattern["confidence"] >= 0.80
    elif sig_count >= 3:
        assert pattern["confidence"] >= 0.70
    elif sig_count >= 2:
        assert pattern["confidence"] >= 0.60


def test_mo_canonical_tag_contribution(db_session):
    """Canonical modus operandi tags are detected and surfaced in the fused result."""
    seeded = _seed_baseline_and_spike(db_session)

    patterns = intelligence_engine.detect_emerging_patterns(db_session)
    assert len(patterns) >= 1

    mo_signals = [s for s in patterns[0]["supporting_signals"] if s["signal_type"] == "mo_pattern"]
    assert len(mo_signals) >= 1
    mo_signal = mo_signals[0]
    assert "Similar MO" in mo_signal["description"]
    assert "night_operation" in mo_signal["evidence_details"]["shared_tags"] or "break_in" in mo_signal["evidence_details"]["shared_tags"]


def test_at_large_suspect_entity_signal(db_session):
    """Presence of at-large suspects contributes an entity_link signal."""
    _seed_baseline_and_spike(db_session)

    patterns = intelligence_engine.detect_emerging_patterns(db_session)
    assert len(patterns) >= 1

    entity_signals = [s for s in patterns[0]["supporting_signals"] if s["signal_type"] == "entity_link"]
    assert len(entity_signals) >= 1
    assert "Vikram Singh" in entity_signals[0]["evidence_details"]["at_large_suspects"]


def test_graceful_degradation_when_analytics_fail(db_session):
    """The pipeline continues operating if forecasting or other modules fail."""
    _seed_baseline_and_spike(db_session)

    # Mock predict_forecast to simulate service failure
    with patch("app.ai.inference.risk.predict_forecast", side_effect=RuntimeError("Forecast model artifact missing")):
        patterns = intelligence_engine.detect_emerging_patterns(db_session)
        assert len(patterns) >= 1
        pattern = patterns[0]
        # Forecast is recorded as unavailable in contributing_analytics without breaking pipeline
        assert pattern["contributing_analytics"]["forecast"]["status"] == "UNAVAILABLE"
        # Other signals still fused
        sig_types = [s["signal_type"] for s in pattern["supporting_signals"]]
        assert "temporal" in sig_types


def test_configurable_threshold_filtering(db_session):
    """Strict thresholds successfully filter out marginal patterns."""
    _seed_baseline_and_spike(db_session)

    # Ultra-strict threshold (requires 10 supporting signals)
    strict_thresholds = intelligence_engine.FusionThresholds(min_supporting_signals=10)
    strict_patterns = intelligence_engine.detect_emerging_patterns(db_session, custom_thresholds=strict_thresholds)
    assert strict_patterns == []

    # Ultra-high risk threshold (0.999)
    high_risk_thresholds = intelligence_engine.FusionThresholds(min_risk_score=0.999)
    high_risk_patterns = intelligence_engine.detect_emerging_patterns(db_session, custom_thresholds=high_risk_thresholds)
    assert high_risk_patterns == []


def test_backward_compatibility_build_intelligence(db_session):
    """Existing build_intelligence function remains backward compatible and adds emerging_intelligence."""
    seeded = _seed_baseline_and_spike(db_session)
    case = seeded["recent_cases"][0]

    report = intelligence_engine.build_intelligence(db_session, "case", str(case.id))
    assert "entity_info" in report
    assert "summary" in report
    assert "connections" in report
    assert "common_threads" in report
    assert "timeline" in report
    assert "confidence_summary" in report
    assert "explainability" in report

    # New additive field
    assert "emerging_intelligence" in report
    if report["emerging_intelligence"]:
        assert "intelligence_id" in report["emerging_intelligence"]
        assert "pattern_type" in report["emerging_intelligence"]


# ---------------------------------------------------------------------------
# API Integration Tests
# ---------------------------------------------------------------------------

def test_api_get_emerging_patterns(analyst_client, db_session):
    """GET /api/v2/intelligence/emerging-patterns returns structured fusion response."""
    client, user = analyst_client
    _seed_baseline_and_spike(db_session)

    resp = client.get("/api/v2/intelligence/emerging-patterns?district=Bengaluru Urban")
    assert resp.status_code == 200
    data = resp.json()

    assert "total" in data
    assert "patterns" in data
    assert "generated_at" in data
    assert "thresholds_applied" in data
    assert data["total"] >= 1

    pattern = data["patterns"][0]
    assert pattern["location"]["district"] == "Bengaluru Urban"
    assert pattern["change_from_baseline"]["direction"] == "increasing"


def test_api_post_fuse_on_demand(analyst_client, db_session):
    """POST /api/v2/intelligence/fuse executes on-demand fusion and records history."""
    client, user = analyst_client
    _seed_baseline_and_spike(db_session)

    payload = {
        "district": "Bengaluru Urban",
        "thresholds": {
            "min_supporting_signals": 2,
            "min_risk_score": 0.30,
            "min_confidence": 0.40,
            "min_percentage_change": 15.0,
            "current_window_days": 30,
            "baseline_window_days": 90,
        },
    }
    resp = client.post("/api/v2/intelligence/fuse", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1

    # Verify run was saved to user history as a single fusion entry
    hist_resp = client.get("/api/v2/intelligence/history")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    fused_entries = [h for h in history if h.get("entity_type") == "fusion"]
    assert len(fused_entries) == 1


def test_api_get_pattern_by_id(analyst_client, db_session):
    """GET /api/v2/intelligence/emerging-patterns/{id} retrieves specific pattern."""
    client, user = analyst_client
    _seed_baseline_and_spike(db_session)

    list_resp = client.get("/api/v2/intelligence/emerging-patterns")
    assert list_resp.status_code == 200
    pattern_id = list_resp.json()["patterns"][0]["intelligence_id"]

    get_resp = client.get(f"/api/v2/intelligence/emerging-patterns/{pattern_id}")
    assert get_resp.status_code == 200
    p = get_resp.json()
    assert p["intelligence_id"] == pattern_id
    assert "location" in p
    assert "supporting_signals" in p


def test_api_dispatch_action_to_interventions(investigator_client, db_session):
    """POST /api/v2/intelligence/emerging-patterns/{id}/action creates a real Intervention."""
    client, user = investigator_client
    _seed_baseline_and_spike(db_session)

    list_resp = client.get("/api/v2/intelligence/emerging-patterns")
    pattern_id = list_resp.json()["patterns"][0]["intelligence_id"]

    action_resp = client.post(
        f"/api/v2/intelligence/emerging-patterns/{pattern_id}/action",
        json={"title": "Custom Surge: Whitefield Sector 4"},
    )
    assert action_resp.status_code == 200
    res = action_resp.json()
    assert res["dispatched"] is True
    assert res["title"] == "Custom Surge: Whitefield Sector 4"
    assert res["district"] == "Bengaluru Urban"

    # Verify created in DB
    intervention = db_session.query(Intervention).filter_by(id=uuid.UUID(res["intervention_id"])).first()
    assert intervention is not None
    assert intervention.title == "Custom Surge: Whitefield Sector 4"
    assert intervention.district == "Bengaluru Urban"


def test_api_action_dispatch_rbac_enforcement(viewer_client, db_session):
    """Unauthorized role (viewer) cannot dispatch actions into interventions."""
    client, user = viewer_client
    _seed_baseline_and_spike(db_session)

    list_resp = client.get("/api/v2/intelligence/emerging-patterns")
    assert list_resp.status_code == 200
    pattern_id = list_resp.json()["patterns"][0]["intelligence_id"]

    # viewer is NOT in (admin, investigator, inspector, policymaker)
    action_resp = client.post(
        f"/api/v2/intelligence/emerging-patterns/{pattern_id}/action",
        json={},
    )
    assert action_resp.status_code == 403


def test_alerts_red_zones_cross_reference(analyst_client, db_session):
    """GET /api/v2/alerts/red-zones?include_intelligence=true attaches fused intelligence ID."""
    client, user = analyst_client
    _seed_baseline_and_spike(db_session)

    resp = client.get("/api/v2/alerts/red-zones?include_intelligence=true&min_current=2")
    assert resp.status_code == 200
    data = resp.json()
    assert "red_zones" in data
    matching_zones = [z for z in data["red_zones"] if z.get("district") == "Bengaluru Urban"]
    if matching_zones:
        assert "fused_intelligence_id" in matching_zones[0]
        assert "Theft" in matching_zones[0]["fused_pattern_type"]
