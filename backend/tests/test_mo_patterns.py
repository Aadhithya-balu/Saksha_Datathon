"""Tests for normalized MO storage/backfill, recurring pattern detection,
MO feature vectors, and demo-seed provenance flags
(issue #144: gaps 132.1-132.4)."""
from datetime import datetime, timezone

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink
from app.models.location import Location
from app.models.role import Role
from app.models.user import User
from app.services.mo_pattern_service import (
    detect_recurring_mo_patterns,
    sync_mo_tags,
    tags_for_text,
)
from app.services.network.network_service import _is_seed_case_number

NET = "/api/v2/network"
MO = "/api/v2/ai/mo"


@pytest.fixture
def analyst_client(client, db_session):
    role = db_session.query(Role).filter_by(name="crime_analyst").first()
    if role is None:
        role = Role(name="crime_analyst", description="Crime Analyst")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="pattern-analyst",
        email="pattern-analyst@example.com",
        full_name="Pattern Analyst",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def pattern_fixture(db_session):
    """Two burglars whose MO summaries share night-operation and tool tags."""
    category = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="high")
    location = Location(district="Mysuru", station="Devaraja", latitude=12.3, longitude=76.6)
    crook_a = Criminal(
        full_name="Pattern Alpha",
        status="at_large",
        gang_affiliation="Night Cell",
        mo_summary="Breaks into homes after midnight using an iron rod; always wears gloves.",
    )
    crook_b = Criminal(
        full_name="Pattern Beta",
        status="at_large",
        gang_affiliation="Night Cell",
        mo_summary="Uses an iron rod to pry windows during late-night break-ins.",
    )
    loner = Criminal(
        full_name="Unrelated Lone",
        status="convicted",
        mo_summary="Runs phishing SMS campaigns targeting elderly bank customers.",
    )
    db_session.add_all([category, location, crook_a, crook_b, loner])
    db_session.flush()

    case_a = CrimeCase(
        case_number="CR-PAT-0001", category_id=category.id, location_id=location.id,
        occurred_at=datetime(2026, 6, 10, tzinfo=timezone.utc), status="open",
        description="Midnight house break-in with an iron rod.", mo_tags="night_operation",
    )
    case_b = CrimeCase(
        case_number="CR-PAT-0002", category_id=category.id, location_id=location.id,
        occurred_at=datetime(2026, 6, 18, tzinfo=timezone.utc), status="open",
        description="Iron rod used to pry open a window shutter after midnight.", mo_tags="night_operation",
    )
    db_session.add_all([case_a, case_b])
    db_session.flush()

    fir_a = FIR(fir_number="FIR-PAT-0001", crime_case_id=case_a.id,
                complainant_name="Owner One", sections="457, 380",
                narrative="Intruder entered after midnight carrying an iron rod.")
    fir_b = FIR(fir_number="FIR-PAT-0002", crime_case_id=case_b.id,
                complainant_name="Owner Two", sections="457, 380",
                narrative="Window pried open with an iron rod during the night.")
    db_session.add_all([fir_a, fir_b])
    db_session.flush()

    db_session.add_all([
        FIRCriminalLink(fir_id=fir_a.id, criminal_id=crook_a.id),
        FIRCriminalLink(fir_id=fir_b.id, criminal_id=crook_b.id),
    ])
    db_session.commit()
    return {"crook_a": crook_a, "crook_b": crook_b, "loner": loner, "case_a": case_a}


# ---------------------------------------------------------------------------
# 132.1 lexicon + idempotent backfill
# ---------------------------------------------------------------------------

def test_tags_for_text_lexicon_and_slug():
    tags = tags_for_text("Broke in at midnight with an iron rod and fled on a stolen motorcycle KA-05-MN-9087")
    assert "night_operation" in tags
    assert "tool_usage" in tags
    assert "vehicle_crime" in tags


def test_sync_mo_tags_is_idempotent(pattern_fixture, db_session):
    first = sync_mo_tags(db_session)
    assert first["criminals_scanned"] == 3
    assert first["tags_created"] > 0
    assert first["criminal_links_created"] > 0

    second = sync_mo_tags(db_session)
    total_links = first["case_links_created"] + first["criminal_links_created"]
    assert second["tags_created"] == 0
    assert second["case_links_created"] == 0
    assert second["criminal_links_created"] == 0
    assert second["already_synced"] == total_links


# ---------------------------------------------------------------------------
# 132.2 recurring-MO detection
# ---------------------------------------------------------------------------

def test_patterns_group_shared_mo_offenders(pattern_fixture, db_session):
    body = detect_recurring_mo_patterns(db_session, min_support=2)
    assert body["min_support"] == 2
    matching = [
        p for p in body["patterns"]
        if {"Pattern Alpha", "Pattern Beta"} <= {m["label"] for m in p["members"] if m["kind"] == "criminal"}
    ]
    assert matching, "co-MO offenders were not grouped"
    pattern = matching[0]
    assert pattern["support"] >= 2
    assert pattern["threat_score"] > 0
    assert len(pattern["shared_tags"]) >= 2
    # The unrelated phishing offender must never join the burglary pattern.
    all_member_labels = {m["label"] for p in body["patterns"] for m in p["members"]}
    if "Unrelated Lone" in all_member_labels:
        lone_patterns = [p for p in body["patterns"]
                         if any(m["label"] == "Unrelated Lone" for m in p["members"])]
        assert all({"Pattern Alpha", "Pattern Beta"}.isdisjoint({m["label"] for m in p["members"]})
                   for p in lone_patterns)


def test_patterns_min_support_filters_singletons(pattern_fixture, db_session):
    body = detect_recurring_mo_patterns(db_session, min_support=2)
    for pattern in body["patterns"]:
        assert pattern["support"] >= 2


def test_patterns_endpoint(analyst_client, pattern_fixture):
    c, _ = analyst_client
    r = c.get(f"{MO}/patterns?min_support=2")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["min_support"] == 2
    assert body["entities_analysed"]["criminals"] == 3
    assert isinstance(body["patterns"], list)

    r_sync = c.post(f"{MO}/sync-tags", json={})
    assert r_sync.status_code == 200, r.text
    stats = r_sync.json()
    assert stats["cases_scanned"] == 2
    assert stats["criminals_scanned"] == 3


# ---------------------------------------------------------------------------
# 132.3 MO features in similarity vectors
# ---------------------------------------------------------------------------

def test_extractor_emits_14_feature_vector(pattern_fixture, db_session):
    from app.ai.features.criminal.extractor import FEATURE_NAMES, extract_for_criminal

    result = extract_for_criminal(db_session, pattern_fixture["crook_a"])
    assert len(result.values) == len(FEATURE_NAMES) == 14
    raw = result.raw
    assert raw["mo_tags"], "expected canonical MO tags on raw payload"
    assert raw["mo_tags"] and any("night" in tag for tag in raw["mo_tags"])
    assert result.values[FEATURE_NAMES.index("mo_night_flag")] == 1.0   # midnight language
    assert result.values[FEATURE_NAMES.index("mo_weapon_flag")] == 1.0  # iron rod -> tool_usage


# ---------------------------------------------------------------------------
# 132.4 seed provenance flags
# ---------------------------------------------------------------------------

def test_seed_case_number_detection():
    assert _is_seed_case_number("CR-2026-SYN-001") is True
    assert _is_seed_case_number("CR-NET-0001") is False
    assert _is_seed_case_number(None) is False
    assert _is_seed_case_number("") is False


def test_graph_reports_live_scope_without_seed_data(analyst_client, pattern_fixture):
    """Non-seed records only -> dataset_scope stays 'live_records'."""
    c, _ = analyst_client
    r = c.get(f"{NET}/graph")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dataset_scope"] == "live_records"
    assert body["seed_node_count"] == 0
    assert all(node.get("isSeed") in (False, None) for node in body["nodes"])

    r_gangs = c.get(f"{NET}/gangs")
    assert r_gangs.status_code == 200, r_gangs.text
    gangs = r_gangs.json()
    assert gangs, "expected at least one gang from affiliations"
    for gang in gangs:
        assert gang["is_demo_derived"] is False
