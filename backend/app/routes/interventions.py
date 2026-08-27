"""Intervention routes — evidence-based prevention loop (gap M7).

Log proactive interventions and measure their effect via pre/post crime
trend comparison per district.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import (
    ALL_ROLES,
    ROLE_ADMIN,
    ROLE_INSPECTOR,
    ROLE_INVESTIGATOR,
    ROLE_POLICYMAKER,
    require_roles,
)
from app.database.postgres import get_db
from app.models.intervention import Intervention
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.intervention import (
    InterventionCreate,
    InterventionListResponse,
    InterventionOut,
    InterventionUpdate,
)
from app.services import audit_service, intervention_service

router = APIRouter(
    prefix="/interventions",
    tags=["Interventions"],
    dependencies=[Depends(require_roles(*ALL_ROLES))],
)


@router.get("", response_model=InterventionListResponse)
def list_interventions(
    district: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Intervention)
    if district:
        query = query.filter(Intervention.district.ilike(f"%{district}%"))
    if status:
        query = query.filter(Intervention.status == status)
    total = query.count()
    rows = (
        query.order_by(Intervention.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": rows,
        "interventions": rows,
    }


@router.post(
    "",
    response_model=InterventionOut,
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_INSPECTOR, ROLE_POLICYMAKER))],
)
def create_intervention(
    payload: InterventionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    intervention = Intervention(**payload.model_dump(), created_by_id=current_user.id)
    db.add(intervention)
    db.flush()
    audit_service.log_action(db, current_user, "CREATE", "Intervention", str(intervention.id), details=payload.title)
    db.commit()
    db.refresh(intervention)
    return intervention


@router.get("/{intervention_id}", response_model=InterventionOut)
def get_intervention(
    intervention_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Intervention).filter(Intervention.id == intervention_id).first()


@router.put(
    "/{intervention_id}",
    response_model=InterventionOut,
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR, ROLE_INSPECTOR, ROLE_POLICYMAKER))],
)
def update_intervention(
    intervention_id: uuid.UUID,
    payload: InterventionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    intervention = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if intervention is None:
        from fastapi.responses import Response

        return Response(status_code=404, content="Intervention not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(intervention, field, value)
    audit_service.log_action(db, current_user, "UPDATE", "Intervention", str(intervention_id))
    db.commit()
    db.refresh(intervention)
    return intervention


@router.get("/{intervention_id}/effectiveness")
def intervention_effectiveness(
    intervention_id: uuid.UUID,
    window_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pre/post crime-count comparison around the intervention window."""
    intervention = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if intervention is None:
        from fastapi.responses import Response

        return Response(status_code=404, content="Intervention not found")
    result = intervention_service.compute_effectiveness(db, intervention, window_days=window_days)
    db.commit()
    return result
