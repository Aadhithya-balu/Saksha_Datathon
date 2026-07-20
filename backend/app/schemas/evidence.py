"""Evidence schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EvidenceBase(BaseModel):
    case_id: uuid.UUID
    title: str
    evidence_type: str
    description: str | None = None
    status: str = "Pending"
    created_by: str | None = None
    assigned_to: uuid.UUID | None = None
    storage_path: str | None = None


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceUpdate(BaseModel):
    title: str | None = None
    evidence_type: str | None = None
    description: str | None = None
    status: str | None = None
    assigned_to: uuid.UUID | None = None
    storage_path: str | None = None


class EvidenceOut(EvidenceBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None = None


class EvidenceMetadataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    evidence_id: uuid.UUID
    filename: str
    filepath: str
    filesize: int
    mime_type: str
    uploaded_by: str | None = None
    extracted_data: dict[str, Any] | None = None
    created_at: datetime


class EvidenceTimelineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    evidence_id: uuid.UUID
    action: str
    performed_by: str
    role: str
    description: str | None = None
    created_at: datetime


class EvidenceAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    evidence_id: uuid.UUID
    assigned_by: uuid.UUID
    assigned_to: uuid.UUID
    status: str
    assigned_at: datetime
    accepted_at: datetime | None = None
    completed_at: datetime | None = None


class ChainOfCustodyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    evidence_id: uuid.UUID
    from_user: uuid.UUID | None = None
    to_user: uuid.UUID | None = None
    action: str
    location: str | None = None
    remarks: str | None = None
    timestamp: datetime


class EvidenceAISummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    evidence_id: uuid.UUID
    summary: str
    model: str
    created_at: datetime


class EvidenceDetailOut(EvidenceOut):
    metadata: EvidenceMetadataOut | None = None
    timeline: list[EvidenceTimelineOut] = []
    assignments: list[EvidenceAssignmentOut] = []
    chain_of_custody: list[ChainOfCustodyOut] = []
    ai_summaries: list[EvidenceAISummaryOut] = []

