import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class EvidenceMetadata(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "evidence_metadata"

    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, unique=True)
    evidence: Mapped["Evidence"] = relationship()

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filepath: Mapped[str] = mapped_column(String(500), nullable=False)
    filesize: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    uploaded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    extracted_data: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True, default={})
