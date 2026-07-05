"""
Phase 3 — AI Integration Support.

These endpoints are the *contract* the AI/ML team's models plug into.
Backend owns data access + response shape; the AI/ML team's model logic
lives in app/services/*_ai_service.py and is called from here. Until the
real models are wired in, each endpoint returns a clearly-marked stub
response so the frontend can be built against a stable contract today.
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.postgres import get_db
from app.models.user import User

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
    """
    TODO(AI team): replace stub with RAG pipeline call
    (embed query -> retrieve from vector store -> call LLM -> return answer).
    """
    return ChatQueryResponse(
        answer="AI chat model not yet integrated. This is a placeholder response.",
        data=[],
        sources=[],
        chart_suggestion=None,
    )


@router.get("/predictions/risk-scores")
def risk_scores(district_id: str | None = None, window: str = "next_7d", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """TODO(AI team): replace with trained risk-scoring model (e.g. XGBoost) output."""
    return {"district_id": district_id, "window": window, "grid_predictions": [], "model_version": "not_integrated"}


@router.get("/predictions/anomalies")
def anomalies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """TODO(AI team): replace with Isolation Forest / LOF anomaly-detection output."""
    return {"anomalies": []}


@router.get("/hotspots")
def hotspots(district_id: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """TODO(AI team): replace with ST-DBSCAN / KDE hotspot clustering output."""
    return {"hotspots": []}


@router.get("/network/person/{person_id}")
def network_person(person_id: str, depth: int = 1, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """TODO(AI/Graph team): replace with Neo4j Cypher traversal + Louvain/Node2Vec output."""
    return {"nodes": [], "edges": []}
