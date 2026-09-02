"""Crime case schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


class CrimeCaseBase(BaseModel):
    category_id: uuid.UUID
    location_id: uuid.UUID
    occurred_at: datetime
    description: str | None = None
    mo_tags: str | None = None
    status: str = "open"
    priority: str = "medium"
    progress: int = 10
    assigned_officer_id: uuid.UUID | None = None
    found_by_police: bool = False

    @model_validator(mode="after")
    def validate_police_discovery(self) -> "CrimeCaseBase":
        if self.found_by_police and not self.assigned_officer_id:
            raise ValueError("Officer is required when the crime is found by police.")
        return self


class CrimeCaseCreate(CrimeCaseBase):
    case_number: str


class CrimeCaseUpdate(BaseModel):
    description: str | None = None
    mo_tags: str | None = None
    status: str | None = None
    priority: str | None = None
    progress: int | None = None
    assigned_officer_id: uuid.UUID | None = None


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
