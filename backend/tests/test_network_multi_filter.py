"""Tests for multi-parameter Network Analysis search & filtering (issue #226).

Verifies server-side structured filters (criminal name, crime type, district,
police station, FIR/case number, victim name, date range), combined AND/OR
semantics, empty results, backward compatibility, authorization, and that the
returned nodes/edges correspond only to the filtered dataset.
"""
from datetime import datetime, timezone

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.location import Location
from app.models.role import Role
from app.models.user import User
from app.models.victim import Victim

NET = "/api/v2/network"


@pytest.fixture
def analyst_client(client, db_session):
    role = db_session.query(Role).filter_by(name="crime_analyst").first()
    if role is None:
        role = Role(name="crime_analyst", description="Crime Analyst")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="net-filter-analyst",
        email="net-filter-analyst@example.com",
        full_name="Network Filter Analyst",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


def _build_dataset(db_session):
    """Seed a small heterogeneous dataset for filter assertions.

    Returns dict keyed by label -> ORM object.
    """
    theft = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="high")
    robbery = CrimeCategory(name="Robbery", section_code="IPC 392", severity="high")
    narcotics = CrimeCategory(name="Narcotics", section_code="NDPS 22", severity="high")

    bengaluru = Location(district="Bengaluru Urban", station="Whitefield", latitude=12.97, longitude=77.75)
    mysuru = Location(district="Mysuru", station="Devaraja", latitude=12.3, longitude=76.6)

    theft_alpha = Criminal(full_name="Theft Alpha", status="at_large", gang_affiliation="Bengaluru Cell")
    theft_beta = Criminal(full_name="Theft Beta", status="arrested", gang_affiliation="Bengaluru Cell")
    robbery_gamma = Criminal(full_name="Robbery Gamma", status="at_large")
    narcotics_delta = Criminal(full_name="Narcotics Delta", status="under_trial")
    isolated = Criminal(full_name="Isolated Epsilon", status="at_large")

    victim_b = Victim(full_name="Bengaluru Victim", gender="F", age=34)
    victim_m = Victim(full_name="Mysuru Victim", gender="M", age=41)

    db_session.add_all([
        theft, robbery, narcotics,
        bengaluru, mysuru,
        theft_alpha, theft_beta, robbery_gamma, narcotics_delta, isolated,
        victim_b, victim_m,
    ])
    db_session.flush()

    case_b_theft = CrimeCase(
        case_number="CR-FIL-0001", category_id=theft.id, location_id=bengaluru.id,
        occurred_at=datetime(2026, 6, 10, tzinfo=timezone.utc), status="open",
        description="Theft in Bengaluru", mo_tags="night_break_in",
    )
    case_m_theft = CrimeCase(
        case_number="CR-FIL-0002", category_id=theft.id, location_id=mysuru.id,
        occurred_at=datetime(2026, 7, 15, tzinfo=timezone.utc), status="open",
        description="Theft in Mysuru", mo_tags="street_snatch",
    )
    case_b_robbery = CrimeCase(
        case_number="CR-FIL-0003", category_id=robbery.id, location_id=bengaluru.id,
        occurred_at=datetime(2026, 8, 5, tzinfo=timezone.utc), status="open",
        description="Robbery in Bengaluru", mo_tags=None,
    )
    db_session.add_all([case_b_theft, case_m_theft, case_b_robbery])
    db_session.flush()

    fir_b_theft = FIR(
        fir_number="FIR-FIL-0001", crime_case_id=case_b_theft.id,
        complainant_name="Bengaluru Victim", sections="379",
        filed_at=datetime(2026, 6, 11, 22, 30, tzinfo=timezone.utc),
    )
    fir_m_theft = FIR(
        fir_number="FIR-FIL-0002", crime_case_id=case_m_theft.id,
        complainant_name="Mysuru Victim", sections="379",
        filed_at=datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc),
    )
    fir_b_robbery = FIR(
        fir_number="FIR-FIL-0003", crime_case_id=case_b_robbery.id,
        complainant_name="Bank Manager", sections="392",
        filed_at=datetime(2026, 8, 6, 14, 20, tzinfo=timezone.utc),
    )
    # FIR linked to a narcotics case in Bengaluru (used for OR / isolation checks)
    case_b_narcotics = CrimeCase(
        case_number="CR-FIL-0004", category_id=narcotics.id, location_id=bengaluru.id,
        occurred_at=datetime(2026, 9, 1, tzinfo=timezone.utc), status="open",
        description="Narcotics in Bengaluru", mo_tags=None,
    )
    db_session.add(case_b_narcotics)
    db_session.flush()
    fir_b_narcotics = FIR(
        fir_number="FIR-FIL-0004", crime_case_id=case_b_narcotics.id,
        complainant_name="NCB Informant", sections="NDPS 22",
        filed_at=datetime(2026, 9, 2, 9, 15, tzinfo=timezone.utc),
    )
    db_session.add_all([fir_b_theft, fir_m_theft, fir_b_robbery, fir_b_narcotics])
    db_session.flush()

    db_session.add_all([
        FIRCriminalLink(fir_id=fir_b_theft.id, criminal_id=theft_alpha.id),
        FIRCriminalLink(fir_id=fir_b_theft.id, criminal_id=theft_beta.id),
        FIRCriminalLink(fir_id=fir_b_theft.id, criminal_id=robbery_gamma.id),
        FIRCriminalLink(fir_id=fir_m_theft.id, criminal_id=theft_alpha.id),
        FIRCriminalLink(fir_id=fir_b_robbery.id, criminal_id=robbery_gamma.id),
        FIRCriminalLink(fir_id=fir_b_narcotics.id, criminal_id=narcotics_delta.id),
        FIRVictimLink(fir_id=fir_b_theft.id, victim_id=victim_b.id),
        FIRVictimLink(fir_id=fir_m_theft.id, victim_id=victim_m.id),
        FIRVictimLink(fir_id=fir_b_robbery.id, victim_id=victim_b.id),
    ])
    db_session.commit()

    return {
        "theft_alpha": theft_alpha, "theft_beta": theft_beta,
        "robbery_gamma": robbery_gamma, "narcotics_delta": narcotics_delta,
        "isolated": isolated, "victim_b": victim_b,
        "fir_b_theft": fir_b_theft, "fir_m_theft": fir_m_theft,
        "fir_b_robbery": fir_b_robbery, "fir_b_narcotics": fir_b_narcotics,
        "case_b_theft": case_b_theft, "case_b_narcotics": case_b_narcotics,
    }


def _node_names(body):
    return {n["name"] for n in body["nodes"]}


def _node_ids(body):
    return {n["id"] for n in body["nodes"]}


def _names_of_category(body, category):
    return {n["name"] for n in body["nodes"] if n["category"] == category}


# ---------------------------------------------------------------------------
# Structured filters
# ---------------------------------------------------------------------------

def test_filter_by_criminal_name(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"criminal_name": "Theft Alpha"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_nodes"] >= 1
    names = _node_names(body)
    assert "Theft Alpha" in names
    assert "Theft Beta" in names  # co-accused in the same matching FIR
    assert "Robbery Gamma" in names  # co-accused with Alpha in the Bengaluru theft FIR
    assert "Narcotics Delta" not in names
    assert "Isolated Epsilon" not in names


def test_filter_by_crime_type(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"crime_type": "Robbery"})
    assert r.status_code == 200, r.text
    body = r.json()
    names = _node_names(body)
    assert "Robbery Gamma" in names
    assert "Theft Alpha" not in names
    assert "Theft Beta" not in names
    # Only the robbery FIR case node remains
    case_nodes = _names_of_category(body, "case")
    assert case_nodes == {"FIR #FIR-FIL-0003"}


def test_filter_by_district(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"district": "Bengaluru Urban"})
    assert r.status_code == 200, r.text
    body = r.json()
    # All location nodes belong to Bengaluru
    for node in body["nodes"]:
        if node["category"] == "location":
            assert "Bengaluru" in node["name"], node["name"]
    case_nodes = _names_of_category(body, "case")
    assert {"FIR #FIR-FIL-0001", "FIR #FIR-FIL-0003", "FIR #FIR-FIL-0004"} == case_nodes
    assert "FIR #FIR-FIL-0002" not in case_nodes  # Mysuru theft excluded


def test_crime_type_plus_district_combined(analyst_client, db_session):
    """The marquee scenario: 'show me thefts in Bengaluru'."""
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"crime_type": "Theft", "district": "Bengaluru"})
    assert r.status_code == 200, r.text
    body = r.json()
    case_nodes = _names_of_category(body, "case")
    assert case_nodes == {"FIR #FIR-FIL-0001"}
    names = _node_names(body)
    # Theft in Bengaluru only: co-accused trio of the Bengaluru theft FIR.
    assert {"Theft Alpha", "Theft Beta", "Robbery Gamma"} <= names
    assert "Narcotics Delta" not in names
    # Mysuru theft FIR must not appear even though category matches.
    location_names = _names_of_category(body, "location")
    assert all("Bengaluru" in ln for ln in location_names)


def test_and_behaviour_across_parameters(analyst_client, db_session):
    """AND across parameters: an impossible combination yields no results."""
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"crime_type": "Robbery", "district": "Mysuru"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_nodes"] == 0
    assert body["total_edges"] == 0


def test_multiple_crime_types_use_or_semantics(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"crime_type": "Theft,Robbery"})
    assert r.status_code == 200, r.text
    body = r.json()
    case_nodes = _names_of_category(body, "case")
    assert {
        "FIR #FIR-FIL-0001", "FIR #FIR-FIL-0002", "FIR #FIR-FIL-0003",
    } <= case_nodes
    assert "FIR #FIR-FIL-0004" not in case_nodes


def test_multiple_districts_use_or_semantics(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"district": "Mysuru,Bengaluru"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "FIR #FIR-FIL-0002" in _names_of_category(body, "case")
    assert "FIR #FIR-FIL-0001" in _names_of_category(body, "case")


def test_victim_name_filter(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"victim_name": "Bengaluru Victim"})
    assert r.status_code == 200, r.text
    body = r.json()
    names = _node_names(body)
    assert "Bengaluru Victim" in names
    assert "Mysuru Victim" not in names
    # Only FIRs where the Bengaluru Victim appears (theft + robbery, both Bengaluru).
    case_nodes = _names_of_category(body, "case")
    assert {"FIR #FIR-FIL-0001", "FIR #FIR-FIL-0003"} == case_nodes


def test_fir_number_filter(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"fir_number": "FIR-FIL-0003"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert _names_of_category(body, "case") == {"FIR #FIR-FIL-0003"}


def test_case_number_filter(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"fir_number": "CR-FIL-0002"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert _names_of_category(body, "case") == {"FIR #FIR-FIL-0002"}


def test_police_station_filter(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"police_station": "Whitefield"})
    assert r.status_code == 200, r.text
    body = r.json()
    case_nodes = _names_of_category(body, "case")
    assert {"FIR #FIR-FIL-0001", "FIR #FIR-FIL-0003", "FIR #FIR-FIL-0004"} == case_nodes
    assert "FIR #FIR-FIL-0002" not in case_nodes


def test_date_range_filter(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"date_from": "2026-08-01"})
    assert r.status_code == 200, r.text
    body = r.json()
    case_nodes = _names_of_category(body, "case")
    assert {"FIR #FIR-FIL-0003", "FIR #FIR-FIL-0004"} == case_nodes
    assert "FIR #FIR-FIL-0001" not in case_nodes
    assert "FIR #FIR-FIL-0002" not in case_nodes

    r2 = c.get(f"{NET}/graph", params={"date_to": "2026-07-31", "date_from": "2026-07-01"})
    assert r2.status_code == 200
    body2 = r2.json()
    assert _names_of_category(body2, "case") == {"FIR #FIR-FIL-0002"}


def test_invalid_date_returns_422(analyst_client):
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"date_from": "not-a-date"})
    assert r.status_code == 422, r.text


# ---------------------------------------------------------------------------
# Empty / default / backward-compatibility states
# ---------------------------------------------------------------------------

def test_unfiltered_graph_still_returns_full_dataset(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph")
    assert r.status_code == 200, r.text
    body = r.json()
    names = _node_names(body)
    assert "Isolated Epsilon" in names  # unfiltered graph keeps the enrichment pass
    case_nodes = _names_of_category(body, "case")
    assert {
        "FIR #FIR-FIL-0001", "FIR #FIR-FIL-0002", "FIR #FIR-FIL-0003", "FIR #FIR-FIL-0004",
    } <= case_nodes


def test_empty_results_are_handled(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"district": "NONEXISTENT"})
    assert r.status_code == 200
    body = r.json()
    assert body["nodes"] == []
    assert body["edges"] == []
    assert body["total_nodes"] == 0
    assert body["total_edges"] == 0


def test_existing_category_and_risk_filters_still_work(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"category_filter": "victim", "min_risk": 0})
    assert r.status_code == 200, r.text
    body = r.json()
    assert all(n["category"] == "victim" for n in body["nodes"])


# ---------------------------------------------------------------------------
# Graph fidelity: nodes/edges correspond only to the filtered dataset
# ---------------------------------------------------------------------------

def test_edges_derived_only_from_filtered_firs(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"crime_type": "Theft", "district": "Bengaluru"})
    assert r.status_code == 200, r.text
    body = r.json()

    all_edge_ids = set()
    for e in body["edges"]:
        all_edge_ids.update({e["source"], e["target"]})
    node_ids = _node_ids(body)
    assert all_edge_ids <= node_ids  # every edge endpoint is a returned node

    # No edge references the Mysuru FIR case node.
    mysuru_case_id = f"case-{d['fir_m_theft'].id}"
    assert mysuru_case_id not in node_ids
    assert all(mysuru_case_id not in (e["source"], e["target"]) for e in body["edges"])

    # Co-accused analytic edges derived from the single matching FIR
    # (3 accused -> 3 pairwise SHARED_CASE edges, all within the filtered set).
    co_edges = [e for e in body["edges"] if e["relationship_type"] == "SHARED_CASE"]
    assert len(co_edges) == 3
    for e in co_edges:
        assert all(n in node_ids for n in (e["source"], e["target"]))


def test_isolated_unrelated_entities_are_excluded(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(f"{NET}/graph", params={"district": "Mysuru"})
    assert r.status_code == 200, r.text
    body = r.json()
    names = _node_names(body)
    # Isolated criminal with no FIR and thieves active only in Bengaluru are excluded.
    assert "Isolated Epsilon" not in names


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

def test_unauthorized_cannot_use_new_filters(client):
    r = client.get(f"{NET}/graph", params={"crime_type": "Theft", "district": "Bengaluru"})
    assert r.status_code in (401, 403)


def test_sql_injection_cannot_manipulate_query(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    payload = "Alpha' OR '1'='1 --"
    r = c.get(f"{NET}/graph", params={"criminal_name": payload})
    assert r.status_code == 200, r.text
    body = r.json()
    # Parameterised matching treats the payload as a literal substring -> no match.
    assert body["total_nodes"] == 0
    assert "error" not in str(body).lower() and "traceback" not in str(body).lower()