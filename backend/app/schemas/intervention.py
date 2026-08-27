"""Intervention schemas (evidence-based prevention loop, gap M7)."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InterventionBase(BaseModel):
    district: str
    intervention_type: str
    title: str
    description: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    status: str = "active"


class InterventionCreate(InterventionBase):
    pass


class InterventionUpdate(BaseModel):
    district: str | None = None
    intervention_type: str | None = None
    title: str | None = None
    description: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    status: str | None = None


class InterventionOut(InterventionBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_by_id: uuid.UUID | None = None
    created_at: datetime


class InterventionListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    results: list[InterventionOut] = []
    interventions: list[InterventionOut] = []
