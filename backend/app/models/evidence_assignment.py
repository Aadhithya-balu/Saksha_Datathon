import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class EvidenceAssignment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "evidence_assignments"

    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False)
    evidence: Mapped["Evidence"] = relationship()

    assigned_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), default="Assigned")
    
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    assigner: Mapped["User"] = relationship("User", foreign_keys=[assigned_by])
    assignee: Mapped["User"] = relationship("User", foreign_keys=[assigned_to])
