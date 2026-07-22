"""Reports table — generated intelligence/summary reports for SCRB."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Report(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "reports"

    template: Mapped[str] = mapped_column(String(100), nullable=False)
    requested_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    requested_by: Mapped["User"] = relationship()

    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    format: Mapped[str] = mapped_column(String(10), default="pdf")  # pdf/excel
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued/processing/ready/failed
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
