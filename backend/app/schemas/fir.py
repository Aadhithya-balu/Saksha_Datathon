"""FIR schemas."""
import json
import re
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.schemas.crime import CrimeCaseOut
from app.schemas.officer import OfficerOut
from app.schemas.criminal import CriminalOut
from app.schemas.victim import VictimOut
from app.schemas.evidence import EvidenceOut


class FIRBase(BaseModel):
    crime_case_id: uuid.UUID
    investigating_officer_id: uuid.UUID | None = None
    complainant_name: str
    complainant_contact: str | None = None
    sections: str | None = None
    narrative: str | None = None
    status: str = "registered"
    attachments: list[dict] | None = None
    found_by_police: bool = False

    @model_validator(mode="after")
    def validate_police_discovery(self) -> "FIRBase":
        if self.found_by_police and not self.investigating_officer_id:
            raise ValueError("Officer is required when the crime is found by police.")
        return self

    @field_validator("attachments", mode="before")
    @classmethod
    def parse_attachments(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

    @field_validator("complainant_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or len(v.strip()) < 3:
            raise ValueError("Complainant name must be at least 3 characters long")
        return v.strip()

    @field_validator("complainant_contact")
    @classmethod
    def validate_contact(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        cleaned = re.sub(r"[\s\-]", "", v.strip())
        if not re.match(r"^(?:\+91)?\d{10}$", cleaned):
            raise ValueError("Complainant contact must be a valid Indian phone number (10 digits)")
        return cleaned

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"registered", "in_progress", "closed"}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


class FIRCreate(FIRBase):
    fir_number: str
    criminal_ids: list[uuid.UUID] = []
    victim_ids: list[uuid.UUID] = []

    @field_validator("fir_number")
    @classmethod
    def validate_fir_number(cls, v: str) -> str:
        if not re.match(r"^FIR-\d{3,4}/[A-Z0-9]{2,10}/\d{4}$", v.strip().upper()):
            raise ValueError("FIR number must follow the format 'FIR-[3-4 digits]/[STATION]/[YEAR]' (e.g. FIR-045/BNG/2026)")
        return v.strip().upper()


class FIRUpdate(BaseModel):
    investigating_officer_id: uuid.UUID | None = None
    status: str | None = None
    narrative: str | None = None
    sections: str | None = None
    complainant_name: str | None = None
    complainant_contact: str | None = None
    criminal_ids: list[uuid.UUID] | None = None
    victim_ids: list[uuid.UUID] | None = None
    attachments: list[dict] | None = None

    @field_validator("complainant_name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if len(v.strip()) < 3:
            raise ValueError("Complainant name must be at least 3 characters long")
        return v.strip()

    @field_validator("complainant_contact")
    @classmethod
    def validate_contact(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        cleaned = re.sub(r"[\s\-]", "", v.strip())
        if not re.match(r"^(?:\+91)?\d{10}$", cleaned):
            raise ValueError("Complainant contact must be a valid Indian phone number (10 digits)")
        return cleaned

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return None
        allowed = {"registered", "in_progress", "closed"}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


class FIROut(FIRBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    fir_number: str
    filed_at: datetime
    created_at: datetime


class FIRDetailOut(FIROut):
    model_config = ConfigDict(from_attributes=True)
    crime_case: CrimeCaseOut | None = None
    investigating_officer: OfficerOut | None = None
    criminals: list[CriminalOut] = []
    victims: list[VictimOut] = []
    evidence: list[EvidenceOut] = []
    attachments: list[dict] = []
    ai_risk_score: int = 50
    ai_analysis_reasons: list[str] = []
