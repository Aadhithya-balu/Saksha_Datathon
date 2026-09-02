"""
Intelligence Engine routes — unified investigation intelligence builder.

Endpoints for building comprehensive intelligence reports, comparing cases,
and searching for entities to start an intelligence analysis from.
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, require_roles
from app.database.postgres import get_db
from app.models.user import User
from app.services import intelligence_engine
from app.services.audit_service import log_action

router = APIRouter(
    prefix="/intelligence",
    tags=["Intelligence Engine"],
    dependencies=[Depends(require_roles(*ALL_ROLES))],
)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class BuildIntelligenceRequest(BaseModel):
    entity_type: str
    entity_id: str


class CompareCasesRequest(BaseModel):
    primary_case_id: str
    compare_case_ids: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/build")
def build_intelligence(
    body: BuildIntelligenceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Build a comprehensive intelligence report for a given entity."""
    try:
        report = intelligence_engine.build_intelligence(db, body.entity_type, body.entity_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Intelligence engine error: {exc}")

    log_action(
        db, current_user, "INTELLIGENCE_BUILD", "IntelligenceReport",
        resource_id=body.entity_id,
        details=f"Intelligence report built for {body.entity_type}:{body.entity_id}",
        metadata_json=f'{{"entity_type":"{body.entity_type}","entity_id":"{body.entity_id}"}}',
    )

    _record_run(db, current_user, body.entity_type, body.entity_id, report)
    db.commit()
    return report


def _record_run(
    db: Session,
    user: User,
    entity_type: str,
    entity_id: str,
    report: dict[str, Any],
) -> None:
    """Persist a compact record of the built report for the user's history."""
    from app.models.intelligence_report import IntelligenceReportRun

    info = report.get("entity_info") or {}
    label = (
        info.get("full_name")
        or info.get("case_number")
        or (f"FIR {info.get('fir_number')}" if info.get("fir_number") else None)
        or f"{entity_type}:{entity_id}"
    )

    cs = report.get("confidence_summary") or {}
    run = IntelligenceReportRun(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=str(label)[:300],
        summary=(report.get("summary") or "")[:2000],
        connections=len(report.get("connections") or []),
        leads=len(report.get("investigation_leads") or []),
        threads=len(report.get("common_threads") or []),
        timeline_events=len(report.get("timeline") or []),
        confirmed=int(cs.get("confirmed", 0)),
        probable=int(cs.get("probable", 0)),
        possible=int(cs.get("possible", 0)),
        created_by_id=user.id,
    )
    db.add(run)


@router.get("/history")
def list_history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's recent intelligence builds (most recent first)."""
    from app.models.intelligence_report import IntelligenceReportRun

    runs = (
        db.query(IntelligenceReportRun)
        .filter(IntelligenceReportRun.created_by_id == current_user.id)
        .order_by(IntelligenceReportRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "entity_label": r.entity_label,
            "summary": r.summary,
            "connections": r.connections,
            "leads": r.leads,
            "threads": r.threads,
            "timeline_events": r.timeline_events,
            "confirmed": r.confirmed,
            "probable": r.probable,
            "possible": r.possible,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]


@router.delete("/history/{run_id}")
def delete_history(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a single history entry owned by the current user."""
    from app.models.intelligence_report import IntelligenceReportRun

    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid run id: {exc}")

    run = (
        db.query(IntelligenceReportRun)
        .filter(IntelligenceReportRun.id == run_uuid)
        .filter(IntelligenceReportRun.created_by_id == current_user.id)
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="History entry not found")
    db.delete(run)
    db.commit()
    return {"deleted": True}


@router.post("/compare")
def compare_cases(
    body: CompareCasesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compare two or more cases side by side."""
    try:
        primary_uuid = uuid.UUID(body.primary_case_id)
        compare_uuids = [uuid.UUID(cid) for cid in body.compare_case_ids]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {exc}")

    try:
        result = intelligence_engine._compare_cases(db, primary_uuid, compare_uuids)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Case comparison error: {exc}")

    log_action(
        db, current_user, "INTELLIGENCE_COMPARE", "CaseComparison",
        resource_id=body.primary_case_id,
        details=f"Compared case {body.primary_case_id} with {len(body.compare_case_ids)} case(s)",
        metadata_json=f'{{"primary":"{body.primary_case_id}","compared_count":{len(body.compare_case_ids)}}}',
    )
    db.commit()
    return result


@router.get("/entity-search")
def entity_search(
    q: str = Query(..., min_length=1, max_length=200),
    entity_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search for entities (criminals, FIRs, cases, victims) to start intelligence from."""
    from app.models.criminal import Criminal
    from app.models.victim import Victim
    from app.models.fir import FIR
    from app.models.crime import CrimeCase

    results: list[dict[str, Any]] = []
    pattern = f"%{q}%"
    want_all = entity_type is None

    if want_all or entity_type == "criminal":
        criminals = db.query(Criminal).filter(
            Criminal.full_name.ilike(pattern) | Criminal.aliases.ilike(pattern)
        ).limit(10).all()
        for c in criminals:
            results.append({
                "id": str(c.id),
                "type": "criminal",
                "name": c.full_name,
                "subtitle": f"Status: {c.status} | Aliases: {c.aliases or 'None'}",
            })

    if want_all or entity_type == "fir":
        firs = db.query(FIR).filter(
            FIR.fir_number.ilike(pattern) | FIR.complainant_name.ilike(pattern)
        ).limit(10).all()
        for f in firs:
            results.append({
                "id": str(f.id),
                "type": "fir",
                "name": f"FIR {f.fir_number}",
                "subtitle": f"Complainant: {f.complainant_name} | Sections: {f.sections or 'N/A'}",
            })

    if want_all or entity_type == "case":
        cases = db.query(CrimeCase).filter(
            CrimeCase.case_number.ilike(pattern) | CrimeCase.description.ilike(pattern)
        ).limit(10).all()
        for c in cases:
            results.append({
                "id": str(c.id),
                "type": "case",
                "name": c.case_number,
                "subtitle": f"Status: {c.status} | Priority: {c.priority or 'N/A'}",
            })

    if want_all or entity_type == "victim":
        victims = db.query(Victim).filter(
            Victim.full_name.ilike(pattern)
        ).limit(10).all()
        for v in victims:
            results.append({
                "id": str(v.id),
                "type": "victim",
                "name": v.full_name,
                "subtitle": f"Age: {v.age or 'N/A'} | Gender: {v.gender or 'N/A'}",
            })

    results.sort(key=lambda r: r["name"])
    return {"total": len(results[:10]), "results": results[:10]}
