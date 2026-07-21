"""Location schemas."""
import uuid

from pydantic import BaseModel, ConfigDict


class LocationBase(BaseModel):
    address: str | None = None
    district: str
    station: str | None = None
    latitude: float
    longitude: float
    pincode: str | None = None


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    address: str | None = None
    station: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    pincode: str | None = None


class LocationOut(LocationBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
