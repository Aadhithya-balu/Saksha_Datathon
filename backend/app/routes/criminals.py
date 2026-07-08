"""Accused/Criminals routes — queries real Accused table."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.criminal import Accused
from app.models.user import User

router = APIRouter(prefix="/criminals", tags=["Criminals"])


@router.get("")
def list_criminals(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Accused)
    if q:
        query = query.filter(Accused.AccusedName.ilike(f"%{q}%"))
    total = query.count()
    results = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "results": [_out(r) for r in results],
    }


@router.get("/{accused_id}")
def get_criminal(accused_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(Accused).filter(Accused.AccusedMasterID == accused_id).first()
    if not row:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Accused not found")
    return _out(row)


def _out(r: Accused) -> dict:
    return {
        "id": r.AccusedMasterID,
        "case_id": r.CaseMasterID,
        "name": r.AccusedName,
        "age": r.AgeYear,
        "gender_id": r.GenderID,
        "person_id": r.PersonID,
    }
