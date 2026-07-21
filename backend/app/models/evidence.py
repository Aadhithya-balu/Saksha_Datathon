"""Evidence table — physical/digital evidence linked to a crime case."""
import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Evidence(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "evidence"

    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crime_cases.id"), nullable=False)
    crime_case: Mapped["CrimeCase"] = relationship(back_populates="evidence")

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., image, video, audio, document
    status: Mapped[str] = mapped_column(String(50), default="Pending")
    
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Relationships for backref or further linkage
    assignee: Mapped["User"] = relationship("User", foreign_keys=[assigned_to])
