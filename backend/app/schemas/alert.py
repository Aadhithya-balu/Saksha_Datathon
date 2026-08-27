"""Pydantic schemas for structured alert API responses.

Issue #10 P2: Every alert must carry evidence, provenance, confidence,
policy version, and enough metadata for the frontend to explain why it
was generated.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Evidence block ──────────────────────────────────────────────────

class AlertEvidence(BaseModel):
    """Supporting record metadata for an alert."""
    current_count: int = Field(..., description="Observed count in the current window")
    baseline_count: float = Field(..., description="Normalised baseline count")
    spike_ratio: float = Field(..., description="Current / baseline ratio")
    supporting_records: int = Field(..., description="Number of underlying crime records")
    supporting_record_ids: list[str] = Field(default_factory=list, description="Case IDs backing this alert")
    baseline_observations: int = Field(0, description="Historical data points used for baseline")
    stations: list[str] = Field(default_factory=list, description="Affected stations")


# ── Warning block ───────────────────────────────────────────────────

class AlertWarning(BaseModel):
    """Non-fatal warning attached to an alert (e.g. low confidence, demo data)."""
    code: str = Field(..., description="Machine-readable warning code")
    message: str = Field(..., description="Human-readable explanation")


# ── Individual alert ────────────────────────────────────────────────

class AlertItem(BaseModel):
    """A single structured alert returned by the alerts API."""
    alert_id: str = Field(..., description="Unique alert identifier")
    type: str = Field(..., description="Alert type: RED_ZONE_SPIKE, CRIME_SPIKE, ANOMALY")
    severity: str = Field(..., description="Severity: critical, high, medium, low, informational")
    status: str = Field("unread", description="Lifecycle status")
    district: str = Field(..., description="Affected district")
    crime_category: str = Field(..., description="Affected crime category")
    policy_version: str = Field(..., description="Policy version used for detection")
    provenance: str = Field(..., description="Dataset provenance: LIVE, DEMO, MIXED, UNKNOWN")
    confidence: str = Field(..., description="Confidence: HIGH, MEDIUM, LOW, INSUFFICIENT_DATA")
    evidence: AlertEvidence = Field(..., description="Supporting evidence metadata")
    explanation: str = Field("", description="Human-readable alert explanation")
    warnings: list[AlertWarning] = Field(default_factory=list)
    detection_timestamp: str = Field(..., description="ISO timestamp of detection")
    resource_type: str | None = Field(None, description="Related resource type for investigation linking")
    resource_id: str | None = Field(None, description="Related resource ID (e.g. redzone:district:category)")
    related_case_number: str | None = Field(None, description="Related case number if applicable")


# ── Collection response ─────────────────────────────────────────────

class AlertListResponse(BaseModel):
    """Response from the alerts API — list of structured alerts with metadata."""
    generated_at: str = Field(..., description="ISO timestamp of alert generation")
    policy_version: str = Field(..., description="Policy version used")
    total: int = Field(..., description="Total alerts in this response")
    red_zones: list[AlertItem] = Field(default_factory=list)
    thresholds: dict[str, Any] = Field(default_factory=dict, description="Thresholds applied")


# ── District / category ranking ─────────────────────────────────────

class DistrictRankItem(BaseModel):
    """A single district ranking entry."""
    district: str
    incident_count: int
    rank: int
    period_days: int
    metric: str


class CategoryRankItem(BaseModel):
    """A single crime-category ranking entry."""
    category: str
    incident_count: int
    rank: int
    period_days: int
    metric: str
    change_percentage: float | None = None


# ── Policy inspection ───────────────────────────────────────────────

class PolicyOut(BaseModel):
    """Admin-facing view of the current alert policy."""
    policy_version: str
    red_zone: dict[str, Any]
    anomaly: dict[str, Any]
    incident_priority: dict[str, Any]
    district_ranking: dict[str, Any]
    category_ranking: dict[str, Any]
    evidence_requirements: dict[str, Any]
    dedup_window_minutes: int
