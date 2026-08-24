"""Officers table — investigating/station officers, linked 1:1 to a User login."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Officer(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "officers"

    supabase_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=True)
    user: Mapped["User"] = relationship(back_populates="officer_profile")

    badge_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rank: Mapped[str | None] = mapped_column(String(100), nullable=True)
    station: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(50), default="active")

    # Issue #107: officer profile image
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Issue #118: face biometric fields
    # Compact numpy float32 embedding stored as JSON array; never exposed to frontend
    face_embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    face_embedding_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    face_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    face_enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    face_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    firs: Mapped[list["FIR"]] = relationship(back_populates="investigating_officer")
