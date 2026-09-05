"""SAKSHA Pattern-to-Network Investigation & Evidence Intelligence Tests (#250).

Verifies the provenance-aware investigation layer that consumes the #249
``UnifiedIntelligenceResult`` contract:

1. FIR references (``related_fir_ids`` = FIR numbers) resolve case + evidence set
2. Verification-state vocabulary is derived from real data:
   - live + DB-backed          -> VERIFIED
   - analytical inference       -> POTENTIAL   (MO/pattern edges)
   - demo-seed (non-sensitive)  -> DEMO
   - demo-seed + sensitive      -> RESTRICTED
3. RESTRICTED evidence is masked for non-reviewer roles, open for reviewers
4. MO/pattern matches reuse the structured MO-profile similarity engine
5. Network subgraph uses solid/dashed/dotted/lock vocabulary
6. "Why This Insight?" always carries methodology + safety note
7. API: POST /intelligence/emerging-patterns/{id}/investigate accepts the full
   #249 contract, enforces path/body id match, and is available to read roles
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.evidence import Evidence
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.location import Location
from app.models.role import Role
from app.models.user import User
from app.models.victim import Victim
from app.services.intelligence_investigation_service import (
    SAFETY_NOTE,
    build_intelligence_investigation,
    is_restricted_record,
    verification_status_for,
)


# ---------------------------------------------------------------------------
# Helpers
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
    user = _make_user(db_session, "inv-analyst", "crime_analyst")
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def viewer_client(client, db_session):
    user = _make_user(db_session, "inv-viewer", "viewer")
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


def _seed(db_session):
    """Two theft cases (one live, one demo) + one RESTRICTED demo case.

    Returns enough references to build a realistic #249 pattern.
    """
    cat_theft = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="high")
    cat_pocso = CrimeCategory(name="Sexual Offences", section_code="POCSO", severity="critical")
    loc_wf = Location(district="Bengaluru Urban", station="Whitefield", latitude=12.9698, longitude=77.7499)
    db_session.add_all([cat_theft, cat_pocso, loc_wf])
    db_session.flush()

    criminal = Criminal(
        full_name="Vikram Singh",
        aliases="Vicky Nightlock",
        status="at_large",
        mo_summary="Late night residential housebreak, lock break, crowbar",
    )
    criminal.dataset_provenance = "live"
    victim = Victim(full_name="Asha Sharma", contact_number="9845012345")
    victim.dataset_provenance = "live"
    db_session.add_all([criminal, victim])
    db_session.flush()

    now = datetime.now(timezone.utc)

    # LIVE verified case + FIR + links + evidence
    c_live = CrimeCase(
        case_number="CC-250-LIVE-01",
        category_id=cat_theft.id,
        location_id=loc_wf.id,
        occurred_at=now,
        reported_at=now,
        status="investigating",
        priority="high",
        description="Night time residential burglary with crowbar",
        mo_tags="night_operation,break_in,tool_usage",
    )
    c_live.dataset_provenance = "live"
    db_session.add(c_live)
    db_session.flush()
    f_live = FIR(
        fir_number="FIR-250-LIVE-1",
        crime_case_id=c_live.id,
        complainant_name="Asha Sharma",
        sections="IPC 380, IPC 457",
        filed_at=now,
        status="investigating",
        narrative="Burglary reported at 0215; door lock forced open overnight.",
    )
    f_live.dataset_provenance = "live"
    db_session.add(f_live)
    db_session.flush()
    db_session.add(FIRCriminalLink(fir_id=f_live.id, criminal_id=criminal.id, role="accused"))
    db_session.add(FIRVictimLink(fir_id=f_live.id, victim_id=victim.id))
    ev_live = Evidence(
        case_id=c_live.id,
        title="CCTV grab — street camera 04",
        description="Footage of unknown male forcing the lock at 0210.",
        evidence_type="video",
        status="Under review",
    )
    ev_live.dataset_provenance = "live"
    db_session.add(ev_live)

    # DEMO case + FIR (demo-derived, non-sensitive)
    c_demo = CrimeCase(
        case_number="CC-250-DEMO-01",
        category_id=cat_theft.id,
        location_id=loc_wf.id,
        occurred_at=now,
        reported_at=now,
        status="open",
        priority="medium",
        description="Bike theft practice pattern from seeded demo dataset",
        mo_tags="night_operation,break_in",
    )
    c_demo.dataset_provenance = "demo"
    db_session.add(c_demo)
    db_session.flush()
    f_demo = FIR(
        fir_number="FIR-250-DEMO-1",
        crime_case_id=c_demo.id,
        complainant_name="Demo Victim",
        sections="IPC 380",
        filed_at=now,
        status="open",
        narrative="Seeded demo burglary record.",
    )
    f_demo.dataset_provenance = "demo"
    db_session.add(f_demo)
    db_session.flush()
    ev_demo = Evidence(
        case_id=c_demo.id,
        title="Demo fingerprint card",
        description="Marginal match to seeded demo offender profile.",
        evidence_type="document",
        status="Pending",
    )
    ev_demo.dataset_provenance = "demo"
    db_session.add(ev_demo)

    # RESTRICTED case + FIR + evidence (demo-derived AND sensitive content)
    c_restricted = CrimeCase(
        case_number="CC-250-RES-01",
        category_id=cat_pocso.id,
        location_id=loc_wf.id,
        occurred_at=now,
        reported_at=now,
        status="open",
        priority="critical",
        description="Sexual assault of a minor child in residential colony",
        mo_tags="night_operation,sexual_assault",
    )
    c_restricted.dataset_provenance = "demo"
    db_session.add(c_restricted)
    db_session.flush()
    f_restricted = FIR(
        fir_number="FIR-250-RES-1",
        crime_case_id=c_restricted.id,
        complainant_name="Guardian",
        sections="POCSO 6, IPC 376",
        filed_at=now,
        status="investigating",
        narrative="Minor child reportedly assaulted; medico-legal done.",
    )
    f_restricted.dataset_provenance = "demo"
    db_session.add(f_restricted)
    db_session.flush()
    ev_restricted = Evidence(
        case_id=c_restricted.id,
        title="Medico-legal report — POCSO",
        description="Age, injuries and corroborating medical findings for the minor.",
        evidence_type="document",
        status="Confidential",
    )
    ev_restricted.dataset_provenance = "demo"
    db_session.add(ev_restricted)

    db_session.commit()
    return {
        "criminal": criminal,
        "victim": victim,
        "c_live": c_live,
        "f_live": f_live,
        "ev_live": ev_live,
        "c_demo": c_demo,
        "f_demo": f_demo,
        "ev_demo": ev_demo,
        "c_restricted": c_restricted,
        "f_restricted": f_restricted,
        "ev_restricted": ev_restricted,
    }


def _pattern(db_session, seeded, *, fir_numbers=None, entity_ids=None, pattern_type="Emerging Theft"):
    if fir_numbers is None:
        fir_numbers = [seeded["f_live"].fir_number]
    if entity_ids is None:
        entity_ids = [str(seeded["criminal"].id), str(seeded["victim"].id)]
    return {
        "intelligence_id": "250-test-pattern-01",
        "pattern_type": pattern_type,
        "location": {
            "district": "Bengaluru Urban",
            "stations": ["Whitefield"],
            "latitude": 12.9698,
            "longitude": 77.7499,
        },
        "affected_h3_cells": ["8928308280fffff"],
        "time_window": "last_30_days",
        "change_from_baseline": {
            "baseline_count": 2,
            "current_count": 5,
            "change_percentage": 150.0,
            "direction": "increasing",
            "baseline_window_days": 90,
            "current_window_days": 30,
        },
        "risk_score": 0.72,
        "forecast": None,
        "confidence": 0.81,
        "supporting_signals": [
            {"signal_type": "temporal", "description": "Late-night timing cluster", "status": "CONFIRMED"},
            {"signal_type": "mo_pattern", "description": "Shared MO: night_operation, break_in", "status": "PROBABLE"},
            {"signal_type": "entity_link", "description": "Vikram Singh linked to 2 related FIRs", "status": "POSSIBLE"},
        ],
        "related_fir_ids": fir_numbers,
        "related_entity_ids": entity_ids,
        "recommended_action_input": {
            "action_type": "patrol_surge",
            "priority": "HIGH",
            "title": "Night patrol surge Whitefield",
            "description": "Increase night visibility around Whitefield residential sectors.",
            "suggested_intervention": {"district": "Bengaluru Urban"},
        },
        "ml_status": "HYBRID",
        "model_name": "SAKSHA Intelligence Fusion",
        "model_version": "2.4.0",
        "detection_timestamp": datetime.now(timezone.utc).isoformat(),
        "explanation": "Pattern: Emerging Theft\nBaseline: 2\nCurrent: 5\nRisk Score: 0.72\nRecommended Action: patrol_surge",
        "contributing_analytics": {
            "forecast": {"status": "AVAILABLE", "trend": "increasing"},
        },
        "data_provenance": "LIVE_DB",
    }


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------

def test_resolves_fir_numbers_to_cases_and_evidence(db_session):
    seeded = _seed(db_session)
    analyst = _make_user(db_session, "svc-analyst", "crime_analyst")

    view = build_intelligence_investigation(db_session, _pattern(db_session, seeded), analyst)

    assert view["intelligence_id"] == "250-test-pattern-01"
    assert [f["fir_number"] for f in view["firs"]] == ["FIR-250-LIVE-1"]
    assert len(view["cases"]) == 1
    assert view["cases"][0]["case_number"] == "CC-250-LIVE-01"
    assert len(view["entities"]) == 2
    names = {e["name"]: e["entity_type"] for e in view["entities"]}
    assert names["Vikram Singh"] == "criminal"
    assert names["Asha Sharma"] == "victim"
    assert len(view["evidence"]) == 1
    assert view["evidence"][0]["title"] == "CCTV grab — street camera 04"


def test_verification_states_derived_from_provenance(db_session):
    seeded = _seed(db_session)
    analyst = _make_user(db_session, "svc-states", "crime_analyst")

    # Unit-level derivation
    assert verification_status_for(seeded["f_live"]) == "VERIFIED"
    assert verification_status_for(seeded["f_demo"]) == "DEMO"
    assert verification_status_for(seeded["f_restricted"]) == "RESTRICTED"
    assert verification_status_for(seeded["ev_restricted"]) == "RESTRICTED"
    assert is_restricted_record(seeded["ev_restricted"]) is True
    assert is_restricted_record(seeded["ev_live"]) is False

    # Wide pattern -> summary across all three states
    view = build_intelligence_investigation(
        db_session,
        _pattern(
            db_session,
            seeded,
            fir_numbers=[
                seeded["f_live"].fir_number,
                seeded["f_demo"].fir_number,
                seeded["f_restricted"].fir_number,
            ],
        ),
        analyst,
    )
    states = {f["fir_number"]: f["verification_status"] for f in view["firs"]}
    assert states["FIR-250-LIVE-1"] == "VERIFIED"
    assert states["FIR-250-DEMO-1"] == "DEMO"
    assert states["FIR-250-RES-1"] == "RESTRICTED"

    summary = view["verification_summary"]
    assert summary["VERIFIED"] >= 1
    assert summary["DEMO"] >= 1
    assert summary["RESTRICTED"] >= 1
    assert all(summary[s] >= 0 for s in ("VERIFIED", "POTENTIAL", "DEMO", "RESTRICTED", "UNVERIFIED"))


def test_restricted_evidence_open_for_reviewer(db_session):
    seeded = _seed(db_session)
    analyst = _make_user(db_session, "svc-review", "crime_analyst")

    view = build_intelligence_investigation(
        db_session,
        _pattern(db_session, seeded, fir_numbers=[seeded["f_restricted"].fir_number]),
        analyst,
    )
    assert view["access"]["has_restricted_access"] is True
    restricted = [e for e in view["evidence"] if e["is_restricted"]]
    assert len(restricted) == 1
    assert restricted[0]["masked"] is False
    assert restricted[0]["title"] == "Medico-legal report — POCSO"
    assert "corroborating medical findings" in restricted[0]["description"]


def test_restricted_evidence_masked_for_non_reviewer(db_session):
    seeded = _seed(db_session)
    viewer = _make_user(db_session, "svc-viewer", "viewer")

    view = build_intelligence_investigation(
        db_session,
        _pattern(db_session, seeded, fir_numbers=[seeded["f_restricted"].fir_number]),
        viewer,
    )
    assert view["access"]["has_restricted_access"] is False
    restricted = [e for e in view["evidence"] if e["is_restricted"]]
    assert len(restricted) == 1
    assert restricted[0]["masked"] is True
    assert restricted[0]["title"] == "[RESTRICTED — reviewer access required]"
    assert restricted[0]["description"] == "[RESTRICTED — reviewer access required]"
    # Verification/status metadata stays visible — only content is masked
    assert restricted[0]["evidence_type"] == "document"
    assert restricted[0]["status"] == "Confidential"


def test_mo_matches_use_structured_similarity(db_session):
    seeded = _seed(db_session)
    analyst = _make_user(db_session, "svc-mo", "crime_analyst")

    view = build_intelligence_investigation(
        db_session,
        _pattern(
            db_session,
            seeded,
            fir_numbers=[
                seeded["f_live"].fir_number,
                seeded["f_demo"].fir_number,
            ],
        ),
        analyst,
    )
    mo = view["mo_matches"]
    assert mo["method"]
    assert "night_operation" in mo["shared_tags"] or "break_in" in mo["shared_tags"]

    # The linked criminal (matching MO profile, confirmed relationship) surfaces as a suspect
    suspects = mo["suspects"]
    assert len(suspects) >= 1
    assert suspects[0]["full_name"] == "Vikram Singh"
    assert suspects[0]["is_confirmed_relationship"] is True
    assert suspects[0]["verification_status"] in ("VERIFIED", "POTENTIAL")

    # Two related cases sharing MO -> analytical POTENTIAL edge in the network
    shared_edges = [e for e in view["network"]["edges"] if e["relationship_type"] == "SHARED_MO"]
    assert len(shared_edges) >= 1
    assert shared_edges[0]["verification_status"] == "POTENTIAL"
    assert "does not establish a confirmed association" in shared_edges[0]["operational_warning"]


def test_network_uses_verified_demo_restricted_vocabulary(db_session):
    seeded = _seed(db_session)
    analyst = _make_user(db_session, "svc-net", "crime_analyst")

    view = build_intelligence_investigation(
        db_session,
        _pattern(
            db_session,
            seeded,
            fir_numbers=[
                seeded["f_live"].fir_number,
                seeded["f_demo"].fir_number,
                seeded["f_restricted"].fir_number,
            ],
        ),
        analyst,
    )
    net = view["network"]
    assert len(net["nodes"]) >= 6
    assert len(net["edges"]) >= 6

    node_ids = {n["id"]: n for n in net["nodes"]}
    for fir in view["firs"]:
        fid = f"case-{fir['id']}"
        assert fid in node_ids
        node = node_ids[fid]
        expected = {
            "FIR-250-LIVE-1": "VERIFIED",
            "FIR-250-DEMO-1": "DEMO",
            "FIR-250-RES-1": "RESTRICTED",
        }[fir["fir_number"]]
        assert node["verification_status"] == expected

    # Every edge carries the full citation vocabulary
    for edge in net["edges"]:
        assert edge["provenance"] in ("DIRECT_DATABASE", "ANALYTICAL_INFERENCE", "DEMO_SEED", "RESTRICTED")
        assert edge["verification_status"] in ("VERIFIED", "POTENTIAL", "DEMO", "RESTRICTED", "UNVERIFIED")
        assert "evidence" in edge


def test_why_this_insight_has_methodology_and_safety_note(db_session):
    seeded = _seed(db_session)
    analyst = _make_user(db_session, "svc-why", "crime_analyst")

    view = build_intelligence_investigation(db_session, _pattern(db_session, seeded), analyst)
    why = view["why_this_insight"]
    assert "Emerging Theft" in why["summary"]
    assert len(why["signals"]) == 3
    assert why["methodology"]["model_name"] == "SAKSHA Intelligence Fusion"
    assert why["methodology"]["analytics_available"]["forecast"] == "AVAILABLE"
    assert "PostgreSQL operational records" in why["data_sources"][0]
    assert why["safety_note"] == SAFETY_NOTE
    assert any("not confirmed guilt or evidence" in l for l in why["limitations"])


def test_orphan_entities_still_surface_in_network(db_session):
    """An entity referenced by intelligence but with no resolved FIR link still joins the graph."""
    seeded = _seed(db_session)
    analyst = _make_user(db_session, "svc-orph", "crime_analyst")

    stray = Criminal(full_name="Ramu Swamy", status="arrested", mo_summary="Fence, contraband resale")
    stray.dataset_provenance = "live"
    db_session.add(stray)
    db_session.commit()

    view = build_intelligence_investigation(
        db_session,
        _pattern(
            db_session,
            seeded,
            entity_ids=[str(seeded["criminal"].id), str(seeded["victim"].id), str(stray.id)],
        ),
        analyst,
    )
    node_ids = {n["id"] for n in view["network"]["nodes"]}
    assert f"criminal-{stray.id}" in node_ids


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------

def test_api_investigate_endpoint(analyst_client, db_session):
    client, _ = analyst_client
    seeded = _seed(db_session)
    pattern = _pattern(db_session, seeded, fir_numbers=[seeded["f_live"].fir_number])

    resp = client.post(
        f"/api/v2/intelligence/emerging-patterns/{pattern['intelligence_id']}/investigate",
        json=pattern,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intelligence_id"] == pattern["intelligence_id"]
    assert len(data["firs"]) == 1
    assert data["firs"][0]["fir_number"] == "FIR-250-LIVE-1"
    assert len(data["evidence"]) == 1
    assert data["network"]["nodes"]
    assert data["access"]["has_restricted_access"] is True
    assert data["why_this_insight"]["safety_note"] == SAFETY_NOTE


def test_api_masked_restricted_for_viewer(viewer_client, db_session):
    client, _ = viewer_client
    seeded = _seed(db_session)
    pattern = _pattern(db_session, seeded, fir_numbers=[seeded["f_restricted"].fir_number])

    resp = client.post(
        f"/api/v2/intelligence/emerging-patterns/{pattern['intelligence_id']}/investigate",
        json=pattern,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access"]["has_restricted_access"] is False
    restricted = [e for e in data["evidence"] if e["is_restricted"]]
    assert restricted and restricted[0]["masked"] is True
    assert restricted[0]["title"] == "[RESTRICTED — reviewer access required]"


def test_api_investigate_id_mismatch_returns_400(analyst_client, db_session):
    client, _ = analyst_client
    seeded = _seed(db_session)
    pattern = _pattern(db_session, seeded)

    resp = client.post(
        "/api/v2/intelligence/emerging-patterns/other-pattern-id/investigate",
        json=pattern,
    )
    assert resp.status_code == 400