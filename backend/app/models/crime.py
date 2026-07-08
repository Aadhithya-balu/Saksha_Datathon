"""CaseMaster — maps to the real Supabase CaseMaster table."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Double, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base


class CaseMaster(Base):
    __tablename__ = "CaseMaster"

    CaseMasterID: Mapped[int] = mapped_column(Integer, primary_key=True)
    CrimeNo: Mapped[str] = mapped_column(Text, nullable=False)
    CaseNo: Mapped[str] = mapped_column(Text, nullable=False)
    CrimeRegisteredDate: Mapped[date] = mapped_column(Date, nullable=False)
    PolicePersonID: Mapped[int] = mapped_column(Integer, nullable=False)
    PoliceStationID: Mapped[int] = mapped_column(Integer, nullable=False)
    CaseCategoryID: Mapped[int] = mapped_column(Integer, nullable=False)
    GravityOffenceID: Mapped[int] = mapped_column(Integer, nullable=False)
    CrimeMajorHeadID: Mapped[int] = mapped_column(Integer, nullable=False)
    CrimeMinorHeadID: Mapped[int] = mapped_column(Integer, nullable=False)
    CaseStatusID: Mapped[int] = mapped_column(Integer, nullable=False)
    CourtID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    IncidentFromDate: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    IncidentToDate: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    InfoReceivedPSDate: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    BriefFacts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    accused: Mapped[list["Accused"]] = relationship(
        "Accused", primaryjoin="CaseMaster.CaseMasterID == Accused.CaseMasterID", foreign_keys="Accused.CaseMasterID"
    )
    victims: Mapped[list["Victim"]] = relationship(
        "Victim", primaryjoin="CaseMaster.CaseMasterID == Victim.CaseMasterID", foreign_keys="Victim.CaseMasterID"
    )
    complainants: Mapped[list["ComplainantDetails"]] = relationship(
        "ComplainantDetails", primaryjoin="CaseMaster.CaseMasterID == ComplainantDetails.CaseMasterID", foreign_keys="ComplainantDetails.CaseMasterID"
    )
    act_sections: Mapped[list["ActSectionAssociation"]] = relationship(
        "ActSectionAssociation", primaryjoin="CaseMaster.CaseMasterID == ActSectionAssociation.CaseMasterID", foreign_keys="ActSectionAssociation.CaseMasterID"
    )
    arrests: Mapped[list["ArrestSurrender"]] = relationship(
        "ArrestSurrender", primaryjoin="CaseMaster.CaseMasterID == ArrestSurrender.CaseMasterID", foreign_keys="ArrestSurrender.CaseMasterID"
    )
    chargesheets: Mapped[list["ChargesheetDetails"]] = relationship(
        "ChargesheetDetails", primaryjoin="CaseMaster.CaseMasterID == ChargesheetDetails.CaseMasterID", foreign_keys="ChargesheetDetails.CaseMasterID"
    )
    status: Mapped["CaseStatusMaster"] = relationship(
        "CaseStatusMaster", primaryjoin="CaseMaster.CaseStatusID == CaseStatusMaster.CaseStatusID", foreign_keys="CaseMaster.CaseStatusID"
    )
    category: Mapped["CaseCategory"] = relationship(
        "CaseCategory", primaryjoin="CaseMaster.CaseCategoryID == CaseCategory.CaseCategoryID", foreign_keys="CaseMaster.CaseCategoryID"
    )
    major_head: Mapped["CrimeHead"] = relationship(
        "CrimeHead", primaryjoin="CaseMaster.CrimeMajorHeadID == CrimeHead.CrimeHeadID", foreign_keys="CaseMaster.CrimeMajorHeadID"
    )
    minor_head: Mapped["CrimeSubHead"] = relationship(
        "CrimeSubHead", primaryjoin="CaseMaster.CrimeMinorHeadID == CrimeSubHead.CrimeSubHeadID", foreign_keys="CaseMaster.CrimeMinorHeadID"
    )
    station: Mapped["Unit"] = relationship(
        "Unit", primaryjoin="CaseMaster.PoliceStationID == Unit.UnitID", foreign_keys="CaseMaster.PoliceStationID"
    )
    court: Mapped[Optional["Court"]] = relationship(
        "Court", primaryjoin="CaseMaster.CourtID == Court.CourtID", foreign_keys="CaseMaster.CourtID", viewonly=True
    )
