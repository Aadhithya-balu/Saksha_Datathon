"""Rule-based AI support endpoints backed by live database records."""
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.user import User
from app.services.analytics_service import (
    anomalies as build_anomalies,
    chat_answer,
    hotspots as build_hotspots,
    network_person as build_network_person,
    offender_dossiers,
    risk_scores as build_risk_scores,
)

router = APIRouter(prefix="/ai", tags=["AI Integration Support"])


class ChatQueryRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatQueryResponse(BaseModel):
    answer: str
    data: list[dict[str, Any]] = []
    sources: list[str] = []
    chart_suggestion: str | None = None


@router.post("/chat/query", response_model=ChatQueryResponse)
def chat_query(payload: ChatQueryRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ChatQueryResponse(**chat_answer(db, payload.message))


@router.get("/predictions/risk-scores")
def risk_scores(
    district_id: str | None = None,
    window: str = "next_7d",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return build_risk_scores(db, district_id=district_id, window=window)


@router.get("/predictions/anomalies")
def anomalies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return build_anomalies(db)


@router.get("/hotspots")
def hotspots(district_id: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return build_hotspots(db, district_id=district_id)


@router.get("/offenders/dossiers")
def offenders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"offenders": offender_dossiers(db)}


@router.get("/network/person/{person_id}")
def network_person(person_id: str, depth: int = 1, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return build_network_person(db, person_id=person_id, depth=depth)
