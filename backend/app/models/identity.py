"""
Identity Resolution & Proxy Detection models (issue #225).

These tables support the Identity Resolution / Proxy Relationship Engine:
candidate matching between existing person records (criminals/victims),
explainable confidence scoring, alias evolution, temporal identifier reuse,
identity conflicts, the data-integrity dashboard, and the audit-able proxy
pattern rule engine.

Design rules (issue #225):
  * No existing person record is duplicated here — entities are referenced
    polymorphically via ``entity_type`` + ``entity_id``.
  * Sensitive identifiers are stored hashed; only masked display values are kept
    in the identity layer to minimise PII duplication.
  * Every relationship / alert carries provenance, an explainable score
    breakdown, counter-evidence and reviewer state. Nothing is auto-confirmed.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

# Canonical person kinds the identity engine understands. Each refers to an
# existing registry table (criminals / victims) — never a new person row.
ENTITY_KIND_CRIMINAL = "criminal"
ENTITY_KIND_VICTIM = "victim"
ENTITY_KINDS = (ENTITY_KIND_CRIMINAL, ENTITY_KIND_VICTIM)

# Relationship / assessment vocabulary (issue #225 section 1). The system never
# declares a *confirmed* identity unless an investigator explicitly confirms it.
REL_SAME_PERSON_PROBABLE = "SAME_PERSON_PROBABLE"
REL_SAME_PERSON_POSSIBLE = "SAME_PERSON_POSSIBLE"
REL_ALIAS_OF = "ALIAS_OF"
REL_SHARES_PHONE = "SHARES_PHONE"
REL_SHARES_DEVICE = "SHARES_DEVICE"
REL_SHARES_ADDRESS = "SHARES_ADDRESS"
REL_SHARES_VEHICLE = "SHARES_VEHICLE"
REL_SHARES_CONTACT = "SHARES_CONTACT"
REL_POSSIBLE_PROXY = "POSSIBLE_PROXY"
REL_ASSOCIATED_WITH = "ASSOCIATED_WITH"
REL_CONFLICTING_IDENTITY = "CONFLICTING_IDENTITY"

RELATIONSHIP_TYPES = (
    REL_SAME_PERSON_PROBABLE,
    REL_SAME_PERSON_POSSIBLE,
    REL_ALIAS_OF,
    REL_SHARES_PHONE,
    REL_SHARES_DEVICE,
    REL_SHARES_ADDRESS,
    REL_SHARES_VEHICLE,
    REL_SHARES_CONTACT,
    REL_POSSIBLE_PROXY,
    REL_ASSOCIATED_WITH,
    REL_CONFLICTING_IDENTITY,
)

REL_STATUS_OPEN = "open"
REL_STATUS_IN_REVIEW = "in_review"
REL_STATUS_CONFIRMED_SAME = "confirmed_same"
REL_STATUS_REJECTED = "rejected"
REL_STATUS_DISMISSED = "dismissed"
REL_STATUS_CONFIRMED_ASSOCIATION = "confirmed_association"
REL_STATUS_MARKED_PROXY = "marked_proxy"
REL_STATUS_MARKED_ALIAS = "marked_alias"
REL_STATUS_MARKED_DATA_ERROR = "marked_data_error"

RELATIONSHIP_STATUSES = (
    REL_STATUS_OPEN,
    REL_STATUS_IN_REVIEW,
    REL_STATUS_CONFIRMED_SAME,
    REL_STATUS_REJECTED,
    REL_STATUS_DISMISSED,
    REL_STATUS_CONFIRMED_ASSOCIATION,
    REL_STATUS_MARKED_PROXY,
    REL_STATUS_MARKED_ALIAS,
    REL_STATUS_MARKED_DATA_ERROR,
)

ASSESSMENT_PROBABLE_IDENTITY = "PROBABLE_IDENTITY_MATCH"
ASSESSMENT_POSSIBLE_IDENTITY = "POSSIBLE_IDENTITY_MATCH"
ASSESSMENT_POSSIBLE_ASSOCIATED = "POSSIBLE_ASSOCIATED"
ASSESSMENT_POSSIBLE_PROXY = "POSSIBLE_PROXY_RELATIONSHIP"
ASSESSMENT_IDENTIFIER_SHARING = "SHARED_IDENTIFIER"
ASSESSMENT_IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
ASSESSMENT_REQUIRES_REVIEW = "REQUIRES_INVESTIGATOR_REVIEW"

EVIDENCE_GROUP_BIOGRAPHICAL = "biographical"
EVIDENCE_GROUP_CONTACT = "contact"
EVIDENCE_GROUP_LOCATION = "location"
EVIDENCE_GROUP_DEVICE = "device"
EVIDENCE_GROUP_VEHICLE = "vehicle"
EVIDENCE_GROUP_CASE_HISTORY = "case_history"
EVIDENCE_GROUP_NETWORK = "network"

EVIDENCE_GROUPS = (
    EVIDENCE_GROUP_BIOGRAPHICAL,
    EVIDENCE_GROUP_CONTACT,
    EVIDENCE_GROUP_LOCATION,
    EVIDENCE_GROUP_DEVICE,
    EVIDENCE_GROUP_VEHICLE,
    EVIDENCE_GROUP_CASE_HISTORY,
    EVIDENCE_GROUP_NETWORK,
)

ALERT_DUPLICATE = "possible_duplicate"
ALERT_CONFLICT = "identity_conflict"
ALERT_IDENTIFIER_REUSE = "identifier_reuse"
ALERT_ALIAS = "possible_alias"
ALERT_PROXY = "possible_proxy"
ALERT_DUPLICATE_RECORD = "possible_duplicate_record"

ALERT_TYPES = (
    ALERT_DUPLICATE,
    ALERT_CONFLICT,
    ALERT_IDENTIFIER_REUSE,
    ALERT_ALIAS,
    ALERT_PROXY,
    ALERT_DUPLICATE_RECORD,
)

SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"

AUDIT_MATCH_PROPOSED = "MATCH_PROPOSED"
AUDIT_MATCH_CONFIRMED = "MATCH_CONFIRMED"
AUDIT_MATCH_REJECTED = "MATCH_REJECTED"
AUDIT_PROXY_PROPOSED = "PROXY_RELATIONSHIP_PROPOSED"
AUDIT_PROXY_CONFIRMED = "PROXY_RELATIONSHIP_CONFIRMED"
AUDIT_ALIAS_DETECTED = "ALIAS_DETECTED"
AUDIT_ALIAS_CONFIRMED = "ALIAS_CONFIRMED"
AUDIT_IDENTIFIER_REUSE = "IDENTIFIER_REUSE_DETECTED"
AUDIT_CONFLICT_DETECTED = "IDENTITY_CONFLICT_DETECTED"


class IdentityRelationship(UUIDPKMixin, Base, TimestampMixin):
    """Scored, explainable candidate relationship between two person records.

    A single primary relationship row per unordered pair. Supporting signals
    (shared phone, shared vehicle, ...) are captured as ``IdentityEvidence``
    rows and individual integrity alerts rather than separate relationship rows.
    """

    __tablename__ = "identity_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_entity_type",
            "source_entity_id",
            "target_entity_type",
            "target_entity_id",
            name="uq_identity_relationship_pair",
        ),
    )

    source_entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    target_entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)

    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    assessment: Mapped[str] = mapped_column(String(60), nullable=False, default=ASSESSMENT_REQUIRES_REVIEW)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    evidence_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default=REL_STATUS_OPEN, index=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class IdentityAlias(UUIDPKMixin, Base, TimestampMixin):
    """Detected alias / name variation for a person record.

    Original source values are never overwritten — aliases always preserve the
    source label they were derived from.
    """

    __tablename__ = "identity_aliases"

    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_type: Mapped[str] = mapped_column(String(30), nullable=False, default="known_alias")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IdentityIdentifier(UUIDPKMixin, Base, TimestampMixin):
    """A hashed identifier attributed to a person record over a time window.

    Only the hash and a masked display value are persisted in this table so the
    engine can group/compare identifiers without duplicating raw PII.
    """

    __tablename__ = "identity_identifiers"

    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    identifier_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # phone/email/vehicle/...
    value_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_value: Mapped[str] = mapped_column(String(100), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)


class IdentityEvidence(UUIDPKMixin, Base, TimestampMixin):
    """One explainable evidence item behind an identity relationship."""

    __tablename__ = "identity_evidence"

    relationship_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("identity_relationships.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_group: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    weight_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_range: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_counter_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class IdentityConflict(UUIDPKMixin, Base, TimestampMixin):
    """Contradiction between two records that share one or more identity signals.

    Conflicts are surfaced honestly rather than hidden behind a match score.
    """

    __tablename__ = "identity_conflicts"

    relationship_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("identity_relationships.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source_entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    target_entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    attribute: Mapped[str] = mapped_column(String(30), nullable=False)  # dob/address/name/gender/age
    value_a: Mapped[str] = mapped_column(Text, nullable=False)
    value_b: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default=SEVERITY_LOW)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open", index=True)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IntegrityAlert(UUIDPKMixin, Base, TimestampMixin):
    """Data-integrity dashboard alert (possible duplicate / conflict / reuse...).

    ``grouping_key`` lets repeated observations collapse into a single alert
    instead of flooding the operator.
    """

    __tablename__ = "integrity_alerts"

    alert_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default=SEVERITY_MEDIUM)
    entity_a_type: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    entity_a_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    entity_b_type: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    entity_b_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    identifier_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    value_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    display_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    grouping_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open", index=True)
    source_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProxyPattern(UUIDPKMixin, Base, TimestampMixin):
    """Output of a proxy-pattern detection rule (PROXY-001..PROXY-020).

    Always an investigative lead — never a confirmed accusation. Status is only
    changed by explicit investigator review.
    """

    __tablename__ = "proxy_patterns"

    rule_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    rule_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    pattern: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default=SEVERITY_MEDIUM)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    assessment: Mapped[str] = mapped_column(String(60), nullable=False, default=ASSESSMENT_REQUIRES_REVIEW)
    entities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    counter_evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    time_window: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    possible_explanations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    grouping_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open", index=True)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProxyPatternEvidence(UUIDPKMixin, Base, TimestampMixin):
    """Expandable observation behind a proxy pattern (supporting or counter)."""

    __tablename__ = "proxy_pattern_evidence"

    pattern_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("proxy_patterns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_category: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    support: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)