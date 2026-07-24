"""Administrative APIs for users, RBAC roles, audit logs, and persisted settings."""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import JSON, Boolean, String, Text, asc, desc, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, require_roles
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.core.security import hash_password
from app.database.postgres import Base, engine, get_db
from app.models.audit_log import AuditLog
from app.models.role import Role
from app.models.user import User
from app.services import audit_service

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_roles(ROLE_ADMIN))])

PERMISSIONS = {
    "dashboard:view",
    "cases:view", "cases:create", "cases:update", "cases:delete",
    "firs:view", "firs:create", "firs:update", "firs:delete",
    "criminals:view", "criminals:create", "criminals:update", "criminals:delete",
    "evidence:view", "evidence:create", "evidence:update", "evidence:delete", "evidence:export",
    "reports:view", "reports:generate", "reports:export",
    "admin:users", "admin:roles", "admin:audit", "admin:settings",
    "ai:view", "network:view",
}

DEFAULT_ROLE_PERMISSIONS = {
    "admin": sorted(PERMISSIONS),
    "crime_analyst": ["dashboard:view", "cases:view", "criminals:view", "evidence:view", "reports:view", "reports:generate", "reports:export", "ai:view", "network:view"],
    "investigator": ["dashboard:view", "cases:view", "cases:update", "firs:view", "firs:create", "firs:update", "criminals:view", "evidence:view", "evidence:create", "evidence:update", "reports:view"],
    "inspector": ["dashboard:view", "cases:view", "cases:update", "firs:view", "criminals:view", "evidence:view", "reports:view", "reports:export"],
    "forensic": ["dashboard:view", "cases:view", "evidence:view", "evidence:create", "evidence:update", "evidence:export", "reports:view"],
    "policymaker": ["dashboard:view", "cases:view", "reports:view", "reports:export", "ai:view"],
    "viewer": ["dashboard:view", "cases:view", "criminals:view", "reports:view"],
}


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(nullable=True)


class AdminUserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    full_name: str
    is_active: bool
    district: str | None
    station: str | None
    role_id: uuid.UUID
    role: str
    created_at: datetime


class UserCreatePayload(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: str
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role_id: uuid.UUID | None = None
    role: str | None = None
    district: str | None = Field(default=None, max_length=100)
    station: str | None = Field(default=None, max_length=100)
    is_active: bool = True


class UserUpdatePayload(BaseModel):
    email: str | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    role_id: uuid.UUID | None = None
    role: str | None = None
    district: str | None = Field(default=None, max_length=100)
    station: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


class PasswordResetPayload(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class RolePayload(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] = Field(default_factory=list)


class SettingsPayload(BaseModel):
    general: dict[str, Any] = Field(default_factory=dict)
    organization: dict[str, Any] = Field(default_factory=dict)
    security: dict[str, Any] = Field(default_factory=dict)
    password_policy: dict[str, Any] = Field(default_factory=dict)
    report_defaults: dict[str, Any] = Field(default_factory=dict)
    localization: dict[str, Any] = Field(default_factory=dict)
    theme: dict[str, Any] = Field(default_factory=dict)
    backup: dict[str, Any] = Field(default_factory=dict)


def _ensure_admin_tables() -> None:
    if not getattr(_ensure_admin_tables, "_done", False):
        Base.metadata.create_all(bind=engine, tables=[SystemSetting.__table__, RolePermission.__table__])
        _ensure_admin_tables._done = True


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_out(user: User) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        district=user.district,
        station=user.station,
        role_id=user.role_id,
        role=user.role.name if user.role else "",
        created_at=user.created_at,
    )


def _resolve_role(db: Session, role_id: uuid.UUID | None, role_name: str | None) -> Role:
    query = db.query(Role)
    role = query.filter(Role.id == role_id).first() if role_id else query.filter(Role.name == role_name).first()
    if not role:
        raise NotFoundException("Role not found")
    return role


def _validate_permissions(permissions: list[str]) -> list[str]:
    normalized = sorted({permission.strip() for permission in permissions if permission.strip()})
    invalid = [permission for permission in normalized if permission not in PERMISSIONS]
    if invalid:
        raise ForbiddenException(f"Invalid permissions: {', '.join(invalid)}")
    return normalized


def _get_permissions(db: Session, role_id: uuid.UUID, role_name: str) -> list[str]:
    _ensure_admin_tables()
    persisted = db.query(RolePermission.permission).filter(RolePermission.role_id == role_id).all()
    if persisted:
        return sorted(row[0] for row in persisted)
    return DEFAULT_ROLE_PERMISSIONS.get(role_name, [])


def _set_permissions(db: Session, role: Role, permissions: list[str]) -> None:
    _ensure_admin_tables()
    db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
    for permission in _validate_permissions(permissions):
        db.add(RolePermission(role_id=role.id, permission=permission, resource=permission.split(":")[0] if ":" in permission else permission))


def _safe_settings(payload: SettingsPayload) -> dict[str, Any]:
    data = payload.model_dump()
    timeout = data["security"].get("session_timeout_minutes")
    if timeout is not None and (not isinstance(timeout, int) or timeout < 5 or timeout > 1440):
        raise ForbiddenException("Session timeout must be between 5 and 1440 minutes")
    min_length = data["password_policy"].get("minimum_length")
    if min_length is not None and (not isinstance(min_length, int) or min_length < 8 or min_length > 128):
        raise ForbiddenException("Password minimum length must be between 8 and 128")
    retention = data["backup"].get("retention_days")
    if retention is not None and (not isinstance(retention, int) or retention < 1 or retention > 3650):
        raise ForbiddenException("Backup retention must be between 1 and 3650 days")
    return data


@router.get("/permissions")
def list_permissions(current_user: User = Depends(get_current_user)):
    return {"permissions": sorted(PERMISSIONS)}


@router.get("/users")
def list_users(
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    columns = {"username": User.username, "email": User.email, "full_name": User.full_name, "created_at": User.created_at}
    query = db.query(User).join(Role)
    if search:
        query = query.filter(or_(User.username.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"), User.full_name.ilike(f"%{search}%")))
    if role:
        query = query.filter(Role.name == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    total = query.count()
    order = asc if sort_order == "asc" else desc
    items = query.order_by(order(columns.get(sort_by, User.created_at))).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "results": [_user_out(item).model_dump(mode="json") for item in items]}


@router.post("/users", status_code=201)
def create_user(payload: UserCreatePayload, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    role = _resolve_role(db, payload.role_id, payload.role)
    user = User(
        username=payload.username.strip(),
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
        role_id=role.id,
        district=payload.district,
        station=payload.station,
        is_active=payload.is_active,
    )
    try:
        db.add(user)
        db.flush()
        audit_service.log_action(db, current_user, "USER_CREATE", "User", str(user.id), ip_address=_client_ip(request))
        db.commit()
        db.refresh(user)
        return _user_out(user)
    except IntegrityError:
        db.rollback()
        raise ConflictException("Username or email already exists")


@router.put("/users/{user_id}")
def update_user(user_id: uuid.UUID, payload: UserUpdatePayload, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User not found")
    updates = payload.model_dump(exclude_unset=True)
    if "role" in updates or "role_id" in updates:
        user.role_id = _resolve_role(db, updates.get("role_id"), updates.get("role")).id
    for field in ("email", "full_name", "district", "station", "is_active"):
        if field in updates:
            setattr(user, field, updates[field].lower() if field == "email" and updates[field] else updates[field])
    try:
        db.add(user)
        db.flush()
        audit_service.log_action(db, current_user, "USER_UPDATE", "User", str(user.id), details=str(sorted(updates.keys())), ip_address=_client_ip(request))
        db.commit()
        db.refresh(user)
        return _user_out(user)
    except IntegrityError:
        db.rollback()
        raise ConflictException("Email already exists")


@router.delete("/users/{user_id}")
def delete_user(user_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User not found")
    if user.id == current_user.id:
        raise ForbiddenException("You cannot deactivate your own account")
    user.is_active = False
    audit_service.log_action(db, current_user, "USER_DELETE", "User", str(user.id), details="soft_delete", ip_address=_client_ip(request))
    db.commit()
    return {"message": "User deactivated"}


@router.post("/users/{user_id}/activate")
def activate_user(user_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User not found")
    user.is_active = True
    audit_service.log_action(db, current_user, "USER_ACTIVATE", "User", str(user.id), ip_address=_client_ip(request))
    db.commit()
    return {"message": "User activated"}


@router.post("/users/{user_id}/deactivate")
def deactivate_user(user_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_id == current_user.id:
        raise ForbiddenException("You cannot deactivate your own account")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User not found")
    user.is_active = False
    audit_service.log_action(db, current_user, "USER_DEACTIVATE", "User", str(user.id), ip_address=_client_ip(request))
    db.commit()
    return {"message": "User deactivated"}


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: uuid.UUID, payload: PasswordResetPayload, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User not found")
    user.hashed_password = hash_password(payload.password)
    audit_service.log_action(db, current_user, "USER_PASSWORD_RESET", "User", str(user.id), ip_address=_client_ip(request))
    db.commit()
    return {"message": "Password reset"}


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    roles = db.query(Role).order_by(Role.name).all()
    return {"results": [{"id": str(role.id), "name": role.name, "description": role.description, "permissions": _get_permissions(db, role.id, role.name), "user_count": len(role.users)} for role in roles]}


@router.post("/roles", status_code=201)
def create_role(payload: RolePayload, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    role = Role(name=payload.name.strip(), description=payload.description)
    try:
        db.add(role)
        db.flush()
        _set_permissions(db, role, payload.permissions)
        audit_service.log_action(db, current_user, "ROLE_CREATE", "Role", str(role.id), ip_address=_client_ip(request))
        db.commit()
        return {"id": str(role.id), "name": role.name, "description": role.description, "permissions": _get_permissions(db, role.id, role.name)}
    except IntegrityError:
        db.rollback()
        raise ConflictException("Role already exists")


@router.put("/roles/{role_id}")
def update_role(role_id: uuid.UUID, payload: RolePayload, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise NotFoundException("Role not found")
    if role.name in ALL_ROLES and payload.name != role.name:
        raise ForbiddenException("Built-in role names cannot be changed")
    role.name = payload.name.strip()
    role.description = payload.description
    _set_permissions(db, role, payload.permissions)
    audit_service.log_action(db, current_user, "ROLE_UPDATE", "Role", str(role.id), details="permissions_updated", ip_address=_client_ip(request))
    db.commit()
    return {"id": str(role.id), "name": role.name, "description": role.description, "permissions": _get_permissions(db, role.id, role.name)}


@router.delete("/roles/{role_id}")
def delete_role(role_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise NotFoundException("Role not found")
    if role.name in ALL_ROLES or role.users:
        raise ForbiddenException("Role is built-in or assigned to users")
    db.delete(role)
    audit_service.log_action(db, current_user, "ROLE_DELETE", "Role", str(role.id), ip_address=_client_ip(request))
    db.commit()
    return {"message": "Role deleted"}


@router.post("/users/{user_id}/roles/{role_id}")
def assign_role(user_id: uuid.UUID, role_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    role = db.query(Role).filter(Role.id == role_id).first()
    if not user or not role:
        raise NotFoundException("User or role not found")
    user.role_id = role.id
    audit_service.log_action(db, current_user, "ROLE_ASSIGN", "User", str(user.id), details=role.name, ip_address=_client_ip(request))
    db.commit()
    return {"message": "Role assigned"}


@router.delete("/users/{user_id}/roles")
def remove_role(user_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    viewer = db.query(Role).filter(Role.name == "viewer").first()
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not viewer:
        raise NotFoundException("User or fallback role not found")
    user.role_id = viewer.id
    audit_service.log_action(db, current_user, "ROLE_REMOVE", "User", str(user.id), details="viewer", ip_address=_client_ip(request))
    db.commit()
    return {"message": "Role removed"}


@router.get("/audit-logs")
def list_audit_logs(
    search: str | None = None,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(AuditLog).join(User)
    if search:
        query = query.filter(or_(AuditLog.action.ilike(f"%{search}%"), AuditLog.resource_type.ilike(f"%{search}%"), AuditLog.details.ilike(f"%{search}%"), User.full_name.ilike(f"%{search}%")))
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if date_from:
        query = query.filter(AuditLog.timestamp >= date_from)
    if date_to:
        query = query.filter(AuditLog.timestamp <= date_to)
    total = query.count()
    items = query.order_by(desc(AuditLog.timestamp)).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [{
            "id": str(item.id),
            "timestamp": item.timestamp.isoformat() if item.timestamp else None,
            "user": item.user.full_name if item.user else "",
            "role": item.user.role.name if item.user and item.user.role else "",
            "action": item.action,
            "module": item.resource_type,
            "record_id": item.resource_id,
            "status": "success",
            "ip": item.ip_address,
            "user_agent": None,
            "details": item.details,
        } for item in items],
    }


@router.get("/audit-logs/export")
def export_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(AuditLog).join(User).order_by(desc(AuditLog.timestamp)).limit(5000).all()
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer)
    writer.writerow(["timestamp", "user", "role", "action", "module", "record_id", "status", "ip", "details"])
    for item in rows:
        writer.writerow([item.timestamp, item.user.full_name if item.user else "", item.user.role.name if item.user and item.user.role else "", item.action, item.resource_type, item.resource_id, "success", item.ip_address, item.details])
    return Response(content=buffer.getvalue().encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="saksha_audit_logs.csv"'})


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_admin_tables()
    import json as _json
    row = db.query(SystemSetting).filter(SystemSetting.key == "platform").first()
    if row and row.value:
        try:
            return _json.loads(row.value)
        except Exception:
            return SettingsPayload().model_dump()
    return SettingsPayload().model_dump()


@router.put("/settings")
def save_settings(payload: SettingsPayload, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_admin_tables()
    import json as _json
    value = _safe_settings(payload)
    row = db.query(SystemSetting).filter(SystemSetting.key == "platform").first()
    if not row:
        row = SystemSetting(key="platform", value=_json.dumps(value))
    else:
        row.value = _json.dumps(value)
    row.updated_at = datetime.utcnow()
    db.add(row)
    audit_service.log_action(db, current_user, "SETTINGS_UPDATE", "SystemSettings", "platform", ip_address=_client_ip(request))
    db.commit()
    return value
