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
        "image_url": victim.image_url,
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


# ---------------------------------------------------------------------------
# Issue #107 — Victim image upload
# ---------------------------------------------------------------------------

from fastapi import UploadFile, File as FastAPIFile, HTTPException  # noqa: E402


@router.post("/{victim_id}/image", dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_INVESTIGATOR))])
def upload_victim_image(
    victim_id: uuid.UUID,
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a profile image for a victim record."""
    from app.services.evidence_service import _upload_to_supabase_storage, UPLOAD_DIR  # noqa: PLC0415
    import os  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415

    victim = victim_crud.get(db, victim_id)
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only JPEG/PNG/WebP images are accepted.")

    ext = os.path.splitext(file.filename or "img.jpg")[1].lower() or ".jpg"
    unique_name = f"{victim_id}_{_uuid.uuid4()}{ext}"
    local_path = UPLOAD_DIR / unique_name
    with open(local_path, "wb") as fh:
        fh.write(file.file.read())

    storage_key = f"persons/victims/{unique_name}"
    storage_url = _upload_to_supabase_storage(str(local_path), storage_key, file.content_type or "image/jpeg")
    if storage_url:
        os.remove(local_path)
        image_url = storage_url
    else:
        image_url = f"/api/v2/victims/{victim_id}/image-file"

    victim.image_url = image_url
    db.add(victim)
    db.commit()
    audit_service.log_action(db, current_user, "IMAGE_UPLOAD", "Victim", str(victim_id))
    return {"image_url": image_url}
