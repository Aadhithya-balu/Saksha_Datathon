"""Officer schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OfficerBase(BaseModel):
    badge_number: str
    name: str
    rank: str | None = None
    district: str | None = None
    station: str
    designation: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str = "active"


class OfficerCreate(OfficerBase):
    supabase_user_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class OfficerUpdate(BaseModel):
    name: str | None = None
    rank: str | None = None
    district: str | None = None
    station: str | None = None
    designation: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str | None = None


class OfficerOut(OfficerBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    supabase_user_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None


class OfficerPerformance(BaseModel):
    officer_id: uuid.UUID
    total_firs_handled: int
    cases_closed: int
    cases_open: int
    avg_resolution_days: float | None = None
