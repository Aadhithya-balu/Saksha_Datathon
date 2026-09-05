"""
Pattern-to-Network Investigation & Evidence Intelligence (issue #250).

Consumes the #249 ``UnifiedIntelligenceResult`` contract and assembles a
provenance-aware investigation view:

    Intelligence Alert -> Related FIRs -> MO/Pattern Matches -> Network Graph
    -> Evidence Drawer -> Why This Insight?

All verification states reuse the existing network vocabulary
(``VerificationStatus`` / ``RelationshipProvenance`` in app.models.network):

- VERIFIED   : records backed directly by the operational database (solid)
- POTENTIAL  : analytical inference (MO similarity, shared-signal leads) (dashed)
- DEMO       : bundled demo-seed records (dotted)
- RESTRICTED : sensitive demo-derived records; only reviewer roles see the
               actual content (lock). Derived from data, never hardcoded.

The module never re-runs pattern detection: it treats the client-supplied
``UnifiedIntelligenceResult`` as the (already verified) source of truth and
only *resolves* its references against the database.
"""
from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.auth.rbac import REVIEW_ROLES
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.evidence import Evidence
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.victim import Victim

# ---------------------------------------------------------------------------
# Sensitive-content markers used to derive RESTRICTED state from real data.
# Kept conservative: only clearly victim-sensitive content (POCSO, sexual
# violence, domestic violence, trafficking, etc.) can ever be RESTRICTED.
# ---------------------------------------------------------------------------

SENSITIVE_CATEGORY_MARKERS = (
    "domestic",
    "sexual",
    "pocso",
    "assault on woman",
    "human trafficking",
    "stalking",
    "obscene",
)

SENSITIVE_TEXT_MARKERS = (
    "pocso",
    "sexual assault",
    "rape",
    "domestic violence",
    "dowry",
    "human trafficking",
    "sexually abused",
    "minor child",
    "molest",
)

SENSITIVE_SECTION_MARKERS = (
    "POCSO",
    "Domestic Violence Act",
    "IPC 376",
    "IPC 354",
    "BNS 64",
    "BNS 74",
)

SAFETY_NOTE = (
    "Analytical relationships are investigative leads, not confirmed guilt or evidence."
)

_VERIFICATION_BY_PROVENANCE: dict[str, str] = {
    "live": "VERIFIED",
    "demo": "DEMO",
    "migrated": "VERIFIED",
    "unknown": "UNVERIFIED",
}


# ---------------------------------------------------------------------------
# Provenance & restricted state derivation
# ---------------------------------------------------------------------------

def _record_provenance(record: Any) -> str:
    """Return the record's dataset_provenance (live/demo/...) or 'unknown'."""
    return str(getattr(record, "dataset_provenance", None) or "unknown").strip().lower()


def is_demo_derived(record: Any) -> bool:
    return _record_provenance(record) == "demo"


def _case_context(record: Any) -> CrimeCase | None:
    """Best-effort case context for a FIR or Evidence record."""
    return getattr(record, "crime_case", None)


def is_sensitive_case(case: CrimeCase | None) -> bool:
    """True when a crime case involves clearly victim-sensitive content."""
    if case is None:
        return False
    category = case.category
    if category is not None and category.name:
        cat_name = category.name.lower()
        if any(marker in cat_name for marker in SENSITIVE_CATEGORY_MARKERS):
            return True
    text = " ".join(filter(None, [
        (case.description or "").lower(),
        (case.mo_tags or "").lower(),
    ]))
    if any(marker in text for marker in SENSITIVE_TEXT_MARKERS):
        return True
    sections = " ".join(fir.sections or "" for fir in (case.firs or []))
    return any(marker in sections for marker in SENSITIVE_SECTION_MARKERS)


def is_restricted_record(record: Any, case: CrimeCase | None = None) -> bool:
    """Deterministic RESTRICTED derivation from data:
    the record must be demo-derived AND involve clearly sensitive content.
    """
    if not is_demo_derived(record):
        return False
    resolved_case = case if case is not None else _case_context(record)
    return is_sensitive_case(resolved_case)


def verification_status_for(
    record: Any,
    *,
    case: CrimeCase | None = None,
    inferred: bool = False,
) -> str:
    """Map a database record to the shared verification vocabulary.

    CLI order: RESTRICTED > DEMO > (POTENTIAL if inferred) > live status.
    """
    if is_restricted_record(record, case):
        return "RESTRICTED"
    provenance = _record_provenance(record)
    if inferred:
        if provenance == "demo":
            return "DEMO"
        return "POTENTIAL"
    return _VERIFICATION_BY_PROVENANCE.get(provenance, "UNVERIFIED")


def provenance_str(record: Any, *, inferred: bool = False) -> str:
    if is_restricted_record(record):
        return "RESTRICTED"
    provenance = _record_provenance(record)
    if inferred:
        return "ANALYTICAL_INFERENCE" if provenance != "demo" else "DEMO_SEED"
    return "DEMO_SEED" if provenance == "demo" else "DIRECT_DATABASE"


# ---------------------------------------------------------------------------
# Reference resolution (fir_number -> records)
# ---------------------------------------------------------------------------

def _resolve_firs(db: Session, fir_numbers: list[str]) -> list[FIR]:
    if not fir_numbers:
        return []
    firs = (
        db.query(FIR)
        .options(
            joinedload(FIR.crime_case).joinedload(CrimeCase.category),
            joinedload(FIR.crime_case).joinedload(CrimeCase.location),
            joinedload(FIR.criminal_links).joinedload(FIRCriminalLink.criminal),
            joinedload(FIR.victim_links).joinedload(FIRVictimLink.victim),
        )
        .filter(FIR.fir_number.in_(fir_numbers))
        .all()
    )
    by_number = {f.fir_number: f for f in firs}
    return [by_number[num] for num in fir_numbers if num in by_number]


def _resolve_entities(db: Session, entity_ids: list[str]) -> list[dict[str, Any]]:
    """Resolve `related_entity_ids` (criminal/victim UUIDs) into entity dicts."""
    entities: list[dict[str, Any]] = []
    valid_ids: list[uuid.UUID] = []
    for raw in entity_ids:
        try:
            valid_ids.append(uuid.UUID(str(raw)))
        except ValueError:
            continue
    if not valid_ids:
        return entities

    criminals = {
        str(c.id): c for c in db.query(Criminal).filter(Criminal.id.in_(valid_ids)).all()
    }
    victims = {
        str(v.id): v for v in db.query(Victim).filter(Victim.id.in_(valid_ids)).all()
    }
    for raw in entity_ids:
        rid = str(raw)
        if rid in criminals:
            c = criminals[rid]
            entities.append({
                "id": rid,
                "node_id": f"criminal-{rid}",
                "entity_type": "criminal",
                "name": c.full_name,
                "role": c.status or "suspect",
                "status": c.status,
                "aliases": c.aliases,
                "mo_summary": c.mo_summary,
                "gang_affiliation": c.gang_affiliation,
                "risk_score": None,
                "is_demo_derived": is_demo_derived(c),
                "provenance": provenance_str(c),
                "verification_status": verification_status_for(c),
            })
        elif rid in victims:
            v = victims[rid]
            entities.append({
                "id": rid,
                "node_id": f"victim-{rid}",
                "entity_type": "victim",
                "name": v.full_name,
                "role": "victim",
                "status": "victim",
                "aliases": None,
                "mo_summary": v.statement,
                "gang_affiliation": None,
                "risk_score": None,
                "is_demo_derived": is_demo_derived(v),
                "provenance": provenance_str(v),
                "verification_status": verification_status_for(v),
            })
    return entities


def _resolve_evidence(db: Session, case_ids: list[uuid.UUID]) -> list[Evidence]:
    if not case_ids:
        return []
    return (
        db.query(Evidence)
        .filter(Evidence.case_id.in_(case_ids))
        .order_by(Evidence.created_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# MO aggregation over the resolved set (bounded, provenance-aware)
# ---------------------------------------------------------------------------

def _shared_mo_tags(cases: list[CrimeCase]) -> list[str]:
    """Canonical MO tags shared by >=2 of the related cases."""
    tag_counter: Counter[str] = Counter()
    for case in cases:
        tags = set()
        if case.mo_tags:
            tags.update(t.strip().lower() for t in case.mo_tags.split(",") if t.strip())
        if case.description:
            from app.services.mo_pattern_service import tags_for_text
            tags.update(tags_for_text(case.description))
        tag_counter.update(tags)
    return sorted(t for t, count in tag_counter.items() if count >= 2)


def _build_mo_matches(
    db: Session,
    cases: list[CrimeCase],
    entities: list[dict[str, Any]],
    shared_tags: list[str],
) -> dict[str, Any]:
    """Similarity between the primary related case and other related cases /
    named criminals, cast into the verification vocabulary."""
    from app.services.mo_matching_service import (
        calculate_mo_similarity,
        extract_case_mo_profile,
        extract_criminal_mo_profile,
    )

    if not cases:
        return {
            "shared_tags": [],
            "reference_case_id": None,
            "suspects": [],
            "matching_cases": [],
            "method": "No related cases to compare",
        }

    reference = max(cases, key=lambda c: len(c.firs or []) or 0)
    try:
        reference_profile = extract_case_mo_profile(db, reference)
    except Exception:
        return {
            "shared_tags": shared_tags,
            "reference_case_id": str(reference.id) if reference else None,
            "suspects": [],
            "matching_cases": [],
            "method": "Unable to extract MO profile for the reference case",
        }

    suspects: list[dict[str, Any]] = []
    for entity in entities:
        if entity["entity_type"] != "criminal":
            continue
        criminal = db.query(Criminal).filter(Criminal.id == uuid.UUID(entity["id"])).first()
        if criminal is None:
            continue
        try:
            profile = extract_criminal_mo_profile(db, criminal)
            eval_res = calculate_mo_similarity(reference_profile, profile)
        except Exception:
            continue
        if eval_res.score <= 0:
            continue
        suspects.append({
            "criminal_id": entity["id"],
            "full_name": entity["name"],
            "aliases": entity.get("aliases"),
            "status": entity.get("status"),
            "similarity_score": round(eval_res.score, 4),
            "similarity_percent": int(round(eval_res.score * 100)),
            "match_level": eval_res.match_level,
            "confidence": eval_res.confidence,
            "is_confirmed_relationship": True,
            "relationship_label": "Confirmed FIR Accused",
            "verification_status": entity["verification_status"],
            "matching_factors": list(eval_res.matching_factors or []),
            "divergent_factors": list(eval_res.divergent_factors or []),
            "insufficient_data": bool(eval_res.insufficient_data),
        })
    suspects.sort(key=lambda s: (-bool(s["is_confirmed_relationship"]), -s["similarity_score"]))

    matching_cases: list[dict[str, Any]] = []
    for other in cases:
        if other.id == reference.id:
            continue
        try:
            other_profile = extract_case_mo_profile(db, other)
            eval_res = calculate_mo_similarity(reference_profile, other_profile)
        except Exception:
            continue
        if eval_res.score <= 0:
            continue
        restricted = is_restricted_record(other)
        matching_cases.append({
            "case_id": str(other.id),
            "case_number": other.case_number,
            "similarity_score": round(eval_res.score, 4),
            "similarity_percent": int(round(eval_res.score * 100)),
            "match_level": eval_res.match_level,
            "confidence": eval_res.confidence,
            "verification_status": (
                "RESTRICTED" if restricted
                else "DEMO" if is_demo_derived(other)
                else "POTENTIAL"
            ),
            "matching_factors": list(eval_res.matching_factors or []),
            "divergent_factors": list(eval_res.divergent_factors or []),
        })
    matching_cases.sort(key=lambda c: -c["similarity_score"])

    method = (
        "Structured MO profile similarity over canonical modus-operandi tags, "
        "target type, time window, sections and narrative-derived factors"
    )
    return {
        "shared_tags": shared_tags,
        "reference_case_id": str(reference.id) if reference else None,
        "suspects": suspects,
        "matching_cases": matching_cases,
        "method": method,
    }


# ---------------------------------------------------------------------------
# Network snapshot (subgraph over the resolved FIRs/cases/entities)
# ---------------------------------------------------------------------------

def _build_network(
    firs: list[FIR],
    cases: list[CrimeCase],
    entities: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    def add_node(node_id: str, *, name: str, category: str, details: str = "",
                 cases_count: int = 0, is_seed: bool = False,
                 verification_status: str = "VERIFIED") -> None:
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "name": name,
                "category": category,
                "riskScore": 0,
                "details": details,
                "casesCount": cases_count,
                "isSeed": is_seed,
                "verification_status": verification_status,
            }

    def add_edge(source: str, target: str, *, relationship: str,
                 relationship_type: str, provenance: str,
                 verification_status: str, is_demo_derived: bool,
                 confidence: float, confidence_level: str, evidence: list[dict[str, Any]],
                 operational_warning: str | None = None) -> None:
        edges.append({
            "source": source,
            "target": target,
            "relationship": relationship,
            "relationship_type": relationship_type,
            "provenance": provenance,
            "verification_status": verification_status,
            "confidence": confidence,
            "confidence_level": confidence_level,
            "evidence": evidence[:3],
            "is_demo_derived": is_demo_derived,
            "operational_warning": operational_warning,
        })

    firm_case_map: dict[uuid.UUID, CrimeCase | None] = {}
    for fir in firs:
        case = fir.crime_case
        firm_case_map[fir.id] = case
        is_not_restricted = not is_restricted_record(fir, case)
        case_id = f"case-{fir.id}"
        demo = is_demo_derived(fir) or (case is not None and is_demo_derived(case))
        case_status = (
            "RESTRICTED" if is_restricted_record(fir, case)
            else "DEMO" if demo else "VERIFIED"
        )
        add_node(
            case_id,
            name=f"FIR #{fir.fir_number}",
            category="case",
            details=f"Sections: {fir.sections or 'IPC'} · Complainant: {fir.complainant_name}",
            cases_count=1,
            is_seed=demo,
            verification_status=case_status,
        )
        if case is not None and case.location is not None:
            loc_id = f"location-{case.location.id}"
            loc_seed = is_demo_derived(case.location)
            add_node(
                loc_id,
                name=f"{case.location.station or 'Station'}, {case.location.district}",
                category="location",
                details=f"District: {case.location.district}",
                is_seed=loc_seed,
            )
            add_edge(
                case_id, loc_id,
                relationship="Occurred At Jurisdiction",
                relationship_type="CASE_LOCATION",
                provenance="DEMO_SEED" if (demo or loc_seed) else "DIRECT_DATABASE",
                verification_status="RESTRICTED" if is_restricted_record(fir, case) else (
                    "DEMO" if (demo or loc_seed) else "VERIFIED"),
                is_demo_derived=demo or loc_seed,
                confidence=1.0,
                confidence_level="HIGH",
                evidence=[{
                    "record_type": "fir_location",
                    "record_id": str(fir.id),
                    "record_number": fir.fir_number,
                    "details": f"FIR #{fir.fir_number} in {case.location.district}",
                    "timestamp": fir.filed_at.isoformat() if fir.filed_at else None,
                }],
            )

    for link in sum((list(fir.criminal_links) for fir in firs), []):
        criminal = link.criminal
        if criminal is None:
            continue
        crim_id = f"criminal-{criminal.id}"
        demo_c = is_demo_derived(criminal)
        add_node(
            crim_id,
            name=criminal.full_name,
            category="suspect" if criminal.status == "at_large" else "offender",
            details=criminal.mo_summary or criminal.identifying_marks or "Linked in FIR records",
            cases_count=len(criminal.fir_links),
            is_seed=demo_c,
            verification_status="VERIFIED" if not demo_c else "DEMO",
        )
        fir = next((f for f in firs if link.fir_id == f.id), None)
        if fir is None:
            continue
        case_id = f"case-{fir.id}"
        restricted = is_restricted_record(fir, fir.crime_case)
        combined_demo = demo_c or is_demo_derived(fir)
        add_edge(
            crim_id, case_id,
            relationship="Accused in FIR",
            relationship_type="PERSON_CASE",
            provenance="DEMO_SEED" if combined_demo else "DIRECT_DATABASE",
            verification_status="RESTRICTED" if restricted else (
                "DEMO" if combined_demo else "VERIFIED"),
            is_demo_derived=combined_demo,
            confidence=1.0,
            confidence_level="HIGH",
            evidence=[{
                "record_type": "fir_charge",
                "record_id": str(fir.id),
                "record_number": fir.fir_number,
                "details": f"Accused listed under sections {fir.sections or 'IPC'} in FIR #{fir.fir_number}",
                "timestamp": fir.filed_at.isoformat() if fir.filed_at else None,
            }],
        )

    for link in sum((list(fir.victim_links) for fir in firs), []):
        victim = link.victim
        if victim is None:
            continue
        vic_id = f"victim-{victim.id}"
        demo_v = is_demo_derived(victim)
        add_node(
            vic_id,
            name=victim.full_name,
            category="victim",
            details=victim.statement or "Victim named in FIR",
            cases_count=len(victim.fir_links),
            is_seed=demo_v,
        )
        fir = next((f for f in firs if link.fir_id == f.id), None)
        if fir is None:
            continue
        case_id = f"case-{fir.id}"
        restricted = is_restricted_record(fir, fir.crime_case)
        combined_demo = demo_v or is_demo_derived(fir)
        add_edge(
            vic_id, case_id,
            relationship="Victim in FIR",
            relationship_type="PERSON_VICTIM",
            provenance="DEMO_SEED" if combined_demo else "DIRECT_DATABASE",
            verification_status="RESTRICTED" if restricted else (
                "DEMO" if combined_demo else "VERIFIED"),
            is_demo_derived=combined_demo,
            confidence=1.0,
            confidence_level="HIGH",
            evidence=[{
                "record_type": "fir_victim",
                "record_id": str(fir.id),
                "record_number": fir.fir_number,
                "details": f"Victim named in FIR #{fir.fir_number}",
                "timestamp": fir.filed_at.isoformat() if fir.filed_at else None,
            }],
        )

    # Add orphan entities (listed in the intelligence but with no resolved link)
    linked_node_ids = {e["source"] for e in edges} | {e["target"] for e in edges}
    for entity in entities:
        nid = entity["node_id"]
        if nid not in nodes and nid not in linked_node_ids:
            demo = entity["is_demo_derived"]
            add_node(
                nid,
                name=entity["name"],
                category="victim" if entity["entity_type"] == "victim" else (
                    "suspect" if entity.get("status") == "at_large" else "offender"),
                details=entity.get("mo_summary") or "",
                is_seed=demo,
                verification_status="VERIFIED" if not demo else "DEMO",
            )

    # Shared-MO analytical edges between related cases (always POTENTIAL/DEMO/RESTRICTED)
    shared_pairs: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    tag_by_case: dict[str, set[str]] = {}
    for case in cases:
        tags: set[str] = set()
        if case.mo_tags:
            tags.update(t.strip().lower() for t in case.mo_tags.split(",") if t.strip())
        tag_by_case[case.id] = tags
    case_ids_in_graph = {f"case-{fir.id}" for fir in firs}
    for i in range(len(cases)):
        for j in range(i + 1, len(cases)):
            common = tag_by_case.get(cases[i].id, set()) & tag_by_case.get(cases[j].id, set())
            if not common:
                continue
            ci = f"case-{next((f.id for f in firs if f.crime_case_id == cases[i].id), '')}"
            cj = f"case-{next((f.id for f in firs if f.crime_case_id == cases[j].id), '')}"
            if ci not in case_ids_in_graph or cj not in case_ids_in_graph:
                continue
            pair_key = tuple(sorted((ci, cj)))
            shared_pairs[pair_key].append({
                "record_type": "shared_mo",
                "details": f"Shared MO tags: {', '.join(sorted(common)[:4])}",
                "factors": ["Shared canonical modus operandi"],
            })
    for (a, b), evidence in shared_pairs.items():
        edge_demo = nodes[a].get("isSeed", False) and nodes[b].get("isSeed", False)
        restricted = nodes[a]["verification_status"] == "RESTRICTED" or nodes[b]["verification_status"] == "RESTRICTED"
        add_edge(
            a, b,
            relationship=f"Shared MO pattern ({len(evidence)} tag group(s))",
            relationship_type="SHARED_MO",
            provenance="DEMO_SEED" if edge_demo else "ANALYTICAL_INFERENCE",
            verification_status="RESTRICTED" if restricted else (
                "DEMO" if edge_demo else "POTENTIAL"),
            is_demo_derived=bool(edge_demo),
            confidence=0.72,
            confidence_level="MEDIUM",
            evidence=evidence,
            operational_warning="Shared modus operandi derived analytically from case records. "
                                "This does not establish a confirmed association.",
        )

    return {"nodes": list(nodes.values()), "edges": edges}


# ---------------------------------------------------------------------------
# Verification summary
# ---------------------------------------------------------------------------

def _verification_summary(
    firs: list[FIR],
    cases: list[CrimeCase],
    entities: list[dict[str, Any]],
    evidence: list[Evidence],
    network: dict[str, Any],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in firs:
        counts[verification_status_for(record, case=record.crime_case)] += 1
    for case in cases:
        counts[verification_status_for(case)] += 1
    for entity in entities:
        counts[entity["verification_status"]] += 1
    for item in evidence:
        counts[verification_status_for(item, case=item.crime_case)] += 1
    for edge in network.get("edges", []):
        counts[edge["verification_status"]] += 1
    return {state: int(counts.get(state, 0)) for state in
            ("VERIFIED", "POTENTIAL", "DEMO", "RESTRICTED", "UNVERIFIED")}


# ---------------------------------------------------------------------------
# Why This Insight?
# ---------------------------------------------------------------------------

def _why_this_insight(pattern: dict[str, Any], network: dict[str, Any]) -> dict[str, Any]:
    signals = [
        {
            "signal_type": s.get("signal_type", "unknown"),
            "description": s.get("description", ""),
            "status": s.get("status", "UNAVAILABLE"),
        }
        for s in (pattern.get("supporting_signals") or [])
    ]

    analytics = pattern.get("contributing_analytics") or {}
    methodology = {
        "ml_status": pattern.get("ml_status", "RULE_BASED"),
        "model_name": pattern.get("model_name", "SAKSHA Intelligence Fusion"),
        "model_version": pattern.get("model_version", "v1.0"),
        "analytics_available": {
            key: value.get("status", "UNAVAILABLE")
            for key, value in analytics.items()
            if isinstance(value, dict) and "status" in value
        },
    }

    provenance = (pattern.get("data_provenance") or "LIVE_DB")
    data_sources: list[str] = [
        f"PostgreSQL operational records (provenance: {provenance})",
        "Neo4j relationship graph when available; SQL fallback otherwise",
        "Intelligence Fusion analytics: anomaly, temporal, spatial hotspot, forecast, MO, entity links",
    ]
    demo_count = sum(1 for n in network.get("nodes", []) if n.get("isSeed"))
    if demo_count:
        data_sources.append(
            f"{demo_count} node(s) originate from the bundled demo seed dataset — clearly marked as DEMO."
        )

    limitations = [
        "Analytical relationships are investigative leads, not confirmed guilt or evidence.",
        "MO similarity is behavioural and never a substitute for corroborated witness/financial evidence.",
        "Some analytics degrade to rule-based estimates when trained models are unavailable.",
        "RESTRICTED records are demo-derived sensitive content; reviewer roles must re-validate against source registers.",
    ]

    summary = (
        f"{pattern.get('pattern_type', 'Pattern')} detected in "
        f"{((pattern.get('location') or {}).get('district') or 'the district')} with "
        f"{len(signals)} corroborating signal(s) and "
        f"{len(pattern.get('related_fir_ids') or [])} linked FIR(s)."
    )

    return {
        "summary": summary,
        "signals": signals,
        "methodology": methodology,
        "data_sources": data_sources,
        "limitations": limitations,
        "safety_note": SAFETY_NOTE,
    }


# ---------------------------------------------------------------------------
# Main assembly
# ---------------------------------------------------------------------------

def build_intelligence_investigation(
    db: Session,
    pattern: dict[str, Any],
    current_user: Any,
) -> dict[str, Any]:
    """Compose the full provenance-aware investigation view for one pattern."""
    fir_numbers = list(dict.fromkeys(pattern.get("related_fir_ids") or []))
    entity_ids = list(dict.fromkeys(pattern.get("related_entity_ids") or []))

    firs: list[FIR] = _resolve_firs(db, fir_numbers)
    case_objects: list[CrimeCase] = []
    seen_case_ids: set[uuid.UUID] = set()
    for fir in firs:
        if fir.crime_case is not None and fir.crime_case.id not in seen_case_ids:
            seen_case_ids.add(fir.crime_case.id)
            case_objects.append(fir.crime_case)

    entities: list[dict[str, Any]] = _resolve_entities(db, entity_ids)
    evidence: list[Evidence] = _resolve_evidence(db, list(seen_case_ids))

    shared_tags = _shared_mo_tags(case_objects)
    mo_matches = _build_mo_matches(db, case_objects, entities, shared_tags)
    network = _build_network(firs, case_objects, entities)

    has_restricted_access = current_user.role.name in REVIEW_ROLES

    # FIR / case / evidence payloads with provenance + optional restricted masking
    case_by_fir: dict[uuid.UUID, CrimeCase | None] = {fir.id: fir.crime_case for fir in firs}
    evidence_by_case: dict[uuid.UUID, list[Evidence]] = defaultdict(list)
    for item in evidence:
        evidence_by_case[item.case_id].append(item)

    fir_payloads: list[dict[str, Any]] = []
    for fir in firs:
        case = case_by_fir[fir.id]
        restricted = is_restricted_record(fir, case)
        fir_payloads.append({
            "id": str(fir.id),
            "fir_number": fir.fir_number,
            "complainant_name": fir.complainant_name,
            "complainant_contact": fir.complainant_contact,
            "sections": fir.sections,
            "status": fir.status,
            "filed_at": fir.filed_at.isoformat() if fir.filed_at else None,
            "narrative": fir.narrative,
            "case_id": str(case.id) if case else None,
            "case_number": case.case_number if case else None,
            "verification_status": (
                "RESTRICTED" if restricted
                else "DEMO" if is_demo_derived(fir)
                else "VERIFIED"
            ),
            "provenance": provenance_str(fir),
            "is_demo_derived": is_demo_derived(fir),
            "is_restricted": restricted,
            "evidence_count": len(evidence_by_case.get(fir.crime_case_id, [])),
        })

    case_payloads: list[dict[str, Any]] = []
    for case in case_objects:
        restricted = is_restricted_record(case)
        case_payloads.append({
            "id": str(case.id),
            "case_number": case.case_number,
            "category": case.category.name if case.category else None,
            "district": case.location.district if case.location else None,
            "station": case.location.station if case.location else None,
            "status": case.status,
            "priority": case.priority,
            "progress": case.progress,
            "occurred_at": case.occurred_at.isoformat() if case.occurred_at else None,
            "description": case.description,
            "mo_tags": case.mo_tags,
            "fir_count": len(case.firs or []),
            "evidence_count": len(evidence_by_case.get(case.id, [])),
            "verification_status": (
                "RESTRICTED" if restricted
                else "DEMO" if is_demo_derived(case)
                else "VERIFIED"
            ),
            "provenance": provenance_str(case),
            "is_demo_derived": is_demo_derived(case),
            "is_restricted": restricted,
        })

    restricted_mask = "[RESTRICTED — reviewer access required]"
    evidence_payloads: list[dict[str, Any]] = []
    for item in evidence:
        case = item.crime_case
        restricted = is_restricted_record(item, case)
        masked = restricted and not has_restricted_access
        evidence_payloads.append({
            "id": str(item.id),
            "title": restricted_mask if masked else item.title,
            "description": restricted_mask if masked else item.description,
            "evidence_type": item.evidence_type,
            "status": item.status,
            "case_id": str(item.case_id),
            "case_number": case.case_number if case else None,
            "fir_number": next(
                (f.fir_number for f in firs if f.crime_case_id == item.case_id), None
            ),
            "verification_status": (
                "RESTRICTED" if restricted
                else "DEMO" if is_demo_derived(item)
                else "VERIFIED"
            ),
            "provenance": provenance_str(item),
            "is_demo_derived": is_demo_derived(item),
            "is_restricted": restricted,
            "masked": masked,
        })

    location = pattern.get("location") or {}

    return {
        "intelligence_id": pattern.get("intelligence_id"),
        "pattern_type": pattern.get("pattern_type"),
        "location": {
            "district": location.get("district"),
            "stations": location.get("stations") or [],
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
        },
        "risk_score": pattern.get("risk_score"),
        "confidence": pattern.get("confidence"),
        "generated_at": pattern.get("detection_timestamp"),
        "firs": fir_payloads,
        "cases": case_payloads,
        "entities": entities,
        "mo_matches": mo_matches,
        "network": network,
        "evidence": evidence_payloads,
        "why_this_insight": _why_this_insight(pattern, network),
        "verification_summary": _verification_summary(
            firs, case_objects, entities, evidence, network
        ),
        "access": {"has_restricted_access": has_restricted_access},
    }