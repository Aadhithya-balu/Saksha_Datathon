"""Interventions table — evidence-based prevention loop (M7).

Records proactive policing interventions (patrol surges, CCTV drives, community
programs) so their effect on district crime rates can be measured pre/post.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Intervention(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "interventions"

    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    intervention_type: Mapped[str] = mapped_column(String(50), nullable=False)  # patrol_surge/cctv_deployment/community_program/checkpoint/awareness_drive/other
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # planned/active/completed

    created_by_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by = relationship("User")
