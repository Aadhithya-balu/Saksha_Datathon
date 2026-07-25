"""Locations table — districts, police station jurisdictions, and crime-site geo points."""
from sqlalchemy import Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Location(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("station", "address", name="uq_location_station_address"),)

    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    station: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)

    crimes: Mapped[list["CrimeCase"]] = relationship(back_populates="location")
