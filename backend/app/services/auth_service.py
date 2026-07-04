"""Business logic for authentication: login, token refresh, password change."""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserCreate


def authenticate_user(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedException("Incorrect username or password")
    if not user.is_active:
        raise UnauthorizedException("Account is deactivated")
    return user


def issue_tokens(user: User) -> dict:
    access_token = create_access_token(subject=user.username, role=user.role.name)
    refresh_token = create_refresh_token(subject=user.username)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


def refresh_access_token(db: Session, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise UnauthorizedException("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Provided token is not a refresh token")

    user = db.query(User).filter(User.username == payload.get("sub")).first()
    if not user or not user.is_active:
        raise UnauthorizedException("User not found or inactive")

    return issue_tokens(user)


def register_user(db: Session, payload: UserCreate) -> User:
    if db.query(User).filter(User.username == payload.username).first():
        raise ConflictException("Username already exists")
    if db.query(User).filter(User.email == payload.email).first():
        raise ConflictException("Email already registered")

    role = db.query(Role).filter(Role.name == payload.role_name).first()
    if not role:
        raise ConflictException(f"Role '{payload.role_name}' does not exist")

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        district=payload.district,
        station=payload.station,
        role_id=role.id,
    )
    db.add(user)
    db.flush()
    return user


def change_password(db: Session, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.hashed_password):
        raise UnauthorizedException("Old password is incorrect")
    user.hashed_password = hash_password(new_password)
    db.add(user)
