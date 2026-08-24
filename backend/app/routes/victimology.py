"""Victimology analytics routes — repeat victimization, vulnerability index (gap M5)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, require_roles
from app.database.postgres import get_db
from app.models.user import User
from app.services import victimology_service

router = APIRouter(
    prefix="/victimology",
    tags=["Victimology"],
    dependencies=[Depends(require_roles(*ALL_ROLES))],
)


@router.get("/overview")
def victimology_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Summary metrics: repeat-victimization rate, exposure bands, criminological framing."""
    return victimology_service.get_victimology_overview(db)


@router.get("/repeat-victims")
def repeat_victims(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Victims with 2+ linked FIRs, flagged via identity-normalized matching."""
    return victimology_service.get_repeat_victims(db)


@router.get("/vulnerability-index")
def vulnerability_index(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """All victims ranked by composite vulnerability score with factor explanations."""
    return victimology_service.get_vulnerability_index(db)
