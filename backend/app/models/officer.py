"""Officers table — investigating/station officers, linked 1:1 to a User login."""
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Officer(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "officers"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    user: Mapped["User"] = relationship(back_populates="officer_profile")

    badge_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    rank: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    station: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    firs: Mapped[list["FIR"]] = relationship(back_populates="investigating_officer")
