"""Victim CRUD routes."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, ROLE_ADMIN, ROLE_INVESTIGATOR, require_roles
from app.database.postgres import get_db
from app.models.victim import Victim
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.victim import VictimCreate, VictimOut, VictimUpdate
from app.ai.inference.refresh import mark_data_changed
from app.services import audit_service
from app.services.base_service import BaseCRUDService

router = APIRouter(prefix="/victims", tags=["Victims"], dependencies=[Depends(require_roles(*ALL_ROLES))])
victim_crud = BaseCRUDService(Victim)


@router.get("", response_model=PaginatedResponse[VictimOut])
def list_victims(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import or_
    query = db.query(Victim)
    if q:
        query = query.filter(
            or_(
                Victim.full_name.ilike(f"%{q}%"),
                Victim.contact_number.ilike(f"%{q}%"),
                Victim.address.ilike(f"%{q}%")
            )
        )
        
    total = query.count()
    query = query.order_by(Victim.created_at.desc())
    results = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "results": results}


@router.get("/{victim_id}")
def get_victim(victim_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    victim = victim_crud.get(db, victim_id)
    
    # Retrieve linked FIRs
    linked_firs = []
    for link in victim.fir_links:
        fir = link.fir
        if fir:
            case = fir.crime_case
            linked_firs.append({
                "id": str(fir.id),
                "fir_number": fir.fir_number,
                "complainant_name": fir.complainant_name,
                "status": fir.status,
                "filed_at": fir.filed_at.isoformat() if fir.filed_at else None,
                "sections": fir.sections,
                "crime_case_id": str(case.id) if case else None,
                "crime_case_number": case.case_number if case else None,
            })
            
    # Load relationship viewer network data
    try:
        from app.services.analytics_service import network_person
        net_res = network_person(db, f"victim-{victim_id}")
    except Exception:
        net_res = {"nodes": [], "edges": []}
        
    return {
        "id": str(victim.id),
        "full_name": victim.full_name,
        "contact_number": victim.contact_number,
        "address": victim.address,
        "gender": victim.gender,
        "age": victim.age,
        "statement": victim.statement,
        "created_at": victim.created_at.isoformat() if victim.created_at else None,
        "neo4j_node_id": victim.neo4j_node_id,
        "firs": linked_firs,
        "network": net_res
    }


@router.post("", response_model=VictimOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def create_victim(payload: VictimCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    victim = victim_crud.create(db, payload.model_dump())
    audit_service.log_action(db, current_user, "CREATE", "Victim", str(victim.id))
    mark_data_changed("victim", db=db)
    return victim


@router.put("/{victim_id}", response_model=VictimOut, dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def update_victim(victim_id: uuid.UUID, payload: VictimUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    victim = victim_crud.update(db, victim_id, payload.model_dump(exclude_unset=True))
    audit_service.log_action(db, current_user, "UPDATE", "Victim", str(victim_id))
    mark_data_changed("victim", db=db)
    return victim
