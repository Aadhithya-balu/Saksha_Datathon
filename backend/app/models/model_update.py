from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.postgres import Base
from app.models.mixins import UUIDPKMixin


class ModelUpdateJob(Base, UUIDPKMixin):
    __tablename__ = "model_update_jobs"

    model_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    previous_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dataset_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    training_records: Mapped[int] = mapped_column(nullable=False, default=0)
    evaluation_metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    deployment_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
