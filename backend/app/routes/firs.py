"""FIR routes — queries real ComplainantDetails, ArrestSurrender, ChargesheetDetails tables."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.fir import ArrestSurrender, ChargesheetDetails, ComplainantDetails
from app.models.user import User

router = APIRouter(prefix="/firs", tags=["FIRs"])


@router.get("")
def list_firs(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ComplainantDetails)
    if q:
        query = query.filter(ComplainantDetails.ComplainantName.ilike(f"%{q}%"))
    total = query.count()
    results = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "results": [_fir_out(r) for r in results],
    }


@router.get("/{fir_id}")
def get_fir(fir_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(ComplainantDetails).filter(ComplainantDetails.ComplainantID == fir_id).first()
    if not row:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("FIR not found")
    return _fir_out(row)


@router.get("/arrests")
def list_arrests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = db.query(ArrestSurrender).count()
    results = db.query(ArrestSurrender).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "results": [_arrest_out(r) for r in results],
    }


@router.get("/chargesheets")
def list_chargesheets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = db.query(ChargesheetDetails).count()
    results = db.query(ChargesheetDetails).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "results": [_cs_out(r) for r in results],
    }


def _fir_out(r: ComplainantDetails) -> dict:
    return {
        "id": r.ComplainantID,
        "case_id": r.CaseMasterID,
        "complainant_name": r.ComplainantName,
        "age": r.AgeYear,
        "gender_id": r.GenderID,
        "occupation_id": r.OccupationID,
        "religion_id": r.ReligionID,
        "caste_id": r.CasteID,
    }


def _arrest_out(r: ArrestSurrender) -> dict:
    return {
        "id": r.ArrestSurrenderID,
        "case_id": r.CaseMasterID,
        "date": str(r.ArrestSurrenderDate) if r.ArrestSurrenderDate else None,
        "accused_id": r.AccusedMasterID,
        "court_id": r.CourtID,
        "is_accused": bool(r.IsAccused),
    }


def _cs_out(r: ChargesheetDetails) -> dict:
    return {
        "id": r.CSID,
        "case_id": r.CaseMasterID,
        "date": str(r.csdate) if r.csdate else None,
        "type": r.cstype,
        "officer_id": r.PolicePersonID,
    }
