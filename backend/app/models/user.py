"""Users table — platform accounts (officers, analysts, admins log in through this)."""
import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    role: Mapped["Role"] = relationship(back_populates="users")

    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    station: Mapped[str | None] = mapped_column(String(100), nullable=True)

    officer_profile: Mapped["Officer | None"] = relationship(back_populates="user", uselist=False)
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", foreign_keys="Notification.user_id"
    )
