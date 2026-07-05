"""Evidence table — physical/digital evidence linked to a crime case."""
import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Evidence(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "evidence"

    crime_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crime_cases.id"), nullable=False)
    crime_case: Mapped["CrimeCase"] = relationship(back_populates="evidence")

    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)  # physical/digital/document/biological
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    collected_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chain_of_custody: Mapped[str | None] = mapped_column(Text, nullable=True)
