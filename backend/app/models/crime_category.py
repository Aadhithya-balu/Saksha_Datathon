"""Crime categories — IPC/BNS section-backed taxonomy of crime types."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class CrimeCategory(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "crime_categories"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    section_code: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. IPC 379 / BNS 304
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)  # low/medium/high

    crimes: Mapped[list["CrimeCase"]] = relationship(back_populates="category")
