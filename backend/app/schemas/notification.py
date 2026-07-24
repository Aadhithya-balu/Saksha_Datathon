"""Pydantic schemas for notification models — inter-station communication center."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Base ────────────────────────────────────────────────────────────

class NotificationBase(BaseModel):
    notification_type: str = Field(..., description="Type of notification")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message body")
    severity: str = Field("medium", description="Severity level: critical, high, medium, low")


class NotificationCreate(BaseModel):
    sender_id: UUID | None = Field(None, description="Sender user ID")
    recipient_id: UUID | str | None = Field(None, description="Recipient user ID or username (None = broadcast)")
    subject: str = Field(..., description="Subject line")
    notification_type: str = Field("message", description="Notification type")
    category: str = Field("system_notification", description="Category: investigation_update, evidence_request, crime_alert, etc.")
    title: str = Field(..., description="Notification title")
    message: str = Field("", description="Notification message body")
    priority: str = Field("medium", description="Priority: critical, high, medium, low")
    severity: str = Field("medium", description="Severity: critical, high, medium, low")
    related_case_number: str | None = Field(None, description="Related case number")
    related_fir_number: str | None = Field(None, description="Related FIR number")
    is_broadcast: bool = Field(False, description="Send to all users")
    parent_id: UUID | None = Field(None, description="Parent notification ID for replies")
    attachment_url: str | None = Field(None, description="Attachment URL")


class NotificationUpdate(BaseModel):
    is_read: bool | None = None
    is_dismissed: bool | None = None
    status: str | None = None


class NotificationOut(BaseModel):
    id: UUID
    user_id: UUID | None
    sender_id: UUID | None
    sender_name: str | None = None
    sender_badge: str | None = None
    recipient_name: str | None = None
    subject: str
    notification_type: str
    category: str
    title: str
    message: str
    severity: str
    priority: str
    status: str
    resource_type: str | None
    resource_id: str | None
    related_case_number: str | None
    related_fir_number: str | None
    is_read: bool
    is_dismissed: bool
    is_broadcast: bool
    parent_id: UUID | None
    attachment_url: str | None
    created_at: datetime
    read_at: datetime | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class NotificationListOut(BaseModel):
    total: int
    page: int
    page_size: int
    unread_count: int
    results: list[NotificationOut]


class NotificationCountOut(BaseModel):
    total: int
    unread: int
    critical: int


class NotificationActionOut(BaseModel):
    success: bool
    message: str


# ── Dashboard Summary ──────────────────────────────────────────────

class NotificationDashboardSummary(BaseModel):
    unread_count: int = 0
    critical_alerts: int = 0
    today_messages: int = 0
    pending_acknowledgements: int = 0
    investigation_requests: int = 0
    broadcast_messages: int = 0


# ── Activity Feed Schemas ────────────────────────────────────────


class ActivityEvent(BaseModel):
    id: str
    timestamp: str
    event_type: str
    title: str
    description: str
    actor: str | None
    actor_badge: str | None
    resource_type: str
    resource_id: str | None
    severity: str


class ActivityFeedOut(BaseModel):
    total: int
    results: list[ActivityEvent]


# ── System Health Schemas ────────────────────────────────────────


class ServiceStatus(BaseModel):
    name: str
    status: str
    latency_ms: int
    last_check: str
    details: str | None = None


class SystemHealthOut(BaseModel):
    overall: str
    services: list[ServiceStatus]
    uptime_hours: float
    last_updated: str
