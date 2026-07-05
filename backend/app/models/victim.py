"""Victims table."""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Victim(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "victims"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    age: Mapped[int | None] = mapped_column(nullable=True)
    statement: Mapped[str | None] = mapped_column(Text, nullable=True)

    neo4j_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    fir_links: Mapped[list["FIRVictimLink"]] = relationship(back_populates="victim")
