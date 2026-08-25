"""Import jobs + staging area — audit trail for bulk data ingestion (CSV/XLSX).

Issue 5 (P1): every external dataset passes through an import job and a row-level
staging table before any record is promoted into trusted Saksha tables.

Pipeline:
    upload -> import job (UPLOADED)
           -> parse/map/normalize/validate (PROCESSING)
           -> dedup + reconcile vs production (VALIDATED / RECONCILING)
           -> quality grade (COMPLETED | COMPLETED_WITH_WARNINGS | FAILED)
           -> admin promotion -> production tables with provenance
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ImportJob(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "import_jobs"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # crime_cases/criminals/victims
    source_format: Mapped[str] = mapped_column(String(10), nullable=False, default="csv")  # csv/xlsx
    mapping_profile: Mapped[str] = mapped_column(String(50), nullable=False, default="standard")  # standard/cctns
    source_system: Mapped[str] = mapped_column(String(100), nullable=False, default="manual_upload")
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Lifecycle: uploaded -> processing -> validated -> reconciling ->
    # completed | completed_with_warnings | failed | cancelled
    status: Mapped[str] = mapped_column(String(30), default="uploaded", index=True)

    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)  # legacy alias for new_record_rows
    failed_rows: Mapped[int] = mapped_column(Integer, default=0)  # legacy alias for invalid_rows

    # Issue 5: full quality metrics (all computed from actual staged rows).
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    warning_rows: Mapped[int] = mapped_column(Integer, default=0)
    exact_duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    potential_duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    conflict_rows: Mapped[int] = mapped_column(Integer, default=0)
    new_record_rows: Mapped[int] = mapped_column(Integer, default=0)
    matched_record_rows: Mapped[int] = mapped_column(Integer, default=0)
    updated_record_rows: Mapped[int] = mapped_column(Integer, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0)
    review_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    promoted_rows: Mapped[int] = mapped_column(Integer, default=0)

    # Quality grade: A/B/C/D/REJECTED — see ingest_service.compute_quality_grade.
    quality_grade: Mapped[str | None] = mapped_column(String(10), nullable=True)

    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # JSON-encoded validation report: [{row_number, errors[], warnings[], ...}]
    validation_report: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by = relationship("User", foreign_keys=[created_by_id])

    promoted_by_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    promoted_by = relationship("User", foreign_keys=[promoted_by_id])

    staged_records = relationship("ImportStagedRecord", back_populates="job", cascade="all, delete-orphan")


class ImportStagedRecord(Base, UUIDPKMixin):
    """One staged source row awaiting validation/reconciliation/promotion.

    Nothing reaches a production table until an admin promotes it; this table is
    the durable record of exactly what was received and what happened to it.
    """

    __tablename__ = "import_staging_records"
    __table_args__ = (
        Index("ix_staging_job_row", "job_id", "row_number"),
        Index("ix_staging_reconciliation", "reconciliation_status"),
    )

    job_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job = relationship("ImportJob", back_populates="staged_records")

    row_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-based data row
    source_row_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. spreadsheet row "7"

    # Verbatim mapped source values (auditability: nothing silently dropped).
    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON {source_header: value}
    mapped_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON {saksha_column: normalized value}

    # valid | invalid | warning
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    validation_errors: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON [{code, field, message}]
    validation_warnings: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON [{code, field, message}]

    # unique | exact_duplicate | existing_match | potential_duplicate
    duplicate_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unique", index=True)
    duplicate_of: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON refs [{kind, key, id?}]

    # pending | new_record | matched | updated | conflict | duplicate | review_required | rejected
    reconciliation_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    reconciliation_details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON incl. field diffs

    # validated | validated_with_warnings | review_required | rejected
    trust_level: Mapped[str] = mapped_column(String(30), nullable=False, default="rejected", index=True)

    promoted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    promoted_record_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ImportProvenanceMixin:
    """Lineage columns carried by every imported-then-promoted record (§4/§26).

    ``dataset_provenance`` distinguishes LIVE operational records from MIGRATED
    bulk-imported ones so analytics never treat the two identically.
    """

    dataset_provenance: Mapped[str] = mapped_column(String(20), nullable=False, default="live", index=True)
    source_import_job_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_row_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
