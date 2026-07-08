"""Report schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportGenerateRequest(BaseModel):
    template: str
    district: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    format: str = "pdf"


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    template: str
    district: str | None
    status: str
    format: str
    file_url: str | None
    created_at: datetime
