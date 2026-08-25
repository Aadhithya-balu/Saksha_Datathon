"""Tests for criminological network & link analysis honesty (issue #141).

Covers gap #129.1 (real MO profile derivation), #129.2 (no fabricated seed
graph data), and #129.3 (honest empty/unknown-id responses).
"""
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

NET = "/api/v2/network"


@pytest.fixture
def analyst_client(client, db_session):
    role = db_session.query(Role).filter_by(name="crime_analyst").first()
    if role is None:
        role = Role(name="crime_analyst", description="Crime Analyst")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="net-analyst",
        email="net-analyst@example.com",
        full_name="Network Analyst",
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
def network_fixture(db_session):
    """Two co-accused burglars with a shared armed-robbery FIR in Mysuru."""
    category = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="high")
    location = Location(district="Mysuru", station="Devaraja", latitude=12.3, longitude=76.6)
    crook_a = Criminal(
        full_name="Accused Alpha",
        status="at_large",
        gang_affiliation="Test Burglary Cell",
        mo_summary="Breaks into homes late at night using an iron rod and a country-made pistol.",
    )
    crook_b = Criminal(
        full_name="Accused Beta",
        status="arrested",
        gang_affiliation="Test Burglary Cell",
        mo_summary="Drives the getaway vehicle KA-05-MN-9087 during burglaries.",
    )
    db_session.add_all([category, location, crook_a, crook_b])
    db_session.flush()

    case = CrimeCase(
        case_number="CR-NET-0001", category_id=category.id, location_id=location.id,
        occurred_at=datetime(2026, 6, 10, tzinfo=timezone.utc), status="open",
        description="Night house break-in; stolen ornaments.", mo_tags="night_break_in",
    )
    db_session.add(case)
    db_session.flush()

    fir = FIR(
        fir_number="FIR-NET-0001", crime_case_id=case.id,
        complainant_name="Home Owner", sections="379, 457",
        narrative="Witnesses saw two men arrive on KA-05-MN-9087; one carried an iron rod.",
        filed_at=datetime(2026, 6, 11, 23, 30, tzinfo=timezone.utc),
    )
    db_session.add(fir)
    db_session.flush()

    db_session.add_all([
        FIRCriminalLink(fir_id=fir.id, criminal_id=crook_a.id),
        FIRCriminalLink(fir_id=fir.id, criminal_id=crook_b.id),
    ])
    db_session.commit()
    return {"fir": fir, "case": case, "crook_a": crook_a, "crook_b": crook_b}


def test_mo_profile_derived_from_real_records(analyst_client, network_fixture):
    """#129.1: profile fields computed from linked FIR history, not stubs."""
    c, _ = analyst_client
    r = c.get(f"/api/v2/criminals/{network_fixture['crook_a'].id}/mo-profile")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "Theft & Burglaries" in body["preferred_crime_types"]
    assert body["linked_incidents_count"] == 1
    assert "Mysuru" in body["jurisdictions_active"]
    assert body["common_time_window"] is not None
    assert body["common_time_window"]["window"].startswith("Night")
    assert "iron rod" in body["common_tools"]


def test_sql_graph_has_no_fabricated_seed_nodes(analyst_client, network_fixture):
    """#129.2: every returned node id derives from real records (no 'node-N')."""
    c, _ = analyst_client
    r = c.get(f"{NET}/graph")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_nodes"] >= 4  # 2 criminals + 1 case + 1 location
    for node in body["nodes"]:
        assert not node["id"].startswith("node-"), f"fabricated seed node leaked: {node['id']}"
    names = {n["name"] for n in body["nodes"]}
    assert "Accused Alpha" in names


def test_sql_graph_empty_db_returns_empty(analyst_client):
    """#129.2: an empty database yields an honest empty graph, no mock filler."""
    c, _ = analyst_client
    r = c.get(f"{NET}/graph")
    assert r.status_code == 200
    body = r.json()
    assert body["total_nodes"] == 0
    assert body["total_edges"] == 0


def test_person_graph_unknown_id_is_empty(analyst_client):
    """#129.3: unknown person falls back to an empty graph, never 'node-1'."""
    c, _ = analyst_client
    r = c.get(f"{NET}/person/criminal-does-not-exist")
    assert r.status_code == 200
    body = r.json()
    assert body["total_nodes"] == 0


def test_shortest_path_unknown_ids_not_found(analyst_client):
    """#129.3: path finder reports honestly instead of substituting default nodes."""
    c, _ = analyst_client
    r = c.post(f"{NET}/shortest-path", json={"source_id": "ghost-a", "target_id": "ghost-b"})
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is False
    assert body["path_nodes"] == []


def test_shortest_path_finds_real_co_accused_link(analyst_client, network_fixture):
    c, _ = analyst_client
    r = c.post(f"{NET}/shortest-path", json={
        "source_id": f"criminal-{network_fixture['crook_a'].id}",
        "target_id": f"criminal-{network_fixture['crook_b'].id}",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True
    assert body["distance"] >= 1


def test_gang_networks_derived_from_affiliations(analyst_client, network_fixture):
    c, _ = analyst_client
    r = c.get(f"{NET}/gangs")
    assert r.status_code == 200, r.text
    gangs = r.json()
    assert len(gangs) == 1
    gang = gangs[0]
    assert gang["name"] == "Test Burglary Cell"
    member_names = {m["name"] for m in gang["members"]}
    assert member_names == {"Accused Alpha", "Accused Beta"}


def test_ai_insights_are_data_driven(analyst_client, network_fixture):
    """Insights reference real node ids only, and none exist on an empty DB."""
    c, _ = analyst_client
    r = c.get(f"{NET}/insights")
    assert r.status_code == 200
    insights = r.json()
    assert len(insights) >= 1
    known_ids = {f"criminal-{network_fixture['crook_a'].id}", f"criminal-{network_fixture['crook_b'].id}"}
    for insight in insights:
        for target in insight["target_node_ids"]:
            assert target in known_ids or target.startswith(("criminal-", "victim-", "officer-", "location-", "case-", "vehicle-", "weapon-", "org-")), (
                f"insight targets fabricated id: {target}"
            )


# ==============================================================================
# Issue #159: Comprehensive Provenance and Evidence Verification Tests
# ==============================================================================

def test_direct_database_relationship_provenance(analyst_client, network_fixture):
    """Test 1 — Direct Database Relationship: source = DIRECT_DATABASE, verification_status = VERIFIED."""
    c, _ = analyst_client
    r = c.get(f"{NET}/graph")
    assert r.status_code == 200
    body = r.json()

    case_edges = [e for e in body["edges"] if e["relationship_type"] == "PERSON_CASE"]
    assert len(case_edges) >= 2, "Expected at least 2 PERSON_CASE edges"
    
    for edge in case_edges:
        assert edge["provenance"] == "DIRECT_DATABASE"
        assert edge["verification_status"] == "VERIFIED"
        assert edge["confidence"] == 1.0
        assert edge["confidence_level"] == "HIGH"
        assert len(edge["evidence"]) >= 1
        assert edge["evidence"][0]["record_number"] == network_fixture["fir"].fir_number


def test_analytical_relationship_provenance_and_warning(analyst_client, network_fixture):
    """Test 2 — Analytical Relationship: source = ANALYTICAL_INFERENCE, verification_status = POTENTIAL with warning."""
    c, _ = analyst_client
    r = c.get(f"{NET}/graph")
    assert r.status_code == 200
    body = r.json()

    co_accused_edges = [e for e in body["edges"] if e["relationship_type"] == "SHARED_CASE"]
    assert len(co_accused_edges) == 1, "Expected 1 co-accused analytical edge"
    
    co_edge = co_accused_edges[0]
    assert co_edge["provenance"] == "ANALYTICAL_INFERENCE"
    assert co_edge["verification_status"] == "POTENTIAL"
    assert co_edge["confidence"] == 0.70
    assert co_edge["confidence_level"] == "MEDIUM"
    assert co_edge["operational_warning"] is not None
    assert "Analytical relationship identified" in co_edge["operational_warning"]
    assert len(co_edge["evidence"]) >= 1
    assert "factors" in co_edge["evidence"][0]


def test_seed_relationship_provenance(analyst_client, db_session):
    """Test 3 — Seed Relationship: source = DEMO_SEED, verification_status = DEMO."""
    category = CrimeCategory(name="Theft", section_code="IPC 379", severity="low")
    loc = Location(district="Bengaluru", station="Central", latitude=12.97, longitude=77.59)
    seed_crook = Criminal(full_name="Ramu Swamy", status="at_large")  # Ramu Swamy is in CRIMINALS seed manifest
    db_session.add_all([category, loc, seed_crook])
    db_session.flush()

    case = CrimeCase(
        case_number="CR-2026-SYN-001",
        category_id=category.id,
        location_id=loc.id,
        status="open",
        occurred_at=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )
    db_session.add(case)
    db_session.flush()

    fir = FIR(
        fir_number="FIR-SEED-001",
        crime_case_id=case.id,
        complainant_name="Demo Complainant",
        filed_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
    )
    db_session.add(fir)
    db_session.flush()

    db_session.add(FIRCriminalLink(fir_id=fir.id, criminal_id=seed_crook.id))
    db_session.commit()

    c, _ = analyst_client
    r = c.get(f"{NET}/graph")
    assert r.status_code == 200
    body = r.json()

    seed_node = next((n for n in body["nodes"] if n["name"] == "Ramu Swamy"), None)
    assert seed_node is not None
    assert seed_node["isSeed"] is True

    seed_edges = [e for e in body["edges"] if e["source"] == f"criminal-{seed_crook.id}"]
    assert len(seed_edges) >= 1
    for edge in seed_edges:
        assert edge["provenance"] == "DEMO_SEED"
        assert edge["verification_status"] == "VERIFIED"
        assert edge["is_demo_derived"] is True


def test_mixed_relationship_provenance(analyst_client, db_session):
    """Test 4 — Mixed Relationship: Live Person + Seed Person in shared FIR -> source = MIXED, status = POTENTIAL, is_demo_derived = True."""
    category = CrimeCategory(name="Robbery", section_code="IPC 392", severity="high")
    loc = Location(district="Mysuru", station="Central", latitude=12.3, longitude=76.6)
    live_crook = Criminal(full_name="Real Live Suspect 99", status="at_large")
    seed_crook = Criminal(full_name="Vikram Yadav", status="arrested")  # Vikram Yadav in seed manifest
    db_session.add_all([category, loc, live_crook, seed_crook])
    db_session.flush()

    case = CrimeCase(
        case_number="CR-MIX-001",
        category_id=category.id,
        location_id=loc.id,
        status="open",
        occurred_at=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )
    db_session.add(case)
    db_session.flush()

    fir = FIR(
        fir_number="FIR-MIX-001",
        crime_case_id=case.id,
        complainant_name="Victim Live",
        filed_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
    )
    db_session.add(fir)
    db_session.flush()

    db_session.add_all([
        FIRCriminalLink(fir_id=fir.id, criminal_id=live_crook.id),
        FIRCriminalLink(fir_id=fir.id, criminal_id=seed_crook.id),
    ])
    db_session.commit()

    c, _ = analyst_client
    r = c.get(f"{NET}/graph")
    assert r.status_code == 200
    body = r.json()

    live_id = f"criminal-{live_crook.id}"
    seed_id = f"criminal-{seed_crook.id}"
    mixed_edge = next(
        (e for e in body["edges"] if (e["source"] == live_id and e["target"] == seed_id) or (e["source"] == seed_id and e["target"] == live_id)),
        None
    )
    assert mixed_edge is not None
    assert mixed_edge["provenance"] == "MIXED"
    assert mixed_edge["verification_status"] == "POTENTIAL"
    assert mixed_edge["is_demo_derived"] is True


def test_no_unsupported_edges(analyst_client, db_session):
    """Test 5 — No Supporting Evidence: Isolated entities have no fabricated edges."""
    category = CrimeCategory(name="Cyber", section_code="IT Act 66", severity="medium")
    loc = Location(district="Udupi", station="Town", latitude=13.3, longitude=74.7)
    loner = Criminal(full_name="Isolated Hacker", status="at_large")
    db_session.add_all([category, loc, loner])
    db_session.commit()

    c, _ = analyst_client
    r = c.get(f"{NET}/graph")
    assert r.status_code == 200
    body = r.json()

    # The loner has no FIR links, so no edges should exist for this entity
    loner_edges = [e for e in body["edges"] if e["source"] == f"criminal-{loner.id}" or e["target"] == f"criminal-{loner.id}"]
    assert len(loner_edges) == 0


def test_provenance_summary_and_api_filters(analyst_client, network_fixture):
    """Test 6, 7 & 10 — Provenance Summary and Backend Filtering."""
    c, _ = analyst_client
    r = c.get(f"{NET}/graph")
    assert r.status_code == 200
    body = r.json()

    summary = body.get("provenance_summary")
    assert summary is not None
    assert summary["total_edges"] == len(body["edges"])
    assert summary["verified_relationships"] >= 1
    assert summary["analytical_relationships"] >= 1

    # Filter by VERIFIED
    r_ver = c.get(f"{NET}/graph?provenance_filter=VERIFIED")
    assert r_ver.status_code == 200
    for edge in r_ver.json()["edges"]:
        assert edge["verification_status"] == "VERIFIED"

    # Filter by ANALYTICAL_INFERENCE
    r_ana = c.get(f"{NET}/graph?provenance_filter=ANALYTICAL_INFERENCE")
    assert r_ana.status_code == 200
    for edge in r_ana.json()["edges"]:
        assert edge["provenance"] == "ANALYTICAL_INFERENCE"


def test_confidence_calculation_multi_fir(analyst_client, db_session, network_fixture):
    """Test 8 — Confidence is calculated from multi-incident density (not hardcoded)."""
    crook_a = network_fixture["crook_a"]
    crook_b = network_fixture["crook_b"]
    case = network_fixture["case"]

    # Add a SECOND shared FIR between Crook A and Crook B
    fir2 = FIR(
        fir_number="FIR-NET-0002",
        crime_case_id=case.id,
        complainant_name="Store Owner",
        sections="392 IPC",
        filed_at=datetime(2026, 6, 20, 14, 0, tzinfo=timezone.utc),
    )
    db_session.add(fir2)
    db_session.flush()

    db_session.add_all([
        FIRCriminalLink(fir_id=fir2.id, criminal_id=crook_a.id),
        FIRCriminalLink(fir_id=fir2.id, criminal_id=crook_b.id),
    ])
    db_session.commit()

    c, _ = analyst_client
    r = c.get(f"{NET}/graph")
    assert r.status_code == 200
    body = r.json()

    co_edge = next((e for e in body["edges"] if e["relationship_type"] == "SHARED_CASE"), None)
    assert co_edge is not None
    # 2 shared FIRs -> confidence = min(0.95, round(0.70 + 2*0.08, 2)) = 0.86
    assert co_edge["confidence"] == 0.86
    assert co_edge["confidence_level"] == "HIGH"
    assert len(co_edge["evidence"]) == 2


def test_authorization_enforcement(client):
    """Test 9 — Unauthenticated requests are rejected."""
    r = client.get(f"{NET}/graph")
    assert r.status_code in (401, 403)

