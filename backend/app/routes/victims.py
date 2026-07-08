"""Victims routes — queries real Victim table."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.victim import Victim
from app.models.user import User

router = APIRouter(prefix="/victims", tags=["Victims"])


@router.get("")
def list_victims(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Victim)
    if q:
        query = query.filter(Victim.VictimName.ilike(f"%{q}%"))
    total = query.count()
    results = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "results": [_out(r) for r in results],
    }


@router.get("/{victim_id}")
def get_victim(victim_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(Victim).filter(Victim.VictimMasterID == victim_id).first()
    if not row:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Victim not found")
    return _out(row)


def _out(r: Victim) -> dict:
    return {
        "id": r.VictimMasterID,
        "case_id": r.CaseMasterID,
        "name": r.VictimName,
        "age": r.AgeYear,
        "gender_id": r.GenderID,
        "is_police": bool(r.VictimPolice),
    }
