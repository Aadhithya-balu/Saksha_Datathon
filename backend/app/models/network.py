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


class RelationshipProvenance(str, Enum):
    DIRECT_DATABASE = "DIRECT_DATABASE"
    ANALYTICAL_INFERENCE = "ANALYTICAL_INFERENCE"
    DEMO_SEED = "DEMO_SEED"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    POTENTIAL = "POTENTIAL"
    UNVERIFIED = "UNVERIFIED"
    DEMO = "DEMO"


class RelationshipType(str, Enum):
    PERSON_CASE = "PERSON_CASE"
    PERSON_LOCATION = "PERSON_LOCATION"
    CASE_LOCATION = "CASE_LOCATION"
    PERSON_INVESTIGATION = "PERSON_INVESTIGATION"
    PERSON_VICTIM = "PERSON_VICTIM"
    SHARED_CASE = "SHARED_CASE"
    SHARED_LOCATION = "SHARED_LOCATION"
    SHARED_MO = "SHARED_MO"
    GANG_ASSOCIATION = "GANG_ASSOCIATION"
    OTHER = "OTHER"


class NetworkEdge(BaseModel):
    source: str
    target: str
    relationship: str
    weight: float = 1.0
    first_seen: str | None = None
    last_seen: str | None = None
    # Issue #159: Provenance and evidence verification metadata
    provenance: str = "DIRECT_DATABASE"
    verification_status: str = "VERIFIED"
    relationship_type: str = "OTHER"
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float | None = 1.0
    confidence_level: str = "HIGH"
    is_demo_derived: bool = False
    operational_warning: str | None = None


class NetworkGraphResponse(BaseModel):
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    total_nodes: int
    total_edges: int
    is_neo4j_backed: bool = False
    # Issue #144 gap 132.4: provenance transparency about demo-seeded content.
    seed_node_count: int = 0
    dataset_scope: str = "live_records"  # or "contains_seed_demo_records"
    # Issue #159: Granular provenance summary
    provenance_summary: dict[str, int] = Field(default_factory=dict)
    # Issue #166: Enhanced graph metadata
    entity_counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    confidence_summary: dict[str, int] = Field(default_factory=dict)


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


class NetworkPathNode(BaseModel):
    id: str
    name: str
    category: NetworkNodeCategory
    riskScore: float = 0.0
    casesCount: int = 0
    district: str | None = None
    status: str | None = None
    isSeed: bool = False


class NetworkPathRelationship(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str = "shared_fir"
    relationship: str = "Shared FIR participation"
    # Evidence: every FIR (and its case context) that supports this segment.
    fir_numbers: list[str] = Field(default_factory=list)
    case_numbers: list[str] = Field(default_factory=list)
    crime_types: list[str] = Field(default_factory=list)
    districts: list[str] = Field(default_factory=list)
    stations: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    # role each endpoint played in the supporting FIRs, e.g. "accused"/"victim".
    roles: dict[str, str] = Field(default_factory=dict)


class NetworkPathResponse(BaseModel):
    found: bool
    distance: int = 0
    source: NetworkPathNode | None = None
    target: NetworkPathNode | None = None
    nodes: list[NetworkPathNode] = Field(default_factory=list)
    relationships: list[NetworkPathRelationship] = Field(default_factory=list)
    message: str
    explanation: str = ""
    # Summary metrics: entities, hops, supporting_firs, crime_types, districts.
    summary: dict[str, int] = Field(default_factory=dict)


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
