"""Criminals table — offender/suspect registry. Rich profile links to Neo4j via neo4j_node_id."""
from datetime import date

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Criminal(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "criminals"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    aliases: Mapped[str | None] = mapped_column(String(500), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    identifying_marks: Mapped[str | None] = mapped_column(Text, nullable=True)
    mo_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # modus operandi notes
    status: Mapped[str] = mapped_column(String(30), default="at_large")  # at_large/arrested/convicted/deceased

    # Mirrors the corresponding node in Neo4j for cross-reference between the two stores
    neo4j_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    fir_links: Mapped[list["FIRCriminalLink"]] = relationship(back_populates="criminal")
