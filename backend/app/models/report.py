"""Reports table — generated intelligence/summary reports for SCRB.

Issue #176: reports carry a production audit lifecycle.
Every report is traceable through:

    User → Action → Case/Investigation → Source Records → Evidence
    → Report → Report Version → Audit History

Lifecycle statuses (canonical):
    draft -> generating -> generated -> under_review -> final -> archived
    any state can transition to `failed` on generation/review errors.
Legacy statuses (queued/processing/ready/failed) remain readable.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

# Canonical lifecycle states (issue #176 §2).
REPORT_STATUS_DRAFT = "draft"
REPORT_STATUS_GENERATING = "generating"
REPORT_STATUS_GENERATED = "generated"
REPORT_STATUS_UNDER_REVIEW = "under_review"
REPORT_STATUS_FINAL = "final"
REPORT_STATUS_ARCHIVED = "archived"
REPORT_STATUS_FAILED = "failed"

# Legacy aliases kept readable for backward compatibility.
LEGACY_REPORT_STATUSES = {"queued", "processing", "ready", "failed"}

REPORT_LIFECYCLE = [
    REPORT_STATUS_DRAFT,
    REPORT_STATUS_GENERATING,
    REPORT_STATUS_GENERATED,
    REPORT_STATUS_UNDER_REVIEW,
    REPORT_STATUS_FINAL,
    REPORT_STATUS_ARCHIVED,
    REPORT_STATUS_FAILED,
]

# Provenance (§7): where the underlying records came from.
PROVENANCE_LIVE = "live"
PROVENANCE_MIGRATED = "migrated"
PROVENANCE_DEMO = "demo"
PROVENANCE_MIXED = "mixed"
PROVENANCE_UNKNOWN = "unknown"
REPORT_PROVENANCES = {
    PROVENANCE_LIVE,
    PROVENANCE_MIGRATED,
    PROVENANCE_DEMO,
    PROVENANCE_MIXED,
    PROVENANCE_UNKNOWN,
}

# Generation method (§8/§26).
GEN_METHOD_DATABASE_EXPORT = "database_export"
GEN_METHOD_AI_ASSISTED = "ai_assisted"
GEN_METHOD_MANUAL = "manual"
REPORT_GEN_METHODS = {
    GEN_METHOD_DATABASE_EXPORT,
    GEN_METHOD_AI_ASSISTED,
    GEN_METHOD_MANUAL,
}

# Source record kinds tracked by report_source_links (§5).
SOURCE_TYPE_CASE = "crime_case"
SOURCE_TYPE_CRIMINAL = "criminal"
SOURCE_TYPE_VICTIM = "victim"
SOURCE_TYPE_OFFICER = "officer"
SOURCE_TYPE_FIR = "fir"
SOURCE_TYPE_EVIDENCE = "evidence"
SOURCE_TYPE_NETWORK = "network_relationship"
SOURCE_TYPE_ANALYTICAL = "analytical_result"
REPORT_SOURCE_TYPES = {
    SOURCE_TYPE_CASE,
    SOURCE_TYPE_CRIMINAL,
    SOURCE_TYPE_VICTIM,
    SOURCE_TYPE_OFFICER,
    SOURCE_TYPE_FIR,
    SOURCE_TYPE_EVIDENCE,
    SOURCE_TYPE_NETWORK,
    SOURCE_TYPE_ANALYTICAL,
}


class Report(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_status_type", "status", "report_type"),
        Index("ix_reports_case_id", "case_id"),
        Index("ix_reports_provenance", "provenance"),
    )

    # The legacy `template` column remains available; the canonical type lives
    # in `report_type` (cases/officers/criminals/evidence/dossier/investigation).
    template: Mapped[str] = mapped_column(String(100), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), default="cases", nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    requested_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    requested_by: Mapped["User"] = relationship(foreign_keys=[requested_by_id])

    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    format: Mapped[str] = mapped_column(String(10), default="pdf")  # pdf/csv/docx/txt/xlsx
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # §10 — current version number (increments on every new ReportVersion).
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # §4/§5 — case/investigation context the report belongs to.
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crime_cases.id", ondelete="SET NULL"), nullable=True
    )
    case: Mapped["CrimeCase | None"] = relationship(foreign_keys=[case_id])

    # §7 — provenance of the underlying information.
    provenance: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)

    # §12 — integrity hash of the finalized snapshot (sha256, not encryption).
    integrity_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # §8/§26 — how the report was produced (and which analysis/model applied).
    generation_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    analysis_fingerprint: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # §25 — failure state (never a misleading partial final report).
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Counts computed from actual linked records (never fabricated).
    source_record_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)

    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by_id])

    finalized_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    finalized_by: Mapped["User | None"] = relationship(foreign_keys=[finalized_by_id])

    # §27/§28 — snapshot of the rows used at generation time (JSON string).
    # Finalized reports render exclusively from this snapshot.
    content_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    # §8/§9 — AI provenance block (provider/model/prompt/validation) as JSON.
    ai_reported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)

    # §6 — evidence relationships.
    evidence_links: Mapped[list["ReportEvidenceLink"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
    # §5 — source record relationships.
    source_links: Mapped[list["ReportSourceLink"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
    # §10 — version history.
    versions: Mapped[list["ReportVersion"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class ReportVersion(Base, UUIDPKMixin):
    """An immutable snapshot of a report at a given point in its lifecycle (§10).

    A new row is created every time the report content changes after it has
    been generated; finalized versions are never overwritten.
    """

    __tablename__ = "report_versions"
    __table_args__ = (
        Index("ix_report_versions_report_num", "report_id", "version_number", unique=True),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report: Mapped["Report"] = relationship(back_populates="versions")

    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped["User | None"] = relationship(foreign_keys=[created_by_id])

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Snapshot of the report's state at version-creation time.
    status: Mapped[str] = mapped_column(String(30), default="generated")
    integrity_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportSourceLink(Base, UUIDPKMixin):
    """A source record referenced by a report (§5/§28).

    Only stores the stable record identifier and a human label — sensitive
    content is retrieved on demand, never duplicated into the link.
    """

    __tablename__ = "report_source_links"
    __table_args__ = (
        Index("ix_report_source_link_type_id", "source_type", "source_id"),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report: Mapped["Report"] = relationship(back_populates="source_links")

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReportEvidenceLink(Base, UUIDPKMixin):
    """A supporting evidence record referenced by a report (§6)."""

    __tablename__ = "report_evidence_links"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report: Mapped["Report"] = relationship(back_populates="evidence_links")

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence: Mapped["Evidence"] = relationship()

    role: Mapped[str] = mapped_column(String(30), default="supporting")  # supporting/cited
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())