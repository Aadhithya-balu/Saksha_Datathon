"""Victim — maps to the real Supabase Victim table."""
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base


class Victim(Base):
    __tablename__ = "Victim"

    VictimMasterID: Mapped[int] = mapped_column(Integer, primary_key=True)
    CaseMasterID: Mapped[int] = mapped_column(Integer, ForeignKey("CaseMaster.CaseMasterID"), nullable=False)
    VictimName: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    AgeYear: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    GenderID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    VictimPolice: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    case: Mapped["CaseMaster"] = relationship(back_populates="victims")
