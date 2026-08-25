"""Criminal schemas."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


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
