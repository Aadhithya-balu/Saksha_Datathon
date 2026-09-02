"""Criminal schemas."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

VALID_CRIMINAL_STATUSES = {
    "at_large",
    "searching",
    "wanted",
    "arrested",
    "on_bail",
    "under_trial",
    "convicted",
    "acquitted",
    "deceased",
}


class CriminalBase(BaseModel):
    full_name: str
    aliases: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    address: str | None = None
    identifying_marks: str | None = None
    mo_summary: str | None = None
    status: str = "at_large"
    gang_affiliation: str | None = None
    image_url: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        cleaned = v.strip().lower().replace(" ", "_") if v else "at_large"
        if cleaned in ("searching", "wanted"):
            cleaned = "at_large"
        if cleaned not in VALID_CRIMINAL_STATUSES:
            raise ValueError(
                f"Invalid criminal status '{v}'. Allowed values: {sorted(list(VALID_CRIMINAL_STATUSES))}"
            )
        return cleaned


class CriminalCreate(CriminalBase):
    pass


class CriminalUpdate(BaseModel):
    full_name: str | None = None
    aliases: str | None = None
    address: str | None = None
    identifying_marks: str | None = None
    mo_summary: str | None = None
    status: str | None = None
    gang_affiliation: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip().lower().replace(" ", "_")
        if cleaned in ("searching", "wanted"):
            cleaned = "at_large"
        if cleaned not in VALID_CRIMINAL_STATUSES:
            raise ValueError(
                f"Invalid criminal status '{v}'. Allowed values: {sorted(list(VALID_CRIMINAL_STATUSES))}"
            )
        return cleaned


class CriminalOut(CriminalBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime


class MOTimeWindow(BaseModel):
    window: str
    incident_count: int
    distribution: dict[str, int] = {}


class MOProfile(BaseModel):
    criminal_id: uuid.UUID
    preferred_crime_types: list[str] = []
    common_time_window: MOTimeWindow | None = None
    common_tools: list[str] = []
    jurisdictions_active: list[str] = []
    linked_incidents_count: int = 0
