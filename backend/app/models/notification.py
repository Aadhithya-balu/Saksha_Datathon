"""Notification model — stores inter-station communication notifications for the platform."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import UUIDPKMixin


class Notification(Base, UUIDPKMixin):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    user: Mapped["User"] = relationship(back_populates="notifications", foreign_keys=[user_id])

    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    sender: Mapped["User | None"] = relationship(foreign_keys=[sender_id])

    subject: Mapped[str] = mapped_column(String(500), nullable=False)

    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )

    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="system_notification", index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium"
    )

    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium", index=True
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unread", index=True
    )

    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    related_case_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    related_fir_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_broadcast: Mapped[bool] = mapped_column(Boolean, default=False)

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def mark_read(self) -> None:
        self.is_read = True
        self.status = "read"
        self.read_at = datetime.now()

    def mark_dismissed(self) -> None:
        self.is_dismissed = True
        self.status = "dismissed"

    def mark_acknowledged(self) -> None:
        self.status = "acknowledged"
        self.acknowledged_at = datetime.now()

    def mark_resolved(self) -> None:
        self.status = "resolved"
        self.resolved_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "sender_id": str(self.sender_id) if self.sender_id else None,
            "subject": self.subject,
            "notification_type": self.notification_type,
            "category": self.category,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "priority": self.priority,
            "status": self.status,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "related_case_number": self.related_case_number,
            "related_fir_number": self.related_fir_number,
            "is_read": self.is_read,
            "is_dismissed": self.is_dismissed,
            "is_broadcast": self.is_broadcast,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "attachment_url": self.attachment_url,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
