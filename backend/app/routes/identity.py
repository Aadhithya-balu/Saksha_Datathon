"""
Identity Resolution & Proxy Detection routes (issue #225).

Read endpoints are open to all authenticated roles; review / confirm / run
endpoints are gated to investigators + reviewers. All lifecycle changes are
audited so the operator retains full provenance.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, REVIEW_ROLES, require_roles
from app.database.postgres import get_db
from app.models.identity import (
    ALERT_TYPES,
    AUDIT_ALIAS_CONFIRMED,
    AUDIT_MATCH_CONFIRMED,
    AUDIT_MATCH_PROPOSED,
    AUDIT_MATCH_REJECTED,
    AUDIT_PROXY_CONFIRMED,
    ENTITY_KIND_CRIMINAL,
    ENTITY_KIND_VICTIM,
    RELATIONSHIP_STATUSES,
    IdentityAlias,
    IdentityIdentifier,
    IdentityRelationship,
    IntegrityAlert,
    ProxyPattern,
)
from app.models.user import User
from app.models.criminal import Criminal
from app.models.victim import Victim
from app.services import identity_service, proxy_pattern_service
from app.services.audit_service import log_action

router = APIRouter(
    prefix="/identity",
    tags=["Identity Resolution"],
    dependencies=[Depends(require_roles(*ALL_ROLES))],
)

_REVIEW_ROLES_DEP = Depends(require_roles(*REVIEW_ROLES))

_REL_REVIEW_MAP = {
    "confirm_same": ("confirmed_same", AUDIT_MATCH_CONFIRMED),
    "reject": ("rejected", AUDIT_MATCH_REJECTED),
    "possible_proxy": ("marked_proxy", AUDIT_PROXY_CONFIRMED),
    "associated": ("confirmed_association", AUDIT_PROXY_CONFIRMED),
    "alias": ("marked_alias", AUDIT_ALIAS_CONFIRMED),
    "data_error": ("marked_data_error", AUDIT_MATCH_REJECTED),
    "dismiss": ("dismissed", AUDIT_MATCH_REJECTED),
    "investigate": ("in_review", AUDIT_MATCH_PROPOSED),
}


def _relationship_payload(db: Session, rel: IdentityRelationship) -> dict:
    source, target = _resolve_names(db, rel)
    return {
        "id": str(rel.id),
        "source_entity_type": rel.source_entity_type,
        "source_entity_id": str(rel.source_entity_id),
        "target_entity_type": rel.target_entity_type,
        "target_entity_id": str(rel.target_entity_id),
        "relationship_type": rel.relationship_type,
        "assessment": rel.assessment,
        "confidence": rel.confidence,
        "confidence_breakdown": rel.confidence_breakdown,
        "evidence_summary": rel.evidence_summary,
        "status": rel.status,
        "source_name": source,
        "target_name": target,
        "reviewed_by_id": str(rel.reviewed_by_id) if rel.reviewed_by_id else None,
        "reviewed_at": rel.reviewed_at.isoformat() if rel.reviewed_at else None,
        "review_decision": rel.review_decision,
        "review_note": rel.review_note,
        "created_at": rel.created_at.isoformat() if rel.created_at else None,
    }


def _resolve_names(db: Session, rel: IdentityRelationship) -> tuple[str | None, str | None]:
    def _name(entity_type: str, entity_id) -> str | None:
        if entity_type == ENTITY_KIND_CRIMINAL:
            row = db.query(Criminal).get(entity_id)
        else:
            row = db.query(Victim).get(entity_id)
        return row.full_name if row else None
    return _name(rel.source_entity_type, rel.source_entity_id), _name(rel.target_entity_type, rel.target_entity_id)


@router.get("/dashboard")
def identity_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Integrity + identity + proxy summary for the Data Integrity panel."""
    summary = identity_service.integrity_summary(db)
    summary["assessment_counts"] = _assessment_counts(db)
    summary["proxy_pattern_counts"] = _proxy_counts(db)
    return summary


def _assessment_counts(db: Session) -> dict[str, int]:
    from sqlalchemy.sql import func as f
    rows = db.query(IdentityRelationship.assessment, f.count(IdentityRelationship.id)).group_by(
        IdentityRelationship.assessment
    ).all()
    return {a: c for a, c in rows}


def _proxy_counts(db: Session) -> dict[str, int]:
    from sqlalchemy.sql import func as f
    rows = db.query(ProxyPattern.severity, f.count(ProxyPattern.id)).group_by(ProxyPattern.severity).all()
    return {s: c for s, c in rows}


@router.get("/relationships")
def list_relationships(
    status: str | None = Query(default=None),
    assessment: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Proposed identity relationships with filtering + ordering by confidence."""
    q = db.query(IdentityRelationship)
    if status:
        if status not in RELATIONSHIP_STATUSES:
            raise HTTPException(400, f"Unknown status '{status}'")
        q = q.filter(IdentityRelationship.status == status)
    if assessment:
        q = q.filter(IdentityRelationship.assessment == assessment)
    if entity_type and entity_id:
        q = q.filter(
            ((IdentityRelationship.source_entity_type == entity_type)
             & (IdentityRelationship.source_entity_id == entity_id))
            | ((IdentityRelationship.target_entity_type == entity_type)
               & (IdentityRelationship.target_entity_id == entity_id))
        )
    q = q.order_by(IdentityRelationship.confidence.desc()).limit(limit)
    return {"total": None, "results": [_relationship_payload(db, r) for r in q.all()]}


@router.get("/relationships/{relationship_id}")
def relationship_detail(relationship_id: uuid.UUID, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    payload = identity_service.get_relationship_detail(db, relationship_id)
    if payload is None:
        raise HTTPException(404, "Relationship not found")
    return payload


@router.post("/relationships/{relationship_id}/review", dependencies=[_REVIEW_ROLES_DEP])
def review_relationship(
    relationship_id: uuid.UUID,
    decision: str = Query(...),
    note: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply a reviewer decision to a proposed relationship (audited)."""
    if decision not in _REL_REVIEW_MAP:
        raise HTTPException(400, f"Unknown decision '{decision}', expected one of {sorted(_REL_REVIEW_MAP)}")
    rel = db.query(IdentityRelationship).filter(IdentityRelationship.id == relationship_id).first()
    if rel is None:
        raise HTTPException(404, "Relationship not found")
    from datetime import datetime, timezone
    rel.status, audit_action = _REL_REVIEW_MAP[decision]
    rel.reviewed_by_id = current_user.id
    rel.reviewed_at = datetime.now(timezone.utc)
    rel.review_decision = decision
    rel.review_note = note
    db.flush()
    log_action(
        db, current_user, audit_action, "IdentityRelationship", str(rel.id),
        details=f"Relationship {rel.id} marked '{rel.status}' by {current_user.username} ({decision})",
        metadata_json=f'{{"decision":"{decision}","status":"{rel.status}"}}',
    )
    db.commit()
    return _relationship_payload(db, rel)


@router.get("/alerts")
def list_alerts(
    status: str | None = Query(default=None),
    alert_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Integrity alerts (possible duplicates / conflicts / reuse / aliases / proxy)."""
    q = db.query(IntegrityAlert)
    if status:
        q = q.filter(IntegrityAlert.status == status)
    if alert_type:
        if alert_type not in ALERT_TYPES:
            raise HTTPException(400, f"Unknown alert_type '{alert_type}'")
        q = q.filter(IntegrityAlert.alert_type == alert_type)
    q = q.order_by(IntegrityAlert.severity.desc(), IntegrityAlert.created_at.desc()).limit(limit)
    return {"total": None, "results": [_alert_payload(a) for a in q.all()]}


def _alert_payload(a: IntegrityAlert) -> dict:
    return {
        "id": str(a.id),
        "alert_type": a.alert_type,
        "severity": a.severity,
        "entity_a_type": a.entity_a_type,
        "entity_a_id": str(a.entity_a_id) if a.entity_a_id else None,
        "entity_b_type": a.entity_b_type,
        "entity_b_id": str(a.entity_b_id) if a.entity_b_id else None,
        "identifier_type": a.identifier_type,
        "value_hash": a.value_hash,
        "display_value": a.display_value,
        "confidence": a.confidence,
        "description": a.description,
        "observation_count": a.observation_count,
        "status": a.status,
        "source_summary": a.source_summary,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.post("/alerts/{alert_id}/review", dependencies=[_REVIEW_ROLES_DEP])
def review_alert(alert_id: uuid.UUID, decision: str = Query(...), note: str | None = Query(default=None),
                 db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if decision not in {"dismiss", "confirm", "investigate"}:
        raise HTTPException(400, "decision must be one of dismiss|confirm|investigate")
    alert = db.query(IntegrityAlert).filter(IntegrityAlert.id == alert_id).first()
    if alert is None:
        raise HTTPException(404, "Alert not found")
    from datetime import datetime, timezone
    alert.status = "dismissed" if decision == "dismiss" else ("confirmed" if decision == "confirm" else "in_review")
    alert.reviewed_by_id = current_user.id
    alert.reviewed_at = datetime.now(timezone.utc)
    db.flush()
    log_action(
        db, current_user, "INTEGRITY_ALERT_REVIEWED", "IntegrityAlert", str(alert.id),
        details=f"Integrity alert {alert.id} marked '{alert.status}' ({decision})",
        metadata_json=f'{{"decision":"{decision}"}}',
    )
    db.commit()
    return _alert_payload(alert)


@router.get("/identifiers/reuse")
def identifier_reuse(status: str | None = Query(default=None), limit: int = Query(default=100, ge=1, le=500),
                     db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Hashed identifiers reused by 2+ distinct entities."""
    q = db.query(IntegrityAlert).filter(IntegrityAlert.alert_type == "identifier_reuse")
    if status:
        q = q.filter(IntegrityAlert.status == status)
    q = q.order_by(IntegrityAlert.observation_count.desc()).limit(limit)
    return {"total": None, "results": [_alert_payload(a) for a in q.all()]}


@router.get("/aliases")
def list_aliases(entity_type: str | None = Query(default=None), entity_id: uuid.UUID | None = Query(default=None),
                 limit: int = Query(default=100, ge=1, le=500),
                 db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(IdentityAlias)
    if entity_type:
        q = q.filter(IdentityAlias.entity_type == entity_type)
    if entity_id:
        q = q.filter(IdentityAlias.entity_id == entity_id)
    q = q.limit(limit)
    return {"total": None, "results": [
        {
            "id": str(a.id),
            "entity_type": a.entity_type,
            "entity_id": str(a.entity_id),
            "alias_name": a.alias_name,
            "name_type": a.name_type,
            "confidence": a.confidence,
            "source_label": a.source_label,
            "observed_at": a.observed_at.isoformat() if a.observed_at else None,
        } for a in q.all()
    ]}


@router.get("/identifiers")
def list_identifiers(entity_type: str | None = Query(default=None), entity_id: uuid.UUID | None = Query(default=None),
                     identifier_type: str | None = Query(default=None), limit: int = Query(default=100, ge=1, le=500),
                     db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Hashed/masked identity identifier registry (raw values are never returned)."""
    q = db.query(IdentityIdentifier)
    if entity_type:
        q = q.filter(IdentityIdentifier.entity_type == entity_type)
    if entity_id:
        q = q.filter(IdentityIdentifier.entity_id == entity_id)
    if identifier_type:
        q = q.filter(IdentityIdentifier.identifier_type == identifier_type)
    q = q.limit(limit)
    return {"total": None, "results": [
        {
            "id": str(i.id),
            "entity_type": i.entity_type,
            "entity_id": str(i.entity_id),
            "identifier_type": i.identifier_type,
            "value_hash": i.value_hash,
            "display_value": i.display_value,
            "observed_at": i.observed_at.isoformat() if i.observed_at else None,
            "source_label": i.source_label,
        } for i in q.all()
    ]}


@router.get("/graph")
def identity_graph(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Entity ↔ identity link graph for visualization."""
    return identity_service.build_identity_graph(db)


@router.get("/search")
def search_identity(q: str = Query(..., min_length=1, max_length=200),
                    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return identity_service.search_identity(db, q)


# ---------------------------------------------------------------------------
# Resolution + proxy runs
# ---------------------------------------------------------------------------
@router.post("/run", dependencies=[_REVIEW_ROLES_DEP])
def run_resolution(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """(Re)run identity resolution + identifier sync + integrity + proxy scans."""
    written = identity_service.sync_identity_identifiers(db)
    summary = identity_service.run_identity_resolution(db, persist=True, user=current_user)
    reuse = identity_service.detect_identifier_reuse(db)
    proxy = proxy_pattern_service.detect_proxy_patterns(db, persist=True, user=current_user)
    db.commit()
    return {
        "profiles_analyzed": summary["profiles_analyzed"],
        "candidates_generated": summary["candidates_generated"],
        "relationships_proposed": summary["relationships_proposed"],
        "identifier_links_written": written,
        "identifier_reuse_alerts": len(reuse),
        "proxy_patterns_detected": len(proxy),
    }


@router.get("/proxy/rules")
def proxy_rules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """PROXY-001..020 rules catalog (thresholds are configurable)."""
    return {"rules": proxy_pattern_service.rules_catalog(), "thresholds": {
        "min_shared_contact_count": 2,
        "handoff_window_days": 365,
        "repeated_cooccurrence_min": 2,
        "composite_min_categories": 2,
    }}


@router.get("/proxy")
def list_proxy_patterns(status: str | None = Query(default=None),
                        severity: str | None = Query(default=None),
                        limit: int = Query(default=100, ge=1, le=500),
                        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(ProxyPattern)
    if status:
        q = q.filter(ProxyPattern.status == status)
    if severity:
        q = q.filter(ProxyPattern.severity == severity)
    q = q.order_by(ProxyPattern.confidence.desc(), ProxyPattern.created_at.desc()).limit(limit)
    return {"total": None, "results": [_proxy_payload(p) for p in q.all()]}


def _proxy_payload(p: ProxyPattern) -> dict:
    return {
        "id": str(p.id),
        "rule_id": p.rule_id,
        "rule_version": p.rule_version,
        "pattern": p.pattern,
        "severity": p.severity,
        "confidence": p.confidence,
        "assessment": p.assessment,
        "entities": p.entities,
        "evidence": p.evidence,
        "counter_evidence": p.counter_evidence,
        "time_window": p.time_window,
        "explanation": p.explanation,
        "possible_explanations": p.possible_explanations,
        "observation_count": p.observation_count,
        "status": p.status,
        "reviewed_by_id": str(p.reviewed_by_id) if p.reviewed_by_id else None,
        "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
        "review_decision": p.review_decision,
        "review_note": p.review_note,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.get("/proxy/{pattern_id}")
def proxy_detail(pattern_id: uuid.UUID, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    payload = proxy_pattern_service.get_pattern_detail(db, pattern_id)
    if payload is None:
        raise HTTPException(404, "Proxy pattern not found")
    return payload


@router.post("/proxy/{pattern_id}/review", dependencies=[_REVIEW_ROLES_DEP])
def review_proxy(pattern_id: uuid.UUID,
                 decision: str = Query(...),
                 note: str | None = Query(default=None),
                 db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if decision not in {"confirm", "reject", "same_person", "alias", "proxy", "data_error", "dismiss", "investigate"}:
        raise HTTPException(400, "Unknown decision")
    p = db.query(ProxyPattern).filter(ProxyPattern.id == pattern_id).first()
    if p is None:
        raise HTTPException(404, "Proxy pattern not found")
    from datetime import datetime, timezone
    status_map = {
        "confirm": "confirmed",
        "reject": "rejected",
        "same_person": "confirmed_same",
        "alias": "marked_alias",
        "proxy": "marked_proxy",
        "data_error": "marked_data_error",
        "dismiss": "dismissed",
        "investigate": "in_review",
    }
    p.status = status_map[decision]
    p.reviewed_by_id = current_user.id
    p.reviewed_at = datetime.now(timezone.utc)
    p.review_decision = decision
    p.review_note = note
    db.flush()
    audit_action = AUDIT_PROXY_CONFIRMED if decision in {"confirm", "proxy"} else (
        AUDIT_MATCH_CONFIRMED if decision == "same_person" else "PROXY_RELATIONSHIP_REVIEWED")
    log_action(
        db, current_user, audit_action, "ProxyPattern", str(p.id),
        details=f"Proxy pattern {p.id} marked '{p.status}' by {current_user.username} ({decision})",
        metadata_json=f'{{"decision":"{decision}","status":"{p.status}"}}',
    )
    db.commit()
    return _proxy_payload(p)


@router.post("/proxy/run", dependencies=[_REVIEW_ROLES_DEP])
def run_proxy_detection(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """(Re)run the PROXY pattern rules engine."""
    patterns = proxy_pattern_service.detect_proxy_patterns(db, persist=True, user=current_user)
    db.commit()
    return {"patterns_detected": len(patterns), "patterns": patterns}