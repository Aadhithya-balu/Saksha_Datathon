"""Employee — maps to the real Supabase Employee table (police officers/staff)."""
from datetime import date
from typing import Optional

from sqlalchemy import Date, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base


class Officer(Base):
    __tablename__ = "Employee"

    EmployeeID: Mapped[int] = mapped_column(Integer, primary_key=True)
    DistrictID: Mapped[int] = mapped_column(Integer, nullable=False)
    UnitID: Mapped[int] = mapped_column(Integer, nullable=False)
    RankID: Mapped[int] = mapped_column(Integer, nullable=False)
    DesignationID: Mapped[int] = mapped_column(Integer, nullable=False)
    KGID: Mapped[str] = mapped_column(Text, nullable=False)
    FirstName: Mapped[str] = mapped_column(Text, nullable=False)
    EmployeeDOB: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    GenderID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    BloodGroupID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    PhysicallyChallenged: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    AppointmentDate: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    district: Mapped["District"] = relationship(
        "District", primaryjoin="Officer.DistrictID == District.DistrictID", foreign_keys="Officer.DistrictID"
    )
    unit: Mapped["Unit"] = relationship(
        "Unit", primaryjoin="Officer.UnitID == Unit.UnitID", foreign_keys="Officer.UnitID"
    )
    rank: Mapped["Rank"] = relationship(
        "Rank", primaryjoin="Officer.RankID == Rank.RankID", foreign_keys="Officer.RankID"
    )
    designation: Mapped["Designation"] = relationship(
        "Designation", primaryjoin="Officer.DesignationID == Designation.DesignationID", foreign_keys="Officer.DesignationID"
    )
