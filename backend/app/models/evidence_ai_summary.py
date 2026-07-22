import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class EvidenceAISummary(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "evidence_ai_summary"

    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False)
    evidence: Mapped["Evidence"] = relationship()

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
