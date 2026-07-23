"""Investigation Notes table — records notes made by investigating officers on crime cases."""
import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class InvestigationNote(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "investigation_notes"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crime_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    officer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("officers.id", ondelete="SET NULL"), nullable=True
    )
    officer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    officer_badge: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    crime_case: Mapped["CrimeCase"] = relationship(back_populates="notes")
