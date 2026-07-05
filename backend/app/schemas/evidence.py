"""Evidence schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenceBase(BaseModel):
    crime_case_id: uuid.UUID
    evidence_type: str
    description: str | None = None
    file_url: str | None = None
    collected_by: str | None = None
    chain_of_custody: str | None = None


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceOut(EvidenceBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
