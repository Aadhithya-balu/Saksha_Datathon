"""District & Unit — maps to real Supabase location tables."""
from typing import Optional

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base


class District(Base):
    __tablename__ = "District"

    DistrictID: Mapped[int] = mapped_column(Integer, primary_key=True)
    DistrictName: Mapped[str] = mapped_column(Text, nullable=False)
    StateID: Mapped[int] = mapped_column(Integer, nullable=False)
    Active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    state: Mapped["State"] = relationship(
        "State", primaryjoin="District.StateID == State.StateID", foreign_keys="District.StateID"
    )


class Unit(Base):
    __tablename__ = "Unit"

    UnitID: Mapped[int] = mapped_column(Integer, primary_key=True)
    UnitName: Mapped[str] = mapped_column(Text, nullable=False)
    TypeID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ParentUnit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    NationalityID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    StateID: Mapped[int] = mapped_column(Integer, nullable=False)
    DistrictID: Mapped[int] = mapped_column(Integer, nullable=False)
    Active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    district: Mapped["District"] = relationship(
        "District", primaryjoin="Unit.DistrictID == District.DistrictID", foreign_keys="Unit.DistrictID"
    )
