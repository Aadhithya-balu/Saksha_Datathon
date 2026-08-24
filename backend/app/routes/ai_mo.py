"""AI modus-operandi routes — semantic MO similarity search + narrative NER (gap M6)."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import (
    ROLE_ADMIN,
    ROLE_CRIME_ANALYST,
    ROLE_INSPECTOR,
    ROLE_INVESTIGATOR,
    require_roles,
)
from app.database.postgres import get_db
from app.models.user import User
from app.services.mo_semantic_service import extract_case_entities, extract_entities, search_similar_mo

router = APIRouter(
    prefix="/ai/mo",
    tags=["AI Modus Operandi"],
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_CRIME_ANALYST, ROLE_INVESTIGATOR, ROLE_INSPECTOR))],
)


@router.get("/search")
def semantic_mo_search(
    q: str = Query(..., min_length=2),
    k: int = Query(10, ge=1, le=50),
    kinds: str | None = Query(None, description="Comma list: criminal,crime_case,fir"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Semantic similarity search over MO summaries and case/FIR narratives.

    Uses TF-IDF + LSA embeddings (scikit-learn), so paraphrases match even when
    wording differs — unlike the legacy substring ILIKE search.
    """
    kind_list = [k.strip() for k in kinds.split(",") if k.strip()] if kinds else None
    return search_similar_mo(db, q.strip(), top_k=k, kinds=kind_list)


class NarrativePayload(BaseModel):
    text: str


@router.post("/extract-entities")
def extract_narrative_entities(
    payload: NarrativePayload,
    current_user: User = Depends(get_current_user),
):
    """Rule-based NER over free text: plates, phones, weapons, places, dates, money."""
    if not payload.text.strip():
        return {"entities": {}, "entity_count": 0}
    return extract_entities(payload.text)


@router.get("/extract-case/{case_id}")
def extract_case_narrative_entities(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract investigative entities from a case's description/MO tags + linked FIR narratives."""
    result = extract_case_entities(db, case_id)
    if result is None:
        return {"error": "Case not found"}
    return result
