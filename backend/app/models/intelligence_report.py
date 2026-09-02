"""Intelligence Engine report history — persistence for built intelligence reports.

Enables the Intelligence Engine page to recall a user's prior analysis runs
(recent entities analyzed, summaries, and source IDs) across sessions.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base


class IntelligenceReportRun(Base):
    """A single intelligence build the current user has performed."""

    __tablename__ = "intelligence_report_runs"
    __table_args__ = (
        Index("ix_intel_report_user_ts", "created_by_id", "created_at"),
        Index("ix_intel_report_entity", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # fir/criminal/case/victim
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_label: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Compact report summary for history cards.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Counts surfaced on the history list.
    connections: Mapped[int] = mapped_column(Integer, default=0)
    leads: Mapped[int] = mapped_column(Integer, default=0)
    threads: Mapped[int] = mapped_column(Integer, default=0)
    timeline_events: Mapped[int] = mapped_column(Integer, default=0)
    confirmed: Mapped[int] = mapped_column(Integer, default=0)
    probable: Mapped[int] = mapped_column(Integer, default=0)
    possible: Mapped[int] = mapped_column(Integer, default=0)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by = relationship("User", foreign_keys=[created_by_id])

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
