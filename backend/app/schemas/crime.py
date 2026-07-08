"""Crime case schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CrimeCaseBase(BaseModel):
    category_id: uuid.UUID
    location_id: uuid.UUID
    occurred_at: datetime
    description: str | None = None
    mo_tags: str | None = None
    status: str = "open"


class CrimeCaseCreate(CrimeCaseBase):
    case_number: str


class CrimeCaseUpdate(BaseModel):
    description: str | None = None
    mo_tags: str | None = None
    status: str | None = None


class CrimeCaseOut(CrimeCaseBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    case_number: str
    reported_at: datetime
    created_at: datetime


class CrimeTimelineEvent(BaseModel):
    timestamp: datetime
    event: str
    actor: str | None = None
