"""Lookup/reference tables — CrimeHead, CrimeSubHead, CaseCategory, CaseStatusMaster, Act, Section, etc."""
from typing import Optional

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base


class CrimeHead(Base):
    __tablename__ = "CrimeHead"
    CrimeHeadID: Mapped[int] = mapped_column(Integer, primary_key=True)
    CrimeGroupName: Mapped[str] = mapped_column(Text, nullable=False)
    Active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class CrimeSubHead(Base):
    __tablename__ = "CrimeSubHead"
    CrimeSubHeadID: Mapped[int] = mapped_column(Integer, primary_key=True)
    CrimeHeadID: Mapped[int] = mapped_column(Integer, nullable=False)
    CrimeHeadName: Mapped[str] = mapped_column(Text, nullable=False)
    SeqID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class CaseCategory(Base):
    __tablename__ = "CaseCategory"
    CaseCategoryID: Mapped[int] = mapped_column(Integer, primary_key=True)
    LookupValue: Mapped[str] = mapped_column(Text, nullable=False)


class CaseStatusMaster(Base):
    __tablename__ = "CaseStatusMaster"
    CaseStatusID: Mapped[int] = mapped_column(Integer, primary_key=True)
    CaseStatusName: Mapped[str] = mapped_column(Text, nullable=False)


class GravityOffence(Base):
    __tablename__ = "GravityOffence"
    GravityOffenceID: Mapped[int] = mapped_column(Integer, primary_key=True)
    LookupValue: Mapped[str] = mapped_column(Text, nullable=False)


class Act(Base):
    __tablename__ = "Act"
    ActCode: Mapped[str] = mapped_column(Text, primary_key=True)
    ActDescription: Mapped[str] = mapped_column(Text, nullable=False)
    ShortName: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    Active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Section(Base):
    __tablename__ = "Section"
    ActCode: Mapped[str] = mapped_column(Text, primary_key=True)
    SectionCode: Mapped[str] = mapped_column(Text, primary_key=True)
    SectionDescription: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    Active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Court(Base):
    __tablename__ = "Court"
    CourtID: Mapped[int] = mapped_column(Integer, primary_key=True)
    CourtName: Mapped[str] = mapped_column(Text, nullable=False)
    DistrictID: Mapped[int] = mapped_column(Integer, nullable=False)
    StateID: Mapped[int] = mapped_column(Integer, nullable=False)
    Active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class State(Base):
    __tablename__ = "State"
    StateID: Mapped[int] = mapped_column(Integer, primary_key=True)
    StateName: Mapped[str] = mapped_column(Text, nullable=False)
    NationalityID: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    Active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Rank(Base):
    __tablename__ = "Rank"
    RankID: Mapped[int] = mapped_column(Integer, primary_key=True)
    RankName: Mapped[str] = mapped_column(Text, nullable=False)
    Hierarchy: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    Active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Designation(Base):
    __tablename__ = "Designation"
    DesignationID: Mapped[int] = mapped_column(Integer, primary_key=True)
    DesignationName: Mapped[str] = mapped_column(Text, nullable=False)
    Active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    SortOrder: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
