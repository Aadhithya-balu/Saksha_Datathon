"""Intervention schemas (evidence-based prevention loop, gap M7)."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InterventionBase(BaseModel):
    district: str
    intervention_type: str
    title: str
    description: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    status: str = "active"

    # Human Approval Workflow (Draft -> Supervisor Review -> Approved -> Deployed -> Outcome Review)
    workflow_stage: str = "draft"
    intelligence_id: str | None = None
    pattern_type: str | None = None

    # Recommendation Formulation
    affected_h3_cells: str | None = None
    relevant_time_period: str | None = None
    reason: str | None = None
    supporting_intelligence: str | None = None
    estimated_coverage: float | None = None
    assumptions: str | None = None

    # Plan & Compare Simulation
    simulation_data: str | None = None

    # Supervisor Review Notes
    supervisor_notes: str | None = None

    # Post-Deployment Outcome Review
    subsequent_crime_count: int | None = None
    pattern_persisted: str | None = None
    observed_outcome: str | None = None
    review_notes: str | None = None


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

    workflow_stage: str | None = None
    intelligence_id: str | None = None
    pattern_type: str | None = None
    affected_h3_cells: str | None = None
    relevant_time_period: str | None = None
    reason: str | None = None
    supporting_intelligence: str | None = None
    estimated_coverage: float | None = None
    assumptions: str | None = None
    simulation_data: str | None = None
    supervisor_notes: str | None = None
    subsequent_crime_count: int | None = None
    pattern_persisted: str | None = None
    observed_outcome: str | None = None
    review_notes: str | None = None


class AdvanceStageRequest(BaseModel):
    target_stage: str = Field(..., description="Target workflow stage: draft, supervisor_review, approved, deployed, outcome_review, completed")
    notes: str | None = Field(None, description="Optional officer or supervisor notes accompanying the transition")
    outcome_data: dict[str, Any] | None = Field(None, description="Optional post-deployment outcome review fields")


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

