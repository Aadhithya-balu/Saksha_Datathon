"""Crime cases table — the central incident record."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class CrimeCase(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "crime_cases"

    case_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crime_categories.id"), nullable=False)
    category: Mapped["CrimeCategory"] = relationship(back_populates="crimes")

    location_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False)
    location: Mapped["Location"] = relationship(back_populates="crimes")

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    mo_tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)

    firs: Mapped[list["FIR"]] = relationship(back_populates="crime_case")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="crime_case")
