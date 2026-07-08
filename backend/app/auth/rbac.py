"""Role-Based Access Control."""
from fastapi import Depends

from app.auth.dependencies import get_current_user
from app.core.exceptions import ForbiddenException
from app.services.auth_service import EmployeeSession

ROLE_ADMIN = "admin"
ROLE_CRIME_ANALYST = "crime_analyst"
ROLE_INVESTIGATOR = "investigator"
ROLE_POLICYMAKER = "policymaker"

ALL_ROLES = [ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, ROLE_POLICYMAKER]


def require_roles(*allowed_roles: str):
    def dependency(current_user: EmployeeSession = Depends(get_current_user)) -> EmployeeSession:
        if current_user.role_name not in allowed_roles:
            raise ForbiddenException(
                f"Role '{current_user.role_name}' is not permitted to perform this action"
            )
        return current_user
    return dependency
