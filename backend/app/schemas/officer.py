"""Officer schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OfficerBase(BaseModel):
    badge_number: str
    rank: str | None = None
    district: str
    station: str


class OfficerCreate(OfficerBase):
    user_id: uuid.UUID


class OfficerUpdate(BaseModel):
    rank: str | None = None
    district: str | None = None
    station: str | None = None


class OfficerOut(OfficerBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime


class OfficerPerformance(BaseModel):
    officer_id: uuid.UUID
    total_firs_handled: int
    cases_closed: int
    cases_open: int
    avg_resolution_days: float | None = None
