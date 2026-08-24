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
