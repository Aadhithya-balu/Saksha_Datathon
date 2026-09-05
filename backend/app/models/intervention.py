"""Interventions table — evidence-based prevention loop (M7).

Records proactive policing interventions (patrol surges, CCTV drives, community
programs) so their effect on district crime rates can be measured pre/post.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
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
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # planned/active/completed/suspended

    # Human Approval Workflow (Draft -> Supervisor Review -> Approved -> Deployed -> Outcome Review)
    workflow_stage: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    intelligence_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    pattern_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Recommendation Formulation
    affected_h3_cells: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-serialized list of H3 cell IDs
    relevant_time_period: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    supporting_intelligence: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-serialized signals
    estimated_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)  # e.g. 82.5%
    assumptions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Plan & Compare Simulation
    simulation_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-serialized current vs proposed metrics

    # Supervisor Review Notes
    supervisor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Post-Deployment Outcome Review
    subsequent_crime_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pattern_persisted: Mapped[str | None] = mapped_column(String(50), nullable=True)  # resolved/reduced/persisted/displaced
    observed_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by = relationship("User")

