"""Schemas for the Identity Resolution & Proxy Detection Engine (issue #225).

All vocabulary is deliberately conservative: the platform only ever describes
*possible* / *probable* relationships, and never auto-confirms identity. Every
score is accompanied by an explicit, explainable breakdown and its sources.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Relationship schemas
# ---------------------------------------------------------------------------
class IdentityEntityRef(BaseModel):
    entity_type: str
    entity_id: uuid.UUID | str
    name: str | None = None
    subtype: str | None = None


class IdentityEvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    evidence_group: str
    signal_type: str
    weight_delta: float
    confidence: float | None = None
    severity: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    source_label: str | None = None
    description: str
    observed_at: datetime | None = None
    time_range: str | None = None
    is_counter_evidence: bool


class IdentityConflictOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    attribute: str
    value_a: str
    value_b: str
    severity: str
    explanation: str
    status: str


class IdentityRelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_entity_type: str
    source_entity_id: uuid.UUID
    target_entity_type: str
    target_entity_id: uuid.UUID
    relationship_type: str
    assessment: str
    confidence: float
    confidence_breakdown: dict | None = None
    evidence_summary: dict | None = None
    status: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    reviewed_by_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    review_decision: str | None = None
    review_note: str | None = None
    created_at: datetime


class IdentityRelationshipDetail(IdentityRelationshipOut):
    source: IdentityEntityRef | None = None
    target: IdentityEntityRef | None = None
    evidence: list[IdentityEvidenceOut] = []
    conflicts: list[IdentityConflictOut] = []
    counter_evidence: list[IdentityEvidenceOut] = []


class IdentityRelationshipList(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    results: list[IdentityRelationshipOut] = []
    relationships: list[IdentityRelationshipDetail] = []


# ---------------------------------------------------------------------------
# Identity review actions
# ---------------------------------------------------------------------------
class IdentityReviewRequest(BaseModel):
    decision: str = Field(..., description="confirm_same|reject|possible_proxy|associated|alias|data_error|dismiss|investigate")
    note: str | None = None


# ---------------------------------------------------------------------------
# Search / resolution
# ---------------------------------------------------------------------------
class IdentityCandidate(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    name: str
    matched_block: str | None = None
    score: float = 0.0
    relationship_type: str | None = None
    relationship_id: uuid.UUID | None = None


class IdentitySearchResponse(BaseModel):
    query: str
    exact: list[IdentityCandidate] = []
    probable: list[IdentityCandidate] = []
    possible: list[IdentityCandidate] = []
    method: str


# ---------------------------------------------------------------------------
# Integrity alerts
# ---------------------------------------------------------------------------
class IntegrityAlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    alert_type: str
    severity: str
    entity_a_type: str | None = None
    entity_a_id: uuid.UUID | None = None
    entity_b_type: str | None = None
    entity_b_id: uuid.UUID | None = None
    identifier_type: str | None = None
    value_hash: str | None = None
    display_value: str | None = None
    confidence: float
    description: str
    observation_count: int
    status: str
    source_summary: dict | None = None
    created_at: datetime


class IntegrityAlertList(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    results: list[IntegrityAlertOut] = []
    alerts: list[IntegrityAlertOut] = []


class IntegritySummary(BaseModel):
    records_analyzed: int
    possible_duplicates: int
    identity_conflicts: int
    identifier_reuse_alerts: int
    possible_aliases: int
    possible_proxy_relationships: int
    critical_reviews: int
    open_reviews: int


class IntegritySignature(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    name: str
    hashes: list[str] = []
    display_values: list[str] = []


class IdentifierReuse(BaseModel):
    identifier_type: str
    value_hash: str
    display_value: str
    entities: list[IdentityEntityRef]
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    confidence: float
    explanation: str


# ---------------------------------------------------------------------------
# Proxy pattern alerts
# ---------------------------------------------------------------------------
class ProxyEvidenceItem(BaseModel):
    evidence_category: str
    description: str
    source_type: str | None = None
    source_id: str | None = None
    source_label: str | None = None
    observed_at: datetime | None = None
    weight: float = 0.0
    support: bool = True


class ProxyPatternOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    rule_id: str
    rule_version: str
    pattern: str
    severity: str
    confidence: float
    assessment: str
    entities: list
    evidence: list
    counter_evidence: list
    time_window: dict | None = None
    explanation: str
    possible_explanations: list
    observation_count: int
    status: str
    reviewed_by_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    review_decision: str | None = None
    review_note: str | None = None
    created_at: datetime


class ProxyPatternList(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    results: list[ProxyPatternOut] = []
    patterns: list[ProxyPatternOut] = []


class ProxyPatternDetail(ProxyPatternOut):
    evidence_items: list[ProxyEvidenceItem] = []
    counter_evidence_items: list[ProxyEvidenceItem] = []


class ProxyReviewRequest(BaseModel):
    decision: str = Field(..., description="confirm|reject|same_person|alias|proxy|data_error|dismiss|investigate")
    note: str | None = None


# ---------------------------------------------------------------------------
# Identity graph
# ---------------------------------------------------------------------------
class IdentityGraphNode(BaseModel):
    id: str
    entity_type: str
    entity_id: uuid.UUID
    name: str
    subtype: str | None = None
    aliases: list[str] = []
    identifiers: list[dict] = []
    risk_proxy_cluster: bool = False


class IdentityGraphEdge(BaseModel):
    source: str
    target: str
    relationship_type: str
    relationship_id: uuid.UUID | None = None
    confidence: float = 0.0
    assessment: str
    evidence_count: int = 0
    status: str
    verification_status: str = "unverified"


class IdentityGraphResponse(BaseModel):
    nodes: list[IdentityGraphNode] = []
    edges: list[IdentityGraphEdge] = []
    is_demo_derived: bool = False


# ---------------------------------------------------------------------------
# Rules engine catalog
# ---------------------------------------------------------------------------
class RuleThresholds(BaseModel):
    min_shared_contact_count: int = 2
    handoff_window_days: int = 365
    short_window_days: int = 14
    repeated_cooccurrence_min: int = 2
    repeated_location_overlap_min: int = 3
    vehicle_rotation_min: int = 3
    composite_min_categories: int = 3
    proxy_bridge_min: int = 2


class RuleDefinition(BaseModel):
    rule_id: str
    name: str
    pattern: str
    default_severity: str
    description: str
    trigger_condition: str
    possible_explanations: list[str] = []


class RulesCatalogResponse(BaseModel):
    rules: list[RuleDefinition] = []
    thresholds: RuleThresholds = RuleThresholds()