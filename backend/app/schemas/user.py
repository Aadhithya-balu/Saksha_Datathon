"""User schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    district: str | None = None
    station: str | None = None


class UserCreate(UserBase):
    password: str
    role_name: str  # "investigator" | "crime_analyst" | "policymaker" | "admin"


class UserUpdate(BaseModel):
    full_name: str | None = None
    district: str | None = None
    station: str | None = None
    is_active: bool | None = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    role: str
    created_at: datetime
