"""Pydantic schemas for notification models."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationBase(BaseModel):
    notification_type: str = Field(..., description="Type of notification")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message body")
    severity: str = Field("medium", description="Severity level: critical, high, medium, low")
    resource_type: str | None = Field(None, description="Related resource type")
    resource_id: str | None = Field(None, description="Related resource ID")


class NotificationCreate(NotificationBase):
    user_id: UUID | None = Field(None, description="Target user ID (null = broadcast)")


class NotificationOut(NotificationBase):
    id: UUID
    user_id: UUID | None
    is_read: bool
    is_dismissed: bool
    created_at: datetime
    read_at: datetime | None

    model_config = {"from_attributes": True}


class NotificationUpdate(BaseModel):
    is_read: bool | None = None
    is_dismissed: bool | None = None


class NotificationCountOut(BaseModel):
    total: int
    unread: int
    critical: int


class NotificationListOut(BaseModel):
    total: int
    page: int
    page_size: int
    unread_count: int
    results: list[NotificationOut]


class NotificationMarkReadOut(BaseModel):
    success: bool
    message: str


# ── Activity Feed Schemas ────────────────────────────────────────


class ActivityEvent(BaseModel):
    id: str
    timestamp: str
    event_type: str  # case_created, fir_registered, evidence_added, status_changed, ai_alert
    title: str
    description: str
    actor: str | None
    actor_badge: str | None
    resource_type: str
    resource_id: str | None
    severity: str  # info, success, warning, error


class ActivityFeedOut(BaseModel):
    total: int
    results: list[ActivityEvent]


# ── System Health Schemas ────────────────────────────────────────


class ServiceStatus(BaseModel):
    name: str
    status: str  # healthy, degraded, down
    latency_ms: int
    last_check: str
    details: str | None = None


class SystemHealthOut(BaseModel):
    overall: str  # healthy, degraded, critical
    services: list[ServiceStatus]
    uptime_hours: float
    last_updated: str

