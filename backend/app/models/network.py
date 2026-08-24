"""
Pydantic schemas and data models for Graph-Based Criminal Intelligence,
Neo4j Graph integration, Link Analysis, Gang Networks, and Path Analysis.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class NetworkNodeCategory(str, Enum):
    SUSPECT = "suspect"
    OFFENDER = "offender"
    CASE = "case"
    LOCATION = "location"
    VICTIM = "victim"
    GANG = "gang"
    VEHICLE = "vehicle"
    WEAPON = "weapon"
    OFFICER = "officer"


class NetworkNode(BaseModel):
    id: str
    name: str
    category: NetworkNodeCategory
    riskScore: float = Field(default=50.0, description="Risk assessment score (0-100)")
    details: str = ""
    casesCount: int = 0
    phone: str | None = None
    gangAffiliation: str | None = None
    status: str | None = None
    district: str | None = None
    date: str | None = None
    lat: float | None = None
    lng: float | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
    # Issue #144 gap 132.4: True when this record originates from the bundled
    # demo seed dataset rather than user-entered/live intelligence.
    isSeed: bool = False


class NetworkEdge(BaseModel):
    source: str
    target: str
    relationship: str
    weight: float = 1.0
    first_seen: str | None = None
    last_seen: str | None = None


class NetworkGraphResponse(BaseModel):
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    total_nodes: int
    total_edges: int
    is_neo4j_backed: bool = False
    # Issue #144 gap 132.4: provenance transparency about demo-seeded content.
    seed_node_count: int = 0
    dataset_scope: str = "live_records"  # or "contains_seed_demo_records"


class GangHierarchyMember(BaseModel):
    id: str
    name: str
    role: str  # Leader, Lieutenant, Enforcer, Operative, Mule
    rank_level: int  # 1 (Leader) to 5 (Mule)
    riskScore: float
    status: str
    casesCount: int
    isSeed: bool = False


class GangNetworkSummary(BaseModel):
    gang_id: str
    name: str
    leader_name: str
    leader_id: str | None = None
    active_members: int
    risk_level: str  # Critical, High, Moderate
    territory: str
    primary_racket: str
    members: list[GangHierarchyMember]
    relationships: list[NetworkEdge]
    # Issue #144 gap 132.4: True when all member offenders come from the
    # bundled demo seed dataset.
    is_demo_derived: bool = False


class ShortestPathRequest(BaseModel):
    source_id: str
    target_id: str
    max_depth: int = Field(default=5, ge=1, le=10)


class ShortestPathResponse(BaseModel):
    found: bool
    distance: int
    path_nodes: list[NetworkNode]
    path_edges: list[NetworkEdge]
    explanation: str


class CentralityMetric(BaseModel):
    node_id: str
    node_name: str
    category: str
    degree_centrality: float
    betweenness_score: float
    is_bridge_node: bool
    riskScore: float


class LinkAnalysisResponse(BaseModel):
    graph_density: float
    total_clusters: int
    top_broker_nodes: list[CentralityMetric]
    high_impact_nodes: list[CentralityMetric]
    bridge_nodes: list[CentralityMetric]


class TimelineGraphFilter(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    entity_id: str | None = None


class AIGraphInsight(BaseModel):
    id: str
    insight_type: str  # "broker_identification", "syndicate_cluster", "cross_jurisdiction_link", "high_risk_hub"
    title: str
    description: str
    threat_level: str  # "CRITICAL", "HIGH", "MEDIUM"
    target_node_ids: list[str]
    recommendation: str
    timestamp: str
