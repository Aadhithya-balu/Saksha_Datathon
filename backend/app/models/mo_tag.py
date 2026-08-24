"""Normalized modus-operandi tag storage (issue #144 gap 132.1).

Replaces the denormalized ``crime_cases.mo_tags`` comma-separated string as
the queryable source of truth for MO analytics:

- ``mo_tags``          canonical tag vocabulary (unique names)
- ``case_mo_tags``     case <-> tag association
- ``criminal_mo_tags`` criminal <-> tag association

Legacy free-text fields remain untouched for backward compatibility;
``sync_mo_tags()`` in app.services.mo_pattern_service backfills these rows.
"""
import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class MOTag(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "mo_tags"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)

    case_links: Mapped[list["CaseMOTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )
    criminal_links: Mapped[list["CriminalMOTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )


class CaseMOTag(Base):
    __tablename__ = "case_mo_tags"
    __table_args__ = (UniqueConstraint("case_id", "mo_tag_id", name="uq_case_mo_tag"),)

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crime_cases.id", ondelete="CASCADE"), primary_key=True
    )
    mo_tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mo_tags.id", ondelete="CASCADE"), primary_key=True
    )

    case: Mapped["CrimeCase"] = relationship(viewonly=True)
    tag: Mapped[MOTag] = relationship(back_populates="case_links")


class CriminalMOTag(Base):
    __tablename__ = "criminal_mo_tags"
    __table_args__ = (UniqueConstraint("criminal_id", "mo_tag_id", name="uq_criminal_mo_tag"),)

    criminal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("criminals.id", ondelete="CASCADE"), primary_key=True
    )
    mo_tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mo_tags.id", ondelete="CASCADE"), primary_key=True
    )

    criminal: Mapped["Criminal"] = relationship(viewonly=True)
    tag: Mapped[MOTag] = relationship(back_populates="criminal_links")
