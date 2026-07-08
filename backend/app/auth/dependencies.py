"""FastAPI dependencies for extracting and validating the current user from a JWT."""
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedException
from app.core.security import decode_token
from app.database.postgres import get_db
from app.models.officer import Officer
from app.services.auth_service import RANK_ROLE_MAP, EmployeeSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> EmployeeSession:
    try:
        payload = decode_token(token)
    except ValueError:
        raise UnauthorizedException("Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedException("Provided token is not an access token")

    kgid = payload.get("sub")
    employee = db.query(Officer).filter(Officer.KGID == kgid).first()
    if not employee:
        raise UnauthorizedException("Employee not found or inactive")

    role_name = RANK_ROLE_MAP.get(employee.RankID, "investigator")
    district = employee.district.DistrictName if employee.district else None
    unit = employee.unit.UnitName if employee.unit else None

    return EmployeeSession(
        username=kgid,
        full_name=employee.FirstName,
        role_name=role_name,
        district=district,
        station=unit,
    )
