"""FIR schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FIRBase(BaseModel):
    crime_case_id: uuid.UUID
    investigating_officer_id: uuid.UUID | None = None
    complainant_name: str
    complainant_contact: str | None = None
    sections: str | None = None
    narrative: str | None = None
    status: str = "registered"


class FIRCreate(FIRBase):
    fir_number: str
    criminal_ids: list[uuid.UUID] = []
    victim_ids: list[uuid.UUID] = []


class FIRUpdate(BaseModel):
    investigating_officer_id: uuid.UUID | None = None
    status: str | None = None
    narrative: str | None = None
    sections: str | None = None


class FIROut(FIRBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    fir_number: str
    filed_at: datetime
    created_at: datetime
