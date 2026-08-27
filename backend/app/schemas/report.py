"""Report schemas.

Issue #176: schemas for the production report lifecycle (draft -> generate ->
review -> final -> archive) with source/evidence linking, provenance, versioning
and integrity metadata.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.report import REPORT_LIFECYCLE


class ReportGenerateRequest(BaseModel):
    template: str
    district: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    format: str = "pdf"


class ReportSourceRef(BaseModel):
    source_type: str = Field(min_length=1, max_length=50)
    source_id: str = Field(min_length=1, max_length=100)
    source_label: str | None = Field(default=None, max_length=255)


class ReportCreateRequest(BaseModel):
    report_type: str = Field(default="cases", max_length=50)
    title: str | None = Field(default=None, max_length=255)
    case_id: uuid.UUID | None = None
    district: str | None = Field(default=None, max_length=100)
    format: str = Field(default="pdf", max_length=10)
    provenance: str | None = Field(default=None, max_length=20)
    ai_reported: bool = False


class ReportGeneratePayload(BaseModel):
    """Content + references to persist for a lifecycle report.

    ``content`` is the raw tabular snapshot the finalized report is rendered
    from: {headers: [...], rows: [...]}. ``sources`` and ``evidence_ids`` link
    the report to actual records (they are validated against the database when
    the report is marked as AI-generated / verified).
    """

    content: dict | None = Field(default=None, description="{\"headers\": [...], \"rows\": [...]}")
    title: str | None = Field(default=None, max_length=255)
    sources: list[ReportSourceRef] = Field(default_factory=list)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    ai_metadata: dict | None = Field(
        default=None,
        description="provider/model/prompt/batch identifiers for AI-generated reports",
    )
    require_verified_references: bool = Field(
        default=True,
        description="Reject generation when any referenced source does not exist",
    )
    analysis_fingerprint: str | None = Field(default=None, max_length=200)


class ReportVersionCreateRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
    content: dict | None = Field(default=None)


class ReportReviewRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)


class ReportValidateRequest(BaseModel):
    sources: list[ReportSourceRef] = Field(default_factory=list)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)


class ReportVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    version_number: int
    created_at: datetime
    reason: str | None
    status: str
    integrity_hash: str | None
    created_by: str | None = None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    report_type: str
    template: str
    title: str | None
    district: str | None
    status: str
    format: str
    file_url: str | None
    provenance: str
    version: int = 1
    integrity_hash: str | None
    generation_method: str | None
    ai_reported: bool
    source_record_count: int
    evidence_count: int
    case_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime | None
    requested_by: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _derive_display_fields(cls, obj):
        if isinstance(obj, dict):
            return obj
        try:
            requester = getattr(obj, "requested_by", None)
            requester_name = getattr(requester, "full_name", None) or getattr(requester, "username", None)
        except Exception:
            requester_name = None
        data = obj.__dict__.copy()
        data["requested_by"] = requester_name
        return data


class ReportDetailOut(ReportOut):
    date_from: datetime | None = None
    date_to: datetime | None = None
    case_number: str | None = None
    analysis_fingerprint: str | None = None
    failure_reason: str | None = None
    generated_at: datetime | None = None
    reviewed_at: datetime | None = None
    finalized_at: datetime | None = None
    archived_at: datetime | None = None
    reviewed_by: str | None = None
    finalized_by: str | None = None
    ai_metadata: dict | None = None
    snapshot_headers: list[str] = Field(default_factory=list)
    snapshot_row_count: int = 0
    sources: list[dict] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    versions: list[ReportVersionOut] = Field(default_factory=list)


class ReportAuditOut(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    user: str
    role: str
    action: str
    resource_type: str
    resource_id: str | None
    result: str
    details: str | None
    ip: str | None


class ReportValidationOut(BaseModel):
    verified_records: list[dict] = Field(default_factory=list)
    missing_records: list[dict] = Field(default_factory=list)
    can_finalize_as_verified: bool


class LifecycleTransitionOut(BaseModel):
    id: uuid.UUID
    status: str
    version: int
    integrity_hash: str | None
    message: str


def is_valid_lifecycle_status(value: str) -> bool:
    return value in REPORT_LIFECYCLE