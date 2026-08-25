"""Scenarios 3, 4, 11 acceptance: network intelligence end-to-end.

Verifies the SQL-backed graph actually contains the seeded relationships,
that DEMO provenance is preserved and surfaced, and that partial/missing
records are handled without fabrication.
"""
import pytest

pytestmark = pytest.mark.acceptance

NET = "/api/v2/network"


def _node_ids(body):
    return {n["id"] for n in body["nodes"]}


def test_full_graph_contains_seeded_relationships(client, crime_dataset, analyst_headers):
    r = client.get(f"{NET}/graph", headers=analyst_headers)
    assert r.status_code == 200, r.text
    body = r.json()

    # Nodes: 3 criminals + 1 victim + 1 officer + 2 FIR-case nodes + 2 locations.
    assert body["total_nodes"] >= 9
    assert body["total_nodes"] == len(body["nodes"])
    assert body["total_edges"] == len(body["edges"])
    names = {n["name"] for n in body["nodes"]}
    for expected in ("Accused Alpha", "Accused Beta", "Lone Offender Gamma", "Victim Vega",
                     "FIR #FIR-ACC-0001", "FIR #FIR-ACC-0002"):
        assert expected in names

    categories = {n["category"] for n in body["nodes"]}
    assert {"case", "location", "victim"} <= categories

    # Edges must encode the real FIR links (Alpha & Beta co-accused on FIR-ACC-0001).
    relationships = {(e["source"], e["target"], e["relationship"]) for e in body["edges"]}
    alpha_id = f"criminal-{crime_dataset['criminals']['alpha'].id}"
    beta_id = f"criminal-{crime_dataset['criminals']['beta'].id}"
    case_one_id = f"case-{crime_dataset['firs']['one'].id}"

    assert any(s == alpha_id and t == case_one_id for s, t, _ in relationships), (
        "Alpha -> FIR edge missing"
    )
    assert any(s == beta_id and t == case_one_id for s, t, _ in relationships), (
        "Beta -> FIR edge missing"
    )
    co_accused = any(
        {s, t} == {alpha_id, beta_id} and rel.startswith("Co-accused")
        for s, t, rel in relationships
    )
    assert co_accused, "co-accused association edge missing"


def test_person_graph_centers_on_criminal_with_case_link(client, crime_dataset, analyst_headers):
    alpha = crime_dataset["criminals"]["alpha"]
    r = client.get(f"{NET}/person/criminal-{alpha.id}", headers=analyst_headers)
    assert r.status_code == 200
    body = r.json()
    ids = _node_ids(body)
    assert f"criminal-{alpha.id}" in ids
    assert f"case-{crime_dataset['firs']['one'].id}" in ids


def test_demo_provenance_surfaced_in_graph_metadata(client, crime_dataset, analyst_headers):
    """Scenario 11: the API reports seed/demo content instead of hiding it.

    The Mysuru FIR belongs to a case whose DB row carries
    dataset_provenance="demo"; the graph must not present it as LIVE intel.
    """
    r = client.get(f"{NET}/graph", headers=analyst_headers)
    assert r.status_code == 200
    body = r.json()

    assert isinstance(body["seed_node_count"], int)
    assert body["dataset_scope"] in ("live_records", "contains_seed_demo_records")

    demo_case_id = f"case-{crime_dataset['firs']['two'].id}"
    assert demo_case_id in _node_ids(body), "demo-provenanced FIR missing from graph"
    demo_node = next(n for n in body["nodes"] if n["id"] == demo_case_id)
    assert demo_node["isSeed"] is True, "demo-provenanced record presented as LIVE"

    live_case_id = f"case-{crime_dataset['firs']['one'].id}"
    live_node = next(n for n in body["nodes"] if n["id"] == live_case_id)
    assert live_node["isSeed"] is False

    assert body["seed_node_count"] >= 1
    assert body["dataset_scope"] == "contains_seed_demo_records"


def test_shortest_path_between_co_accused_found(client, crime_dataset, analyst_headers):
    payload = {
        "source_id": f"criminal-{crime_dataset['criminals']['alpha'].id}",
        "target_id": f"criminal-{crime_dataset['criminals']['beta'].id}",
        "max_depth": 5,
    }
    r = client.post(f"{NET}/shortest-path", json=payload, headers=analyst_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True
    assert body["distance"] >= 1
    path_names = {n["name"] for n in body["path_nodes"]}
    assert {"Accused Alpha", "Accused Beta"} <= path_names


def test_unknown_entity_returns_honest_empty_result(client, crime_dataset, analyst_headers):
    r = client.get(f"{NET}/person/criminal-does-not-exist", headers=analyst_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total_nodes"] == 0 and body["total_nodes"] == len(body["nodes"])

    path = client.post(
        f"{NET}/shortest-path",
        json={"source_id": "ghost-a", "target_id": "ghost-b"},
        headers=analyst_headers,
    )
    assert path.status_code == 200
    assert path.json()["found"] is False


def test_partial_record_handled_without_fabrication(client, db_session, crime_dataset, analyst_headers):
    """Scenario 4: a FIR whose linked criminal row vanishes must not crash the
    graph nor invent replacement nodes."""
    import uuid as uuid_mod

    from app.models.fir import FIRCriminalLink

    orphan = FIRCriminalLink(
        fir_id=crime_dataset["firs"]["one"].id,
        criminal_id=uuid_mod.uuid4(),  # no matching criminals row
        role="accused",
    )
    db_session.add(orphan)
    db_session.commit()

    r = client.get(f"{NET}/graph", headers=analyst_headers)
    assert r.status_code == 200
    body = r.json()
    # The dangling reference produced no fabricated node.
    for node in body["nodes"]:
        assert not node["id"].startswith("node-")

    person = client.get(
        f"{NET}/person/criminal-{crime_dataset['criminals']['beta'].id}",
        headers=analyst_headers,
    )
    assert person.status_code == 200


def test_gang_view_derived_from_real_affiliations(client, crime_dataset, analyst_headers):
    r = client.get(f"{NET}/gangs", headers=analyst_headers)
    assert r.status_code == 200
    gangs = {g["name"]: g for g in r.json()}
    assert "Acc-Gang" in gangs
    members = {m["name"] for m in gangs["Acc-Gang"]["members"]}
    assert members == {"Accused Alpha", "Accused Beta"}
