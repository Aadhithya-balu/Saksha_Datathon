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

DEMO_HOTSPOTS = [
    {"district_id": "Bengaluru Urban", "name": "Whitefield", "lat": 12.9698, "lng": 77.7500, "score": 91, "category": "Cyber Fraud", "trend": "up"},
    {"district_id": "Bengaluru Urban", "name": "KR Puram", "lat": 13.0056, "lng": 77.6880, "score": 78, "category": "Vehicle Theft", "trend": "up"},
    {"district_id": "Mysuru", "name": "Devaraja Market", "lat": 12.2958, "lng": 76.6394, "score": 65, "category": "Pickpocketing", "trend": "stable"},
    {"district_id": "Mangaluru", "name": "Harbor Port", "lat": 12.9050, "lng": 74.8350, "score": 72, "category": "Narcotics Transit", "trend": "up"},
]

DEMO_RISK_SCORES = {
    "district_id": None,
    "window": "next_7d",
    "grid_predictions": [
        {"district": "Whitefield", "risk_score": 91, "confidence": 0.94},
        {"district": "KR Puram", "risk_score": 78, "confidence": 0.88},
        {"district": "Yeshwanthpur", "risk_score": 72, "confidence": 0.84},
        {"district": "MG Road", "risk_score": 65, "confidence": 0.76},
    ],
    "model_version": "demo-v1",
}

DEMO_ANOMALIES = {
    "anomalies": [
        {"case_id": "CR-2456", "label": "Witness exposure anomaly", "score": 0.91, "reason": "Unexpected location transfer pattern"},
        {"case_id": "CR-2488", "label": "Cyber spike anomaly", "score": 0.87, "reason": "Alert volume exceeds rolling baseline"},
        {"case_id": "CR-2510", "label": "Repeat offender deviation", "score": 0.82, "reason": "Multi-jurisdiction pattern mismatch"},
    ]
}

DEMO_NETWORKS = {
    "SCRB-7740": {
        "nodes": [
            {"id": "node-1", "name": "Ramu \"Kodaikanal\" Swamy", "category": "suspect", "riskScore": 92, "details": "Leader of coordinate interstate break-in gang.", "casesCount": 14, "phone": "+91 94420-12891"},
            {"id": "node-2", "name": "Vikram \"Vicky\" Yadav", "category": "suspect", "riskScore": 88, "details": "Underground money mule coordinator.", "casesCount": 8, "phone": "+91 98845-09228"},
            {"id": "node-3", "name": "Indiranagar Sect-B, Bengaluru", "category": "location", "riskScore": 75, "details": "Hotspot of recurring app-based extortion campaigns.", "casesCount": 22},
            {"id": "node-4", "name": "K. S. Narayanan", "category": "victim", "riskScore": 10, "details": "Complainant in fraud scan.", "casesCount": 1},
        ],
        "edges": [
            {"source": "node-1", "target": "node-3", "relationship": "Last active cell location"},
            {"source": "node-1", "target": "node-4", "relationship": "Targeted in residential extortion"},
            {"source": "node-2", "target": "node-3", "relationship": "Launders app funds"},
            {"source": "node-2", "target": "node-1", "relationship": "Known accomplice association"},
        ],
    },
    "IO-3921": {
        "nodes": [
            {"id": "node-5", "name": "Sayed Ibrahim", "category": "suspect", "riskScore": 84, "details": "Logistics provider for narcotics shipments.", "casesCount": 6, "phone": "+91 99014-38419"},
            {"id": "node-6", "name": "Harbor Gate A, Mangaluru", "category": "location", "riskScore": 68, "details": "Seizure point of multiple consignments.", "casesCount": 11},
            {"id": "node-7", "name": "Dr. Vinay Murthy", "category": "victim", "riskScore": 12, "details": "Witness in Mysuru break-in.", "casesCount": 1},
        ],
        "edges": [
            {"source": "node-5", "target": "node-6", "relationship": "Smuggles chemical contraband"},
            {"source": "node-5", "target": "node-7", "relationship": "Case-linked communication overlap"},
        ],
    },
}


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
        answer=f"Demo analyst response for: {payload.message}",
        data=[{"query": payload.message, "summary": "Natural-language retrieval is wired to the backend contract."}],
        sources=["dashboard.summary", "ai_support.chat_query"],
        chart_suggestion="bar",
    )


@router.get("/predictions/risk-scores")
def risk_scores(district_id: str | None = None, window: str = "next_7d", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Demo risk scoring payload that keeps the frontend contract stable."""
    payload = dict(DEMO_RISK_SCORES)
    payload["district_id"] = district_id
    payload["window"] = window
    return payload


@router.get("/predictions/anomalies")
def anomalies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Demo anomaly payload that keeps the frontend contract stable."""
    return DEMO_ANOMALIES


@router.get("/hotspots")
def hotspots(district_id: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Demo hotspot payload that keeps the frontend contract stable."""
    hotspots = DEMO_HOTSPOTS
    if district_id:
        hotspots = [item for item in hotspots if item["district_id"] == district_id]
    return {"hotspots": hotspots}


@router.get("/network/person/{person_id}")
def network_person(person_id: str, depth: int = 1, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Demo network payload that keeps the frontend contract stable."""
    return DEMO_NETWORKS.get(person_id, DEMO_NETWORKS["SCRB-7740"])
