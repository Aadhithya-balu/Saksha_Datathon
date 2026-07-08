"""ComplainantDetails, ActSectionAssociation, ArrestSurrender, ChargesheetDetails — real Supabase tables."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base


class ComplainantDetails(Base):
    __tablename__ = "ComplainantDetails"

    ComplainantID: Mapped[int] = mapped_column(Integer, primary_key=True)
    CaseMasterID: Mapped[int] = mapped_column(Integer, nullable=False)
    ComplainantName: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    AgeYear: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    OccupationID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ReligionID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    CasteID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    GenderID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    case: Mapped["CaseMaster"] = relationship(
        "CaseMaster", primaryjoin="ComplainantDetails.CaseMasterID == CaseMaster.CaseMasterID",
        foreign_keys="ComplainantDetails.CaseMasterID"
    )


class ActSectionAssociation(Base):
    __tablename__ = "ActSectionAssociation"

    CaseMasterID: Mapped[int] = mapped_column(Integer, primary_key=True)
    ActID: Mapped[str] = mapped_column(Text, primary_key=True)
    SectionID: Mapped[str] = mapped_column(Text, primary_key=True)
    ActOrderID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    SectionOrderID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    case: Mapped["CaseMaster"] = relationship(
        "CaseMaster", primaryjoin="ActSectionAssociation.CaseMasterID == CaseMaster.CaseMasterID",
        foreign_keys="ActSectionAssociation.CaseMasterID"
    )


class ArrestSurrender(Base):
    __tablename__ = "ArrestSurrender"

    ArrestSurrenderID: Mapped[int] = mapped_column(Integer, primary_key=True)
    CaseMasterID: Mapped[int] = mapped_column(Integer, nullable=False)
    ArrestSurrenderTypeID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ArrestSurrenderDate: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ArrestSurrenderStateId: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ArrestSurrenderDistrictId: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    PoliceStationID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    IOID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    CourtID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    AccusedMasterID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    IsAccused: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    IsComplainantAccused: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    case: Mapped["CaseMaster"] = relationship(
        "CaseMaster", primaryjoin="ArrestSurrender.CaseMasterID == CaseMaster.CaseMasterID",
        foreign_keys="ArrestSurrender.CaseMasterID"
    )


class ChargesheetDetails(Base):
    __tablename__ = "ChargesheetDetails"

    CSID: Mapped[int] = mapped_column(Integer, primary_key=True)
    CaseMasterID: Mapped[int] = mapped_column(Integer, nullable=False)
    csdate: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cstype: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    PolicePersonID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    case: Mapped["CaseMaster"] = relationship(
        "CaseMaster", primaryjoin="ChargesheetDetails.CaseMasterID == CaseMaster.CaseMasterID",
        foreign_keys="ChargesheetDetails.CaseMasterID"
    )
