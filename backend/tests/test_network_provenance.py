"""Tests for Issue #166: Network Graph Provenance, Warnings, and Entity Counts."""
import pytest
from app.models.network import (
    NetworkNode,
    NetworkEdge,
    NetworkNodeCategory,
    NetworkGraphResponse,
)


class TestNetworkGraphResponse:
    def test_default_values(self):
        resp = NetworkGraphResponse(nodes=[], edges=[], total_nodes=0, total_edges=0)
        assert resp.entity_counts == {}
        assert resp.warnings == []
        assert resp.confidence_summary == {}

    def test_entity_counts_populated(self):
        nodes = [
            NetworkNode(id="c1", name="X", category=NetworkNodeCategory.SUSPECT),
            NetworkNode(id="c2", name="Y", category=NetworkNodeCategory.SUSPECT),
            NetworkNode(id="v1", name="Z", category=NetworkNodeCategory.VICTIM),
        ]
        resp = NetworkGraphResponse(
            nodes=nodes,
            edges=[],
            total_nodes=3,
            total_edges=0,
            entity_counts={"suspect": 2, "victim": 1},
        )
        assert resp.entity_counts["suspect"] == 2
        assert resp.entity_counts["victim"] == 1

    def test_warnings_for_demo_data(self):
        resp = NetworkGraphResponse(
            nodes=[],
            edges=[],
            total_nodes=0,
            total_edges=0,
            warnings=["Graph contains 3 DEMO/seed-derived relationship(s)."],
        )
        assert len(resp.warnings) == 1
        assert "DEMO" in resp.warnings[0]


class TestGraphResponseFunction:
    """Tests for the _graph_response helper in network_service."""

    def _make_node(self, nid: str, category: NetworkNodeCategory = NetworkNodeCategory.SUSPECT, is_seed: bool = False) -> NetworkNode:
        return NetworkNode(
            id=nid,
            name=f"Node {nid}",
            category=category,
            isSeed=is_seed,
        )

    def _make_edge(self, source: str, target: str, **kwargs) -> NetworkEdge:
        defaults = {
            "source": source,
            "target": target,
            "relationship": "KNOWS",
        }
        defaults.update(kwargs)
        return NetworkEdge(**defaults)

    def test_empty_graph(self):
        from app.services.network.network_service import _graph_response
        resp = _graph_response([], [], is_neo4j_backed=False)
        assert resp.total_nodes == 0
        assert resp.total_edges == 0
        assert resp.entity_counts == {}

    def test_entity_counts_in_response(self):
        from app.services.network.network_service import _graph_response
        nodes = [
            self._make_node("c1", NetworkNodeCategory.SUSPECT),
            self._make_node("v1", NetworkNodeCategory.VICTIM),
        ]
        edges = [self._make_edge("c1", "v1")]
        resp = _graph_response(nodes, edges, is_neo4j_backed=False)
        assert resp.entity_counts.get("suspect", 0) == 1
        assert resp.entity_counts.get("victim", 0) == 1

    def test_demo_warning_present(self):
        from app.services.network.network_service import _graph_response
        nodes = [self._make_node("c1")]
        edges = [self._make_edge("c1", "c1", provenance="DEMO_SEED", is_demo_derived=True)]
        resp = _graph_response(nodes, edges, is_neo4j_backed=False)
        assert any("DEMO" in w for w in resp.warnings)

    def test_exclude_demo_filter(self):
        from app.services.network.network_service import _graph_response
        nodes = [
            self._make_node("c1", is_seed=True),
            self._make_node("c2", is_seed=False),
        ]
        edges = [
            self._make_edge("c1", "c1", is_demo_derived=True),
            self._make_edge("c2", "c2", is_demo_derived=False),
        ]
        resp = _graph_response(nodes, edges, is_neo4j_backed=False, exclude_demo=True)
        node_ids = {n.id for n in resp.nodes}
        assert "c1" not in node_ids
        assert "c2" in node_ids

    def test_confidence_summary(self):
        from app.services.network.network_service import _graph_response
        nodes = [self._make_node("c1")]
        edges = [
            self._make_edge("c1", "c1", confidence_level="HIGH"),
            self._make_edge("c1", "c1", confidence_level="LOW"),
        ]
        resp = _graph_response(nodes, edges, is_neo4j_backed=False)
        assert resp.confidence_summary["HIGH"] == 1
        assert resp.confidence_summary["LOW"] == 1

    def test_provenance_summary_populated(self):
        from app.services.network.network_service import _graph_response
        nodes = [self._make_node("c1")]
        edges = [
            self._make_edge("c1", "c1", verification_status="VERIFIED"),
            self._make_edge("c1", "c1", relationship="SHARED_CASE", verification_status="POTENTIAL"),
        ]
        resp = _graph_response(nodes, edges, is_neo4j_backed=False)
        assert "verified_relationships" in resp.provenance_summary
        assert "potential_relationships" in resp.provenance_summary

    def test_mixed_provenance_warning(self):
        from app.services.network.network_service import _graph_response
        nodes = [self._make_node("c1")]
        edges = [
            self._make_edge("c1", "c1", provenance="MIXED"),
        ]
        resp = _graph_response(nodes, edges, is_neo4j_backed=False)
        assert any("mixed" in w.lower() for w in resp.warnings)


class TestNetworkSearchEndpoint:
    @pytest.fixture(autouse=True)
    def _setup_auth(self, client, db_session):
        """Create a user and seed minimal data for each test in this class."""
        from app.core.security import hash_password
        from app.models.criminal import Criminal
        from app.models.fir import FIR
        from app.models.officer import Officer
        from app.models.victim import Victim
        from app.models.role import Role
        from app.models.user import User
        from app.models.crime_category import CrimeCategory
        from app.models.location import Location
        from app.models.crime import CrimeCase

        role = Role(name="crime_analyst", description="test role")
        db_session.add(role)
        db_session.flush()

        user = User(
            username="search-tester",
            email="search@test.invalid",
            full_name="Search Tester",
            hashed_password=hash_password("TestPass#123"),
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()

        # Seed data for search
        cat = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="high")
        db_session.add(cat)
        db_session.flush()

        loc = Location(district="Bengaluru Urban", station="Whitefield", latitude=12.96, longitude=77.72)
        db_session.add(loc)
        db_session.flush()

        from datetime import datetime, timezone

        case = CrimeCase(
            case_number="CR-2026-TEST-001",
            category_id=cat.id,
            location_id=loc.id,
            occurred_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
            status="open",
            priority="high",
            description="Test case for search endpoint",
        )
        db_session.add(case)
        db_session.flush()

        criminal = Criminal(full_name="Ramu Swamy", aliases="The Ghost", status="active")
        db_session.add(criminal)
        db_session.flush()

        victim = Victim(full_name="Jane Doe", contact_number="9999999999", address="123 Test St", gender="female", age=30)
        db_session.add(victim)
        db_session.flush()

        officer = Officer(badge_number="BDG-9999", name="Inspector Testwala", rank="Inspector", station="Whitefield", status="active")
        db_session.add(officer)
        db_session.flush()

        fir = FIR(fir_number="FIR-TEST-001", crime_case_id=case.id, complainant_name="Jane Doe", sections="IPC 379")
        db_session.add(fir)
        db_session.flush()

        db_session.commit()

        resp = client.post("/api/v2/auth/login", json={"username": "search-tester", "password": "TestPass#123"})
        assert resp.status_code == 200
        self.headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def test_search_returns_criminals(self, client):
        resp = client.get("/api/v2/network/search?q=Ramu", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert data["query"] == "Ramu"
        assert any(r["type"] == "criminal" for r in data["results"])

    def test_search_returns_victims(self, client):
        resp = client.get("/api/v2/network/search?q=Jane", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert any(r["type"] == "victim" for r in data["results"])

    def test_search_returns_firs(self, client):
        resp = client.get("/api/v2/network/search?q=FIR", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert any(r["type"] == "case" for r in data["results"])

    def test_search_returns_cases(self, client):
        resp = client.get("/api/v2/network/search?q=CR-2026", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert any(r["type"] == "case" for r in data["results"])

    def test_search_returns_officers(self, client):
        resp = client.get("/api/v2/network/search?q=Inspector", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert any(r["type"] == "officer" for r in data["results"])

    def test_search_empty_query_rejected(self, client):
        resp = client.get("/api/v2/network/search?q=", headers=self.headers)
        assert resp.status_code == 422

    def test_search_no_results(self, client):
        resp = client.get("/api/v2/network/search?q=ZZZZNOTEXIST", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert data["total"] == 0

    def test_search_limit_applied(self, client):
        resp = client.get("/api/v2/network/search?q=Ramu&limit=1", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) <= 1
