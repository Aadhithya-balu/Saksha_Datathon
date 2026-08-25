"""
FastAPI dependencies for extracting and validating the current user from a JWT.
"""
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedException
from app.core.security import decode_token
from app.database.postgres import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v2/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
    except ValueError:
        raise UnauthorizedException("Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedException("Provided token is not an access token")

    # Server-side revocation (logout / incident response): reject tokens whose
    # jti is on the denylist. Single indexed primary-key lookup per request.
    from app.services.auth_service import is_jti_revoked
    if is_jti_revoked(db, payload.get("jti")):
        raise UnauthorizedException("Token has been revoked")

    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise UnauthorizedException("User not found or inactive")
    return user
