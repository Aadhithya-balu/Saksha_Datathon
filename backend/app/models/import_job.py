"""Import jobs table — audit trail for legacy bulk data ingestion (CSV/XLSX)."""
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ImportJob(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "import_jobs"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # crime_cases/criminals/victims
    source_format: Mapped[str] = mapped_column(String(10), nullable=False, default="csv")  # csv/xlsx
    mapping_profile: Mapped[str] = mapped_column(String(50), nullable=False, default="standard")  # standard/cctns
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed", index=True)  # completed/partial/failed

    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0)

    # JSON-encoded validation report: [{row_number, errors[], warnings[]}]
    validation_report: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by = relationship("User")
