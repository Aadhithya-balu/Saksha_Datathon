"""
Investigation service — compiles full investigation context for a crime case.

Aggregates data from CrimeCase, FIRs, Criminals, Evidence, and AuditLog
into a single unified investigation interface response.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.audit_log import AuditLog
from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.evidence import Evidence
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.officer import Officer
from app.models.investigation_note import InvestigationNote
from app.models.chain_of_custody import ChainOfCustody



# ── Data classes for structured output ─────────────────────────

@dataclass
class InvestigationOfficer:
    id: str
    badge_number: str
    rank: str | None
    full_name: str
    district: str
    station: str


@dataclass
class InvestigationCase:
    id: str
    case_number: str
    description: str | None
    mo_tags: str | None
    status: str
    priority: str
    progress: int
    occurred_at: str
    reported_at: str
    created_at: str
    assigned_officer: InvestigationOfficer | None


@dataclass
class InvestigationFIR:
    id: str
    fir_number: str
    complainant_name: str
    complainant_contact: str | None
    sections: str | None
    status: str
    filed_at: str
    narrative: str | None
    criminals: list[dict]
    victims: list[dict]


@dataclass
class InvestigationCriminal:
    id: str
    full_name: str
    aliases: str | None
    gender: str | None
    date_of_birth: str | None
    identifying_marks: str | None
    mo_summary: str | None
    status: str
    risk_score: int
    linked_fir_count: int


@dataclass
class InvestigationEvidence:
    id: str
    evidence_type: str
    description: str | None
    file_url: str | None
    collected_by: str | None
    chain_of_custody: str | None
    created_at: str


@dataclass
class InvestigationTimelineEvent:
    timestamp: str
    event: str
    actor: str | None
    category: str  # case / fir / evidence / status / note


@dataclass
class InvestigationAIRecommendation:
    type: str
    title: str
    description: str
    priority: str  # high / medium / low


@dataclass
class InvestigationHistoryEntry:
    timestamp: str
    action: str
    resource_type: str
    details: str | None
    officer_name: str | None
    officer_badge: str | None


@dataclass
class InvestigationData:
    case: InvestigationCase
    firs: list[InvestigationFIR]
    criminals: list[InvestigationCriminal]
    evidence: list[InvestigationEvidence]
    timeline: list[InvestigationTimelineEvent]
    ai_recommendations: list[InvestigationAIRecommendation]
    history: list[InvestigationHistoryEntry]


def _calculate_criminal_risk(criminal: Criminal, fir_count: int) -> int:
    """Calculate a simple risk score for a criminal based on attributes."""
    score = 35
    if fir_count >= 3:
        score += 25
    elif fir_count >= 2:
        score += 15
    else:
        score += 5

    if criminal.status == "at_large":
        score += 20
    elif criminal.status == "arrested":
        score -= 10

    if criminal.mo_summary:
        mo_words = len(criminal.mo_summary.split())
        score += min(15, mo_words * 2)

    return min(100, max(5, score))


def _generate_ai_recommendations(case: CrimeCase, firs: list[FIR], evidence: list[Evidence]) -> list[InvestigationAIRecommendation]:
    """Generate AI recommendations based on case data patterns."""
    recommendations = []

    # Check severity-based recommendations
    if case.category and case.category.severity == "high":
        recommendations.append(InvestigationAIRecommendation(
            type="priority",
            title="High Severity Alert",
            description="This case is classified as high severity. Prioritize resource allocation and periodic review.",
            priority="high",
        ))

    # Evidence recommendations
    if evidence:
        digital_evidence = [e for e in evidence if e.evidence_type == "digital" or e.evidence_type == "document"]
        if digital_evidence:
            recommendations.append(InvestigationAIRecommendation(
                type="evidence",
                title="Digital Forensics Required",
                description=f"{len(digital_evidence)} digital/document evidence items require forensic analysis.",
                priority="medium",
            ))
    else:
        recommendations.append(InvestigationAIRecommendation(
            type="evidence",
            title="Evidence Collection Needed",
            description="No evidence has been logged for this case. Initiate evidence collection immediately.",
            priority="high",
        ))

    # FIR-based recommendations
    open_firs = [f for f in firs if f.status != "closed"]
    if len(open_firs) > 2:
        recommendations.append(InvestigationAIRecommendation(
            type="workload",
            title="Multiple Open FIRs",
            description=f"{len(open_firs)} FIRs are still open. Consider workload distribution.",
            priority="medium",
        ))

    # Case stale check
    if case.reported_at:
        days_open = (datetime.now(timezone.utc) - case.reported_at).days
        if days_open > 30 and case.status not in ("closed", "charge sheet filed"):
            recommendations.append(InvestigationAIRecommendation(
                type="aging",
                title="Aging Case Alert",
                description=f"This case has been open for {days_open} days. Review progress and consider escalation.",
                priority="high",
            ))

    # MO pattern recommendations
    if case.mo_tags:
        tag_count = len([t for t in case.mo_tags.split(",") if t.strip()])
        if tag_count >= 3:
            recommendations.append(InvestigationAIRecommendation(
                type="pattern",
                title="Complex MO Pattern",
                description=f"{tag_count} modus operandi tags detected. Cross-reference with district crime database.",
                priority="medium",
            ))

    # Default recommendation if none generated
    if not recommendations:
        recommendations.append(InvestigationAIRecommendation(
            type="general",
            title="Standard Investigation Protocol",
            description="Initiate standard investigation procedures: gather evidence, record statements, and verify alibis.",
            priority="medium",
        ))

    return recommendations


def _build_timeline(case: CrimeCase, firs: list[FIR], evidence: list[Evidence], history: list[AuditLog], notes: list[InvestigationNote] = None) -> list[InvestigationTimelineEvent]:
    """Build a chronological timeline from all case events."""
    events: list[InvestigationTimelineEvent] = []

    # Case creation
    events.append(InvestigationTimelineEvent(
        timestamp=case.reported_at.isoformat() if case.reported_at else "",
        event="Case Created",
        actor=None,
        category="case",
    ))

    # FIR registrations
    for fir in firs:
        events.append(InvestigationTimelineEvent(
            timestamp=fir.filed_at.isoformat() if fir.filed_at else "",
            event=f"FIR {fir.fir_number} Registered",
            actor=fir.complainant_name,
            category="fir",
        ))
        if fir.status == "closed":
            events.append(InvestigationTimelineEvent(
                timestamp=fir.created_at.isoformat() if fir.created_at else "",
                event=f"FIR {fir.fir_number} Closed",
                actor=None,
                category="fir",
            ))

    # Evidence collection
    for ev in evidence:
        events.append(InvestigationTimelineEvent(
            timestamp=ev.created_at.isoformat() if ev.created_at else "",
            event=f"Evidence Collected: {ev.evidence_type}",
            actor=ev.created_by,
            category="evidence",
        ))

    # Investigation notes
    if notes:
        for note in notes:
            events.append(InvestigationTimelineEvent(
                timestamp=note.created_at.isoformat() if note.created_at else "",
                event="Investigation Note Added",
                actor=note.officer_name,
                category="note",
            ))

    # Status changes from audit log
    for log in history:
        if log.resource_type == "CrimeCase" and log.action in ("UPDATE",):
            events.append(InvestigationTimelineEvent(
                timestamp=log.timestamp.isoformat() if log.timestamp else "",
                event=f"Case Updated: {log.details or 'Status changed'}",
                actor=log.user.full_name if log.user else None,
                category="status",
            ))

    # Sort by timestamp
    events.sort(key=lambda e: e.timestamp)
    return events



def get_investigation(db: Session, case_id: uuid.UUID) -> InvestigationData:
    """Compile full investigation data for a given crime case."""
    # Load case with all relationships
    case = (
        db.query(CrimeCase)
        .options(
            joinedload(CrimeCase.category),
            joinedload(CrimeCase.location),
            joinedload(CrimeCase.assigned_officer).joinedload(Officer.user),
            selectinload(CrimeCase.firs)
            .selectinload(FIR.criminal_links)
            .joinedload(FIRCriminalLink.criminal),
            selectinload(CrimeCase.firs)
            .selectinload(FIR.victim_links)
            .joinedload(FIRVictimLink.victim),
            joinedload(CrimeCase.evidence),
        )
        .filter(CrimeCase.id == case_id)
        .first()
    )

    if not case:
        raise ValueError(f"Crime case {case_id} not found")

    # ── Assigned Officer ──
    assigned_officer = None
    if case.assigned_officer:
        off = case.assigned_officer
        assigned_officer = InvestigationOfficer(
            id=str(off.id),
            badge_number=off.badge_number,
            rank=off.rank,
            full_name=off.user.full_name if off.user else "Unknown",
            district=off.district,
            station=off.station,
        )

    # ── Case info ──
    case_info = InvestigationCase(
        id=str(case.id),
        case_number=case.case_number,
        description=case.description,
        mo_tags=case.mo_tags,
        status=case.status,
        priority=case.priority or "medium",
        progress=case.progress or 10,
        occurred_at=case.occurred_at.isoformat() if case.occurred_at else "",
        reported_at=case.reported_at.isoformat() if case.reported_at else "",
        created_at=case.created_at.isoformat() if case.created_at else "",
        assigned_officer=assigned_officer,
    )

    # ── FIRs with linked data ──
    firs_list: list[InvestigationFIR] = []
    criminal_map: dict[str, InvestigationCriminal] = {}
    all_evidence: list[Evidence] = list(case.evidence) if case.evidence else []

    for fir in case.firs:
        fir_criminals = []
        fir_victims = []
        for link in fir.criminal_links:
            if link.criminal:
                c = link.criminal
                fir_criminals.append({
                    "id": str(c.id),
                    "full_name": c.full_name,
                    "aliases": c.aliases,
                    "status": c.status,
                })
                # Accumulate unique criminals for the case-level list
                if str(c.id) not in criminal_map:
                    fir_count = len([lk for lk in c.fir_links if lk.fir_id in [f.id for f in case.firs]])
                    criminal_map[str(c.id)] = InvestigationCriminal(
                        id=str(c.id),
                        full_name=c.full_name,
                        aliases=c.aliases,
                        gender=c.gender,
                        date_of_birth=c.date_of_birth.isoformat() if c.date_of_birth else None,
                        identifying_marks=c.identifying_marks,
                        mo_summary=c.mo_summary,
                        status=c.status,
                        risk_score=_calculate_criminal_risk(c, len(c.fir_links)),
                        linked_fir_count=fir_count,
                    )

        for link in fir.victim_links:
            if link.victim:
                v = link.victim
                fir_victims.append({
                    "id": str(v.id),
                    "full_name": v.full_name,
                    "contact_number": v.contact_number,
                    "gender": v.gender,
                    "age": v.age,
                    "statement": v.statement,
                })

        firs_list.append(InvestigationFIR(
            id=str(fir.id),
            fir_number=fir.fir_number,
            complainant_name=fir.complainant_name,
            complainant_contact=fir.complainant_contact,
            sections=fir.sections,
            status=fir.status,
            filed_at=fir.filed_at.isoformat() if fir.filed_at else "",
            narrative=fir.narrative,
            criminals=fir_criminals,
            victims=fir_victims,
        ))

    # ── Evidence list ──
    evidence_list = []
    for ev in all_evidence:
        custody_records = (
            db.query(ChainOfCustody)
            .filter(ChainOfCustody.evidence_id == ev.id)
            .order_by(ChainOfCustody.timestamp.asc())
            .all()
        )
        chain_summary = None
        if custody_records:
            chain_summary = " → ".join(
                f"{c.action} ({c.timestamp.strftime('%Y-%m-%d') if c.timestamp else 'N/A'})"
                for c in custody_records
            )
        evidence_list.append(InvestigationEvidence(
            id=str(ev.id),
            evidence_type=ev.evidence_type,
            description=ev.description,
            file_url=ev.storage_path,
            collected_by=ev.created_by,
            chain_of_custody=chain_summary,
            created_at=ev.created_at.isoformat() if ev.created_at else "",
        ))

    # ── Audit History ──
    audit_logs = (
        db.query(AuditLog)
        .options(joinedload(AuditLog.user))
        .filter(
            AuditLog.resource_id == str(case.id),
            AuditLog.resource_type.in_(["CrimeCase", "FIR", "Evidence"]),
        )
        .order_by(AuditLog.timestamp.desc())
        .limit(50)
        .all()
    )

    history = [
        InvestigationHistoryEntry(
            timestamp=log.timestamp.isoformat() if log.timestamp else "",
            action=log.action,
            resource_type=log.resource_type,
            details=log.details,
            officer_name=log.user.full_name if log.user else None,
            officer_badge=log.user.username if log.user else None,
        )
        for log in audit_logs
    ]

    # ── Timeline ──
    timeline = _build_timeline(case, case.firs, all_evidence, audit_logs, case.notes if hasattr(case, 'notes') else None)


    # ── AI Recommendations ──
    ai_recommendations = _generate_ai_recommendations(case, case.firs, all_evidence)

    return InvestigationData(
        case=case_info,
        firs=firs_list,
        criminals=list(criminal_map.values()),
        evidence=evidence_list,
        timeline=timeline,
        ai_recommendations=ai_recommendations,
        history=history,
    )

