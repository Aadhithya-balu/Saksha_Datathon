"""Tests for the Investigative Path Finder (issue #230).

Verifies the evidence-backed person-to-person connection search:
direct/2/3-hop paths, max-hops bounding, shortest-path selection, cycle safety,
duplicate shared-FIR evidence aggregation, issue #226 filter compatibility
(AND/OR, crime type + district), authorization, parameterised SQL safety, and
neutral not-found behaviour that never leaks out-of-filter records.
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
from app.models.officer import Officer
from app.models.role import Role
from app.models.user import User
from app.models.victim import Victim

NET = "/api/v2/network"
PATH = f"{NET}/path"


@pytest.fixture
def analyst_client(client, db_session):
    role = db_session.query(Role).filter_by(name="crime_analyst").first()
    if role is None:
        role = Role(name="crime_analyst", description="Crime Analyst")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="net-path-analyst",
        email="net-path-analyst@example.com",
        full_name="Network Path Analyst",
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
    """Seed an entity graph with explicit FIR-level relationships.

    Structure (people A-E via shared FIRs):
      FIR-PTH-0001 (Theft, Bengaluru):  A, B, Victim X, Officer One
      FIR-PTH-0002 (Theft, Mysuru):      B, C
      FIR-PTH-0003 (Robbery, Mysuru):    C, D
      FIR-PTH-0004 (Robbery, Mysuru):    D, E
      FIR-PTH-0005 (Robbery, Bengaluru): A, D         (direct A-D shortcut)
      FIR-PTH-0006 (Smuggling, Mysuru):  A, C         (closes A-B-C-A triangle)
    Isolated I shares no FIR with anyone.
    """
    theft = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="high")
    robbery = CrimeCategory(name="Robbery", section_code="IPC 392", severity="high")
    smuggling = CrimeCategory(name="Smuggling", section_code="IPC 489", severity="high")

    bengaluru = Location(district="Bengaluru Urban", station="Whitefield", latitude=12.97, longitude=77.75)
    mysuru = Location(district="Mysuru", station="Devaraja", latitude=12.3, longitude=76.6)

    alpha = Criminal(full_name="Alpha Path", status="at_large")
    beta = Criminal(full_name="Beta Path", status="arrested")
    charlie = Criminal(full_name="Charlie Path", status="at_large")
    delta = Criminal(full_name="Delta Path", status="at_large")
    echo = Criminal(full_name="Echo Path", status="at_large")
    isolated = Criminal(full_name="Isolated Path", status="at_large")

    victim_x = Victim(full_name="Victim X", gender="F", age=30)
    victim_y = Victim(full_name="Victim Y", gender="M", age=40)

    officer_one = Officer(badge_number="PTH-001", name="Officer One", station="Whitefield", district="Bengaluru Urban", rank="Inspector")
    officer_two = Officer(badge_number="PTH-002", name="Officer Two", station="Devaraja", district="Mysuru", rank="PSI")

    db_session.add_all([
        theft, robbery, smuggling,
        bengaluru, mysuru,
        alpha, beta, charlie, delta, echo, isolated,
        victim_x, victim_y,
        officer_one, officer_two,
    ])
    db_session.flush()

    def _case(number, category, location, occ):
        case = CrimeCase(
            case_number=number, category_id=category.id, location_id=location.id,
            occurred_at=occ, status="open", description="path finder test case",
            mo_tags=None,
        )
        db_session.add(case)
        db_session.flush()
        return case

    def _fir(number, case, complainant, filed):
        fir = FIR(
            fir_number=number, crime_case_id=case.id, complainant_name=complainant,
            sections="IPC", filed_at=filed,
        )
        db_session.add(fir)
        db_session.flush()
        return fir

    case_ab = _case("CR-PTH-0001", theft, bengaluru, datetime(2026, 6, 5, tzinfo=timezone.utc))
    fir_ab = _fir("FIR-PTH-0001", case_ab, "Victim X", datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc))
    fir_ab.investigating_officer_id = officer_one.id

    case_bc = _case("CR-PTH-0002", theft, mysuru, datetime(2026, 6, 15, tzinfo=timezone.utc))
    fir_bc = _fir("FIR-PTH-0002", case_bc, "Victim Y", datetime(2026, 6, 20, 9, 0, tzinfo=timezone.utc))

    case_cd = _case("CR-PTH-0003", robbery, mysuru, datetime(2026, 6, 25, tzinfo=timezone.utc))
    fir_cd = _fir("FIR-PTH-0003", case_cd, "Victim Y", datetime(2026, 7, 1, 11, 30, tzinfo=timezone.utc))
    fir_cd.investigating_officer_id = officer_two.id

    case_de = _case("CR-PTH-0004", robbery, mysuru, datetime(2026, 7, 2, tzinfo=timezone.utc))
    fir_de = _fir("FIR-PTH-0004", case_de, "Victim Y", datetime(2026, 7, 5, 14, 0, tzinfo=timezone.utc))

    case_ad = _case("CR-PTH-0005", robbery, bengaluru, datetime(2026, 7, 8, tzinfo=timezone.utc))
    fir_ad = _fir("FIR-PTH-0005", case_ad, "Victim X", datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc))
    fir_ad.investigating_officer_id = officer_one.id

    case_ac = _case("CR-PTH-0006", smuggling, mysuru, datetime(2026, 7, 12, tzinfo=timezone.utc))
    fir_ac = _fir("FIR-PTH-0006", case_ac, "Victim Y", datetime(2026, 7, 15, 16, 45, tzinfo=timezone.utc))

    db_session.add_all([
        FIRCriminalLink(fir_id=fir_ab.id, criminal_id=alpha.id),
        FIRCriminalLink(fir_id=fir_ab.id, criminal_id=beta.id),
        FIRVictimLink(fir_id=fir_ab.id, victim_id=victim_x.id),
        FIRCriminalLink(fir_id=fir_bc.id, criminal_id=beta.id),
        FIRCriminalLink(fir_id=fir_bc.id, criminal_id=charlie.id),
        FIRCriminalLink(fir_id=fir_cd.id, criminal_id=charlie.id),
        FIRCriminalLink(fir_id=fir_cd.id, criminal_id=delta.id),
        FIRCriminalLink(fir_id=fir_de.id, criminal_id=delta.id),
        FIRCriminalLink(fir_id=fir_de.id, criminal_id=echo.id),
        FIRCriminalLink(fir_id=fir_ad.id, criminal_id=alpha.id),
        FIRCriminalLink(fir_id=fir_ad.id, criminal_id=delta.id),
        FIRCriminalLink(fir_id=fir_ac.id, criminal_id=alpha.id),
        FIRCriminalLink(fir_id=fir_ac.id, criminal_id=charlie.id),
    ])
    db_session.commit()

    return {
        "alpha": alpha, "beta": beta, "charlie": charlie, "delta": delta,
        "echo": echo, "isolated": isolated,
        "victim_x": victim_x, "victim_y": victim_y,
        "officer_one": officer_one, "officer_two": officer_two,
        "fir_ab": fir_ab, "fir_bc": fir_bc, "fir_cd": fir_cd, "fir_de": fir_de,
        "fir_ad": fir_ad, "fir_ac": fir_ac,
        "case_ad": case_ad,
    }


def _criminal_id(d, key):
    return f"criminal-{d[key].id}"


def _victim_id(d, key):
    return f"victim-{d[key].id}"


def _officer_id(d, key):
    return f"officer-{d[key].id}"


def _path_names(body):
    return [n["name"] for n in body["nodes"]] if body.get("nodes") else []


# ---------------------------------------------------------------------------
# Path structure
# ---------------------------------------------------------------------------

def test_direct_shared_fir_connection(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "beta"),
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["distance"] == 1
    assert _path_names(body) == ["Alpha Path", "Beta Path"]
    rel = body["relationships"][0]
    assert rel["source_id"] == _criminal_id(d, "alpha")
    assert rel["target_id"] == _criminal_id(d, "beta")
    assert rel["relationship_type"] == "shared_fir"
    assert rel["fir_numbers"] == ["FIR-PTH-0001"]
    assert rel["case_numbers"] == ["CR-PTH-0001"]
    assert rel["crime_types"] == ["Theft & Burglaries"]
    assert rel["districts"] == ["Bengaluru Urban"]
    assert rel["stations"] == ["Whitefield"]
    assert rel["roles"][_criminal_id(d, "alpha")] == "accused"


def test_two_hop_connection(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "beta"),
        "target_id": _criminal_id(d, "delta"),
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["distance"] == 2
    assert len(body["relationships"]) == 2
    assert len(_path_names(body)) == 3


def test_three_hop_connection(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "beta"),
        "target_id": _criminal_id(d, "echo"),
        "max_hops": 3,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["distance"] == 3
    assert len(body["relationships"]) == 3
    assert body["summary"]["entities"] == 4
    assert body["summary"]["hops"] == 3
    assert body["summary"]["supporting_firs"] >= 3


def test_max_hops_respected(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    # B -> E needs 3 hops; bounded at 2 must not (over-)reach.
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "beta"),
        "target_id": _criminal_id(d, "echo"),
        "max_hops": 2,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is False
    assert body["message"] == "No connection found within 2 hops."
    assert body["source"]["name"] == "Beta Path"
    assert body["target"]["name"] == "Echo Path"


def test_max_hops_one_requires_shared_fir(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "beta"),
        "target_id": _criminal_id(d, "delta"),
        "max_hops": 1,
    })
    assert r.status_code == 200, r.text
    assert r.json()["found"] is False


def test_shortest_path_preferred_over_longer_chain(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    # A-D has a direct FIR (FIR-PTH-0005) even though A-B-C-D exists.
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "delta"),
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["distance"] == 1
    assert _path_names(body) == ["Alpha Path", "Delta Path"]
    assert body["relationships"][0]["fir_numbers"] == ["FIR-PTH-0005"]


def test_cycle_is_handled_without_duplication(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    # Triangle edges exist (A-B, B-C, A-C); BFS must terminate and stay shortest.
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "echo"),
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["distance"] == 2  # A-D(FIR-PTH-0005) -> D-E(FIR-PTH-0004)
    assert len({(rel["source_id"], rel["target_id"]) for rel in body["relationships"]}) == len(body["relationships"])


def test_multiple_shared_firs_aggregate_evidence(analyst_client, db_session):
    d = _build_dataset(db_session)
    # Add a second FIR where A and B appear together.
    dup_case = CrimeCase(
        case_number="CR-PTH-0007", category_id=d["fir_ab"].crime_case.category_id,
        location_id=d["fir_ab"].crime_case.location_id,
        occurred_at=datetime(2026, 6, 12, tzinfo=timezone.utc), status="open",
        description="Second shared theft", mo_tags=None,
    )
    db_session.add(dup_case)
    db_session.flush()
    dup_fir = FIR(
        fir_number="FIR-PTH-0007", crime_case_id=dup_case.id,
        complainant_name="Victim X", sections="IPC",
        filed_at=datetime(2026, 6, 13, 9, 0, tzinfo=timezone.utc),
    )
    db_session.add(dup_fir)
    db_session.flush()
    db_session.add_all([
        FIRCriminalLink(fir_id=dup_fir.id, criminal_id=d["alpha"].id),
        FIRCriminalLink(fir_id=dup_fir.id, criminal_id=d["beta"].id),
    ])
    db_session.commit()

    c, _ = analyst_client
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "beta"),
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["distance"] == 1
    rel = body["relationships"][0]
    assert sorted(rel["fir_numbers"]) == ["FIR-PTH-0001", "FIR-PTH-0007"]
    assert body["summary"]["supporting_firs"] == 2


def test_victim_and_officer_endpoints(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(PATH, params={
        "source_id": _victim_id(d, "victim_x"),
        "target_id": _officer_id(d, "officer_one"),
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["distance"] == 1
    rel = body["relationships"][0]
    assert rel["roles"][_victim_id(d, "victim_x")] == "victim"
    assert rel["roles"][_officer_id(d, "officer_one")] == "investigating officer"
    assert rel["relationship"] == "Shared FIR participation"


def test_bare_primary_key_resolution(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(PATH, params={
        "source_id": str(d["alpha"].id),
        "target_id": str(d["beta"].id),
    })
    assert r.status_code == 200, r.text
    assert r.json()["found"] is True


# ---------------------------------------------------------------------------
# Filter compatibility (issue #226 semantics reused)
# ---------------------------------------------------------------------------

def test_crime_type_filter_restricts_path(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    # Theft only: FIR-AC (smuggling) is excluded, so A-C must route via B (2 hops).
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "charlie"),
        "crime_type": "Theft",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["distance"] == 2
    fir_numbers = [f for rel in body["relationships"] for f in rel["fir_numbers"]]
    assert "FIR-PTH-0006" not in fir_numbers  # smuggling FIR never leaked


def test_district_filter_recomputes_path(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    # Unfiltered A-B is 1 hop; within Mysuru the only A-B route is A-C-B.
    r_unfiltered = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "beta"),
    })
    assert r_unfiltered.json()["distance"] == 1

    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "beta"),
        "district": "Mysuru",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["distance"] == 2
    assert body["source"]["name"] == "Alpha Path"


def test_crime_plus_district_and_semantics(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    # Robbery in Mysuru: only FIR-CD and FIR-DE match -> C-E is 2 hops.
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "charlie"),
        "target_id": _criminal_id(d, "echo"),
        "crime_type": "Robbery",
        "district": "Mysuru",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["distance"] == 2

    # A is not on any Robbery+Mysuru FIR -> neutral not-found, no leak of A-D edge.
    r2 = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "echo"),
        "crime_type": "Robbery",
        "district": "Mysuru",
    })
    assert r2.status_code == 200, r.text
    body2 = r2.json()
    assert body2["found"] is False
    assert "not part of the current filtered network" in body2["message"]


def test_fir_number_filter_restricts_to_that_fir(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "delta"),
        "fir_number": "FIR-PTH-0005",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True
    assert body["distance"] == 1
    assert body["relationships"][0]["fir_numbers"] == ["FIR-PTH-0005"]


def test_entity_not_in_filtered_network(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "isolated"),
        "target_id": _criminal_id(d, "alpha"),
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is False
    assert "not part of the current filtered network" in body["message"]


def test_empty_filtered_dataset(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "beta"),
        "district": "NONEXISTENT",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is False
    assert body["message"] == "No network relationships found for the selected filters."


# ---------------------------------------------------------------------------
# Validation & security
# ---------------------------------------------------------------------------

def test_same_entity_rejected(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "alpha"),
    })
    assert r.status_code == 400, r.text
    assert r.json()["error"]["message"] == "Please select two different entities."


def test_invalid_max_hops_rejected(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    for hops in (0, 6, 99):
        r = c.get(PATH, params={
            "source_id": _criminal_id(d, "alpha"),
            "target_id": _criminal_id(d, "beta"),
            "max_hops": hops,
        })
        assert r.status_code == 422, f"max_hops={hops} -> {r.status_code}"


def test_invalid_date_rejected(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "beta"),
        "date_from": "not-a-date",
    })
    assert r.status_code == 422, r.text


def test_missing_entity_reference_rejected(analyst_client):
    c, _ = analyst_client
    r = c.get(PATH, params={"source_id": "criminal-does-not-exist"})
    assert r.status_code == 422, r.text  # target_id required


def test_unauthorized_cannot_use_path_finder(client):
    r = client.get(PATH, params={"source_id": "criminal-1", "target_id": "criminal-2"})
    assert r.status_code in (401, 403)


def test_sql_injection_cannot_manipulate_query(analyst_client, db_session):
    d = _build_dataset(db_session)
    c, _ = analyst_client
    payload = "Alpha' OR '1'='1 --"
    r = c.get(PATH, params={
        "source_id": _criminal_id(d, "alpha"),
        "target_id": _criminal_id(d, "beta"),
        "criminal_name": payload,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    # Parameterised matching treats the payload as a literal substring -> no FIR match.
    assert body["found"] is False
    assert body["message"] == "No network relationships found for the selected filters."
    assert "error" not in str(body).lower() and "traceback" not in str(body).lower()