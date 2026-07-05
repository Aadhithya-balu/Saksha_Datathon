"""
Role-Based Access Control.
Usage in a route:
    @router.get("/x", dependencies=[Depends(require_roles("admin", "crime_analyst"))])
"""
from fastapi import Depends

from app.auth.dependencies import get_current_user
from app.core.exceptions import ForbiddenException
from app.models.user import User

# Canonical role set for SAKSHA
ROLE_ADMIN = "admin"
ROLE_CRIME_ANALYST = "crime_analyst"
ROLE_INVESTIGATOR = "investigator"
ROLE_POLICYMAKER = "policymaker"

ALL_ROLES = [ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, ROLE_POLICYMAKER]


def require_roles(*allowed_roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in allowed_roles:
            raise ForbiddenException(
                f"Role '{current_user.role.name}' is not permitted to perform this action"
            )
        return current_user

    return dependency


def require_any_authenticated_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
