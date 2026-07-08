"""Locations routes — queries real District and Unit tables."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.location import District, Unit
from app.models.user import User

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get("/districts")
def list_districts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(District).filter(District.Active == 1).order_by(District.DistrictName).all()
    return [{"id": r.DistrictID, "name": r.DistrictName, "state_id": r.StateID} for r in rows]


@router.get("/units")
def list_units(
    district_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Unit).filter(Unit.Active == 1)
    if district_id:
        query = query.filter(Unit.DistrictID == district_id)
    total = query.count()
    results = query.order_by(Unit.UnitName).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "results": [{"id": r.UnitID, "name": r.UnitName, "district_id": r.DistrictID, "type_id": r.TypeID} for r in results],
    }
