"""Crime case schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.services.case_status import ALL_VALID_STATUSES, is_immutable


class CrimeCaseBase(BaseModel):
    category_id: uuid.UUID
    location_id: uuid.UUID
    occurred_at: datetime
    description: str | None = None
    mo_tags: str | None = None
    status: str = "active"
    priority: str = "medium"
    progress: int = 10
    assigned_officer_id: uuid.UUID | None = None
    found_by_police: bool = False

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v.strip().lower() not in ALL_VALID_STATUSES:
            raise ValueError(
                f"'{v}' is not a valid case status. "
                f"Valid values: {sorted(ALL_VALID_STATUSES)}"
            )
        return v.strip().lower()

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

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v.strip().lower() not in ALL_VALID_STATUSES:
            raise ValueError(
                f"'{v}' is not a valid case status. "
                f"Valid values: {sorted(ALL_VALID_STATUSES)}"
            )
        return v.strip().lower()


class CrimeCaseOut(CrimeCaseBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    case_number: str
    reported_at: datetime
    created_at: datetime
    is_locked: bool = False

    @model_validator(mode="after")
    def set_locked(self) -> "CrimeCaseOut":
        self.is_locked = is_immutable(self.status)
        return self


class CrimeTimelineEvent(BaseModel):
    timestamp: datetime
    event: str
    actor: str | None = None
