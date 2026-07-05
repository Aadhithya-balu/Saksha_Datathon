"""FIR table + link tables (FIR<->Criminal, FIR<->Victim are many-to-many)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class FIR(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "firs"

    fir_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    crime_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crime_cases.id"), nullable=False)
    crime_case: Mapped["CrimeCase"] = relationship(back_populates="firs")

    investigating_officer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("officers.id"), nullable=True
    )
    investigating_officer: Mapped["Officer | None"] = relationship(back_populates="firs")

    complainant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    complainant_contact: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sections: Mapped[str | None] = mapped_column(String(255), nullable=True)  # comma-separated IPC/BNS sections
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(30), default="registered", index=True)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)

    criminal_links: Mapped[list["FIRCriminalLink"]] = relationship(back_populates="fir")
    victim_links: Mapped[list["FIRVictimLink"]] = relationship(back_populates="fir")


class FIRCriminalLink(Base, UUIDPKMixin):
    """Many-to-many join: which criminals/suspects are named in a given FIR."""
    __tablename__ = "fir_criminal_links"

    fir_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("firs.id"), nullable=False)
    criminal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("criminals.id"), nullable=False)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)  # accused/suspect/absconding

    fir: Mapped["FIR"] = relationship(back_populates="criminal_links")
    criminal: Mapped["Criminal"] = relationship(back_populates="fir_links")


class FIRVictimLink(Base, UUIDPKMixin):
    """Many-to-many join: which victims are named in a given FIR."""
    __tablename__ = "fir_victim_links"

    fir_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("firs.id"), nullable=False)
    victim_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("victims.id"), nullable=False)

    fir: Mapped["FIR"] = relationship(back_populates="victim_links")
    victim: Mapped["Victim"] = relationship(back_populates="fir_links")
