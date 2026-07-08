"""Auth service — authenticates against real Employee table using KGID + PIN."""
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.officer import Officer


# Map RankID → role string used in JWT and RBAC
RANK_ROLE_MAP = {
    1: "admin",           # Director General of Police
    2: "admin",           # Additional Director General
    3: "policymaker",     # Inspector General of Police
    4: "policymaker",     # Deputy Inspector General
    5: "policymaker",     # Superintendent of Police
    6: "policymaker",     # Additional SP
    7: "crime_analyst",   # Deputy SP
    8: "crime_analyst",   # Inspector
    9: "investigator",    # Sub-Inspector
    10: "investigator",   # Assistant Sub-Inspector
    11: "investigator",   # Head Constable
    12: "investigator",   # Constable
}


@dataclass
class EmployeeSession:
    """Lightweight session object that mimics the old User model interface."""
    username: str       # KGID
    full_name: str
    role_name: str
    district: str | None
    station: str | None
    is_active: bool = True

    @property
    def role(self):
        class _Role:
            def __init__(self, name): self.name = name
        return _Role(self.role_name)


def _get_pin(kgid: str) -> str:
    """Derive 6-digit PIN from KGID — last 6 numeric characters."""
    digits = ''.join(c for c in kgid if c.isdigit())
    return digits[-6:] if len(digits) >= 6 else digits.zfill(6)


def authenticate_user(db: Session, username: str, password: str) -> EmployeeSession:
    kgid = username.strip().upper()
    employee = db.query(Officer).filter(Officer.KGID == kgid).first()

    if not employee:
        raise UnauthorizedException("Incorrect KGID or PIN")

    expected_pin = _get_pin(kgid)
    if password.strip() != expected_pin:
        raise UnauthorizedException("Incorrect KGID or PIN")

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


def issue_tokens(session: EmployeeSession) -> dict:
    access_token = create_access_token(subject=session.username, role=session.role_name)
    refresh_token = create_refresh_token(subject=session.username)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


def refresh_access_token(db: Session, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise UnauthorizedException("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException("Provided token is not a refresh token")

    kgid = payload.get("sub")
    employee = db.query(Officer).filter(Officer.KGID == kgid).first()
    if not employee:
        raise UnauthorizedException("Employee not found")

    role_name = RANK_ROLE_MAP.get(employee.RankID, "investigator")
    session = EmployeeSession(
        username=kgid,
        full_name=employee.FirstName,
        role_name=role_name,
        district=None,
        station=None,
    )
    return issue_tokens(session)
