"""Victim schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VictimBase(BaseModel):
    full_name: str
    contact_number: str | None = None
    address: str | None = None
    gender: str | None = None
    age: int | None = None
    statement: str | None = None
    image_url: str | None = None
    image_url: str | None = None


class VictimCreate(VictimBase):
    pass


class VictimUpdate(BaseModel):
    contact_number: str | None = None
    address: str | None = None
    statement: str | None = None


class VictimOut(VictimBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
