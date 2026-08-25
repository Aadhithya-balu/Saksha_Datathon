"""Revoked JWT denylist — server-side token revocation support.

Stores the ``jti`` of revoked tokens until their natural expiry, after which
rows are pruned. Backed by SQL so revocation works across multiple backend
instances (no in-process memory dependency).
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.postgres import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
