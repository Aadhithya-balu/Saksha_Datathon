"""
Intelligence Engine — unified investigation intelligence builder.

Accepts an entity type (fir/criminal/case/victim) and entity ID, orchestrates
existing services, and returns a single comprehensive intelligence report with
connections, common threads, case comparison, crime DNA profiling, ranked
investigation leads, timeline, and pattern-break analysis.

All functions are stateless — every function takes ``db`` plus explicit
parameters.  Inferred relationships are never presented as confirmed facts;
every insight shows its reasoning and source records.
"""
from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.criminal import Criminal
from app.models.victim import Victim
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.location import Location
from app.models.officer import Officer
from app.models.evidence import Evidence
from app.models.investigation_note import InvestigationNote
from app.services.base_service import BaseCRUDService


# ---------------------------------------------------------------------------
# Structured output types
# ---------------------------------------------------------------------------

@dataclass
class ConnectionItem:
    entity_type: str
    entity_id: str
    entity_name: str
    relationship: str
    strength: float
    confidence: str  # confirmed / inferred / possible
    explanation: str
    source_records: list[dict[str, Any]]


@dataclass
class CommonThread:
    attribute: str
    value: str
    case_count: int
    confidence: str
    source_records: list[dict[str, Any]]


@dataclass
class ComparisonItem:
    attribute: str
    primary_value: Any
    related_value: Any
    status: str  # match / different / missing_in_related / missing_in_primary / conflict
    confidence: str
    source_records: list[dict[str, Any]]


@dataclass
class DNAComponent:
    pattern_type: str
    description: str
    frequency: int
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimilarityResult:
    source: str
    score: float | None
    matching_attributes: list[str]
    explanation: str


@dataclass
class InvestigationLead:
    item_type: str
    item_id: str
    item_name: str
    rank: int
    reason: str
    source_records: list[dict[str, Any]]
    label: str


@dataclass
class TimelineEvent:
    timestamp: str
    event: str
    source_type: str
    source_id: str


@dataclass
class PatternBreak:
    pattern_type: str
    baseline: str
    deviation: str
    confidence: str
    supporting_records: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ENTITY_TYPES = {"fir", "criminal", "case", "victim"}
_MAX_CONNECTIONS = 20
_MAX_THREADS = 10
_MAX_LEADS = 10
_MAX_SIMILARITIES = 10


def _to_str_id(val: Any) -> str:
    return str(val) if val is not None else ""


def _ts(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.isoformat()


def _normalize_sources(records: Any) -> list[dict[str, Any]]:
    """Normalize heterogeneous source-record shapes to {type, id, label}."""
    out: list[dict[str, Any]] = []
    for r in records or []:
        if not isinstance(r, dict):
            continue
        typ = r.get("type") or r.get("record_type") or r.get("source_type")
        rid = r.get("id") or r.get("record_id") or r.get("source_id")
        label = (
            r.get("label")
            or r.get("record_number")
            or r.get("entity_name")
            or r.get("source_label")
            or r.get("record_type")
        )
        if rid:
            out.append({"type": typ or "record", "id": str(rid), "label": label})
    return out


# ---------------------------------------------------------------------------
# a) _resolve_entity
# ---------------------------------------------------------------------------

def _resolve_entity(db: Session, entity_type: str, entity_id: str) -> dict[str, Any]:
    """Resolve an entity type + ID to the ORM object and related data.

    Returns a dict with ``entity``, ``entity_type``, ``related_fir_ids``,
    ``related_case_ids``, ``info``, and ``label``.
    """
    uid = uuid.UUID(entity_id)

    if entity_type == "fir":
        fir = (
            db.query(FIR)
            .options(
                joinedload(FIR.crime_case).joinedload(CrimeCase.category),
                joinedload(FIR.crime_case).joinedload(CrimeCase.location),
                joinedload(FIR.criminal_links).joinedload(FIRCriminalLink.criminal),
                joinedload(FIR.victim_links).joinedload(FIRVictimLink.victim),
                joinedload(FIR.investigating_officer),
            )
            .filter(FIR.id == uid)
            .first()
        )
        if fir is None:
            raise ValueError(f"FIR {entity_id} not found")
        case_id = fir.crime_case_id
        criminal_ids = [lk.criminal_id for lk in fir.criminal_links]
        victim_ids = [lk.victim_id for lk in fir.victim_links]
        officer_name = fir.investigating_officer.name if fir.investigating_officer else None
        info = {
            "id": _to_str_id(fir.id),
            "fir_number": fir.fir_number,
            "case_id": _to_str_id(case_id),
            "complainant": fir.complainant_name,
            "sections": fir.sections,
            "status": fir.status,
            "filed_at": _ts(fir.filed_at),
            "narrative": fir.narrative,
            "criminals": [{"id": _to_str_id(lk.criminal_id), "name": lk.criminal.full_name} for lk in fir.criminal_links if lk.criminal],
            "victims": [{"id": _to_str_id(lk.victim_id), "name": lk.victim.full_name} for lk in fir.victim_links if lk.victim],
            "officer": officer_name,
        }
        return {
            "entity": fir,
            "entity_type": "fir",
            "related_fir_ids": [fir.id],
            "related_case_ids": [case_id] if case_id else [],
            "info": info,
            "label": f"FIR {fir.fir_number}",
        }

    if entity_type == "criminal":
        criminal = (
            db.query(Criminal)
            .options(joinedload(Criminal.fir_links).joinedload(FIRCriminalLink.fir))
            .filter(Criminal.id == uid)
            .first()
        )
        if criminal is None:
            raise ValueError(f"Criminal {entity_id} not found")
        fir_ids = [lk.fir_id for lk in criminal.fir_links]
        case_ids = list({lk.fir.crime_case_id for lk in criminal.fir_links if lk.fir})
        open_firs = sum(1 for lk in criminal.fir_links if lk.fir and lk.fir.status and lk.fir.status.lower() not in ('closed', 'resolved'))
        info = {
            "id": _to_str_id(criminal.id),
            "full_name": criminal.full_name,
            "aliases": criminal.aliases,
            "status": criminal.status,
            "gang_affiliation": criminal.gang_affiliation,
            "mo_summary": criminal.mo_summary,
            "fir_count": len(fir_ids),
            "open_fir_count": open_firs,
            "risk_score": criminal.risk_score if hasattr(criminal, 'risk_score') and criminal.risk_score is not None else None,
            "dob": _ts(criminal.date_of_birth) if hasattr(criminal, 'date_of_birth') else None,
            "gender": criminal.gender if hasattr(criminal, 'gender') else None,
            "address": criminal.address if hasattr(criminal, 'address') else None,
            "identifying_marks": criminal.identifying_marks if hasattr(criminal, 'identifying_marks') else None,
        }
        return {
            "entity": criminal,
            "entity_type": "criminal",
            "related_fir_ids": fir_ids,
            "related_case_ids": case_ids,
            "info": info,
            "label": f"Criminal: {criminal.full_name}",
        }

    if entity_type == "case":
        case = (
            db.query(CrimeCase)
            .options(
                joinedload(CrimeCase.category),
                joinedload(CrimeCase.location),
                joinedload(CrimeCase.firs)
                .joinedload(FIR.criminal_links)
                .joinedload(FIRCriminalLink.criminal),
                joinedload(CrimeCase.firs)
                .joinedload(FIR.victim_links)
                .joinedload(FIRVictimLink.victim),
                joinedload(CrimeCase.evidence),
                joinedload(CrimeCase.assigned_officer),
            )
            .filter(CrimeCase.id == uid)
            .first()
        )
        if case is None:
            raise ValueError(f"Crime case {entity_id} not found")
        fir_ids = [fir.id for fir in case.firs]
        info = {
            "id": _to_str_id(case.id),
            "case_number": case.case_number,
            "category": case.category.name if case.category else None,
            "district": case.location.district if case.location else None,
            "status": case.status,
            "priority": case.priority,
            "description": case.description,
            "mo_tags": case.mo_tags,
            "occurred_at": _ts(case.occurred_at),
            "fir_count": len(fir_ids),
        }
        return {
            "entity": case,
            "entity_type": "case",
            "related_fir_ids": fir_ids,
            "related_case_ids": [case.id],
            "info": info,
            "label": f"Case {case.case_number}",
        }

    if entity_type == "victim":
        victim = (
            db.query(Victim)
            .options(joinedload(Victim.fir_links).joinedload(FIRVictimLink.fir))
            .filter(Victim.id == uid)
            .first()
        )
        if victim is None:
            raise ValueError(f"Victim {entity_id} not found")
        fir_ids = [lk.fir_id for lk in victim.fir_links]
        case_ids = list({lk.fir.crime_case_id for lk in victim.fir_links if lk.fir})
        info = {
            "id": _to_str_id(victim.id),
            "full_name": victim.full_name,
            "gender": victim.gender,
            "age": victim.age,
            "address": victim.address,
            "fir_count": len(fir_ids),
        }
        return {
            "entity": victim,
            "entity_type": "victim",
            "related_fir_ids": fir_ids,
            "related_case_ids": case_ids,
            "info": info,
            "label": f"Victim: {victim.full_name}",
        }

    raise ValueError(f"Unknown entity_type '{entity_type}'. Must be one of {sorted(_VALID_ENTITY_TYPES)}")


# ---------------------------------------------------------------------------
# b) _find_connections
# ---------------------------------------------------------------------------

def _find_connections(
    db: Session,
    entity_type: str,
    entity: Any,
    related_fir_ids: list,
) -> list[dict[str, Any]]:
    """Find the strongest related entities for a given entity."""
    if not related_fir_ids:
        return []

    firs = (
        db.query(FIR)
        .options(
            joinedload(FIR.crime_case).joinedload(CrimeCase.category),
            joinedload(FIR.crime_case).joinedload(CrimeCase.location),
            joinedload(FIR.criminal_links).joinedload(FIRCriminalLink.criminal),
            joinedload(FIR.victim_links).joinedload(FIRVictimLink.victim),
            joinedload(FIR.investigating_officer),
        )
        .filter(FIR.id.in_(related_fir_ids))
        .all()
    )

    people_freq: Counter[str] = Counter()
    people_meta: dict[str, dict[str, Any]] = {}
    location_freq: Counter[str] = Counter()
    location_meta: dict[str, dict[str, Any]] = {}
    officer_freq: Counter[str] = Counter()
    officer_meta: dict[str, dict[str, Any]] = {}
    related_case_set: set[Any] = set()
    extracted_entities: dict[str, list[str]] = defaultdict(list)
    fir_sources: list[dict[str, Any]] = []

    for fir in firs:
        fir_src = {"record_type": "fir", "record_id": _to_str_id(fir.id), "record_number": fir.fir_number}
        fir_sources.append(fir_src)

        # People from criminal links
        for lk in fir.criminal_links:
            if lk.criminal is None:
                continue
            c = lk.criminal
            key = f"criminal-{c.id}"
            people_freq[key] += 1
            if key not in people_meta:
                people_meta[key] = {
                    "entity_type": "criminal",
                    "entity_id": _to_str_id(c.id),
                    "entity_name": c.full_name,
                    "relationship": f"Accused in FIR {fir.fir_number}",
                    "details": {"status": c.status, "gang": c.gang_affiliation, "mo": c.mo_summary},
                }

        # People from victim links
        for lk in fir.victim_links:
            if lk.victim is None:
                continue
            v = lk.victim
            key = f"victim-{v.id}"
            people_freq[key] += 1
            if key not in people_meta:
                people_meta[key] = {
                    "entity_type": "victim",
                    "entity_id": _to_str_id(v.id),
                    "entity_name": v.full_name,
                    "relationship": f"Victim in FIR {fir.fir_number}",
                    "details": {"gender": v.gender, "age": v.age},
                }

        # Locations
        if fir.crime_case and fir.crime_case.location:
            loc = fir.crime_case.location
            loc_key = f"location-{loc.id}"
            location_freq[loc_key] += 1
            if loc_key not in location_meta:
                location_meta[loc_key] = {
                    "entity_type": "location",
                    "entity_id": _to_str_id(loc.id),
                    "entity_name": f"{loc.station or 'Station'}, {loc.district}",
                    "relationship": f"Jurisdiction for FIR {fir.fir_number}",
                    "details": {"district": loc.district, "station": loc.station},
                }

        # Officers
        if fir.investigating_officer:
            o = fir.investigating_officer
            o_key = f"officer-{o.id}"
            officer_freq[o_key] += 1
            if o_key not in officer_meta:
                officer_meta[o_key] = {
                    "entity_type": "officer",
                    "entity_id": _to_str_id(o.id),
                    "entity_name": o.name,
                    "relationship": f"Investigating officer on FIR {fir.fir_number}",
                    "details": {"badge": o.badge_number, "rank": o.rank, "district": o.district},
                }

        # Related cases
        if fir.crime_case_id:
            related_case_set.add(fir.crime_case_id)

        # NER extraction from narratives
        if fir.narrative:
            try:
                from app.services.mo_semantic_service import extract_entities
                ner = extract_entities(fir.narrative)
                ents = ner.get("entities", {})
                for kind in ("phone_numbers", "vehicle_plates", "weapons"):
                    for val in ents.get(kind, []):
                        extracted_entities[kind].append(val)
            except Exception:
                pass

    connections: list[dict[str, Any]] = []

    # People connections
    for key, freq in people_freq.most_common(_MAX_CONNECTIONS):
        meta = people_meta[key]
        confidence = "confirmed" if freq >= 2 else "probable"
        strength = min(1.0, 0.5 + freq * 0.15)
        connections.append({
            "entity_type": meta["entity_type"],
            "entity_id": meta["entity_id"],
            "entity_name": meta["entity_name"],
            "connection_type": "shared_person",
            "entity_detail": meta["relationship"],
            "confidence_score": round(strength, 2),
            "confidence": confidence,
            "explanation": f"Appears in {freq} of the related FIR(s)" + (f" — multiple co-occurrences strengthen this link" if freq >= 2 else ""),
            "source_records": [s for s in fir_sources[:freq]],
        })

    # Location connections
    for key, freq in location_freq.most_common(10):
        meta = location_meta[key]
        confidence = "confirmed" if freq >= 2 else "probable"
        strength = min(1.0, 0.5 + freq * 0.1)
        connections.append({
            "entity_type": "location",
            "entity_id": meta["entity_id"],
            "entity_name": meta["entity_name"],
            "connection_type": "shared_location",
            "entity_detail": meta["relationship"],
            "confidence_score": round(strength, 2),
            "confidence": confidence,
            "explanation": f"Linked to {freq} related FIR(s) — frequent jurisdiction suggests operational area",
            "source_records": [s for s in fir_sources[:freq]],
        })

    # Officer connections
    for key, freq in officer_freq.most_common(5):
        meta = officer_meta[key]
        strength = min(1.0, 0.6 + freq * 0.1)
        connections.append({
            "entity_type": "officer",
            "entity_id": meta["entity_id"],
            "entity_name": meta["entity_name"],
            "connection_type": "shared_officer",
            "entity_detail": meta["relationship"],
            "confidence_score": round(strength, 2),
            "confidence": "confirmed",
            "explanation": f"Investigating officer on {freq} related FIR(s)",
            "source_records": [s for s in fir_sources[:freq]],
        })

    # Extracted entity connections
    for kind, values in extracted_entities.items():
        for val in sorted(set(values))[:10]:
            connections.append({
                "entity_type": "extracted_entity",
                "entity_id": val,
                "entity_name": val,
                "connection_type": "extracted_entity",
                "entity_detail": f"Extracted {kind.replace('_', ' ')} from FIR narrative(s)",
                "confidence_score": 0.5,
                "confidence": "possible",
                "explanation": f"Rule-based NER found '{val}' as a {kind.replace('_', ' ')} in narrative text",
                "source_records": fir_sources[:1],
            })

    return connections[:_MAX_CONNECTIONS]


# ---------------------------------------------------------------------------
# c) _find_common_threads
# ---------------------------------------------------------------------------

def _find_common_threads(
    db: Session,
    related_fir_ids: list,
    related_case_ids: list,
) -> list[dict[str, Any]]:
    """Identify attributes shared across related cases."""
    if not related_fir_ids:
        return []

    firs = (
        db.query(FIR)
        .options(
            joinedload(FIR.crime_case).joinedload(CrimeCase.category),
            joinedload(FIR.criminal_links).joinedload(FIRCriminalLink.criminal),
            joinedload(FIR.victim_links).joinedload(FIRVictimLink.victim),
        )
        .filter(FIR.id.in_(related_fir_ids))
        .all()
    )

    # Shared people
    person_fir_count: Counter[str] = Counter()
    person_meta: dict[str, dict[str, Any]] = {}
    # Shared locations / districts
    district_fir_count: Counter[str] = Counter()
    district_sources: dict[str, list[dict[str, Any]]] = defaultdict(list)
    # Shared crime categories
    category_fir_count: Counter[str] = Counter()
    category_sources: dict[str, list[dict[str, Any]]] = defaultdict(list)
    # Shared MO tags
    mo_tag_fir_count: Counter[str] = Counter()
    mo_tag_sources: dict[str, list[dict[str, Any]]] = defaultdict(list)
    # Shared sections
    section_fir_count: Counter[str] = Counter()
    section_sources: dict[str, list[dict[str, Any]]] = defaultdict(list)
    # Time patterns
    hour_fir_count: Counter[int] = Counter()
    hour_sources: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for fir in firs:
        fir_src = {"record_type": "fir", "record_id": _to_str_id(fir.id), "record_number": fir.fir_number}

        for lk in fir.criminal_links:
            if lk.criminal:
                name = lk.criminal.full_name
                person_fir_count[name] += 1
                if name not in person_meta:
                    person_meta[name] = {"type": "criminal", "id": _to_str_id(lk.criminal.id)}

        for lk in fir.victim_links:
            if lk.victim:
                name = lk.victim.full_name
                person_fir_count[name] += 1
                if name not in person_meta:
                    person_meta[name] = {"type": "victim", "id": _to_str_id(lk.victim.id)}

        if fir.crime_case:
            case = fir.crime_case
            if case.location:
                district = case.location.district
                district_fir_count[district] += 1
                district_sources[district].append(fir_src)
            if case.category:
                cat = case.category.name
                category_fir_count[cat] += 1
                category_sources[cat].append(fir_src)

        if fir.crime_case and fir.crime_case.mo_tags:
            for tag in [t.strip() for t in fir.crime_case.mo_tags.split(",") if t.strip()]:
                mo_tag_fir_count[tag] += 1
                mo_tag_sources[tag].append(fir_src)

        if fir.sections:
            for sec in [s.strip() for s in fir.sections.split(",") if s.strip()]:
                section_fir_count[sec] += 1
                section_sources[sec].append(fir_src)

        if fir.filed_at:
            hour = fir.filed_at.hour
            bucket = _time_bucket(hour)
            hour_fir_count[bucket] += 1
            hour_sources[bucket].append(fir_src)

    threads: list[dict[str, Any]] = []

    # People shared across 2+ FIRs
    for name, count in person_fir_count.most_common(10):
        if count < 2:
            continue
        meta = person_meta[name]
        threads.append({
            "attribute": "shared_person",
            "value": f"{name} ({meta['type']})",
            "case_count": count,
            "confidence": "confirmed",
            "explanation": f"{name} appears in {count} of the {len(related_fir_ids)} related FIRs — suggests active involvement or targeting",
            "source_records": [{"record_type": meta["type"], "record_id": meta["id"], "entity_name": name}],
        })

    # Shared districts
    for district, count in district_fir_count.most_common(5):
        if count < 2:
            continue
        threads.append({
            "attribute": "shared_district",
            "value": district,
            "case_count": count,
            "confidence": "confirmed",
            "explanation": f"{count} FIRs linked to {district} district — geographic clustering suggests operational pattern",
            "source_records": district_sources[district],
        })

    # Shared categories
    for cat, count in category_fir_count.most_common(5):
        if count < 2:
            continue
        threads.append({
            "attribute": "shared_crime_category",
            "value": cat,
            "case_count": count,
            "confidence": "confirmed",
            "explanation": f"{count} FIRs share crime category '{cat}' — consistent modus operandi or target type",
            "source_records": category_sources[cat],
        })

    # Shared MO tags
    for tag, count in mo_tag_fir_count.most_common(5):
        if count < 2:
            continue
        threads.append({
            "attribute": "shared_mo_tag",
            "value": tag,
            "case_count": count,
            "confidence": "probable",
            "explanation": f"MO tag '{tag}' appears in {count} cases — analytical inference of shared methodology",
            "source_records": mo_tag_sources[tag],
        })

    # Shared IPC/BNS sections
    for sec, count in section_fir_count.most_common(5):
        if count < 2:
            continue
        threads.append({
            "attribute": "shared_legal_section",
            "value": sec,
            "case_count": count,
            "confidence": "confirmed",
            "explanation": f"Section {sec} invoked in {count} FIRs — indicates comparable offence classification",
            "source_records": section_sources[sec],
        })

    # Time pattern
    for bucket, count in hour_fir_count.most_common(3):
        if count < 2:
            continue
        threads.append({
            "attribute": "shared_time_pattern",
            "value": bucket,
            "case_count": count,
            "confidence": "probable",
            "explanation": f"{count} FIRs filed during {bucket} — temporal clustering may indicate habitual offending window",
            "source_records": hour_sources[bucket],
        })

    threads.sort(key=lambda t: (-t["case_count"], t["attribute"]))
    return threads[:_MAX_THREADS]


def _time_bucket(hour: int) -> str:
    if 22 <= hour or hour < 5:
        return "Night (22:00-05:00)"
    if 5 <= hour < 12:
        return "Morning (05:00-12:00)"
    if 12 <= hour < 17:
        return "Afternoon (12:00-17:00)"
    return "Evening (17:00-22:00)"


# ---------------------------------------------------------------------------
# d) _compare_cases
# ---------------------------------------------------------------------------

def _compare_cases(
    db: Session,
    primary_case_id: Any,
    related_case_ids: list,
) -> dict[str, Any]:
    """Compare the primary case with each related case."""
    primary = db.query(CrimeCase).options(
        joinedload(CrimeCase.category),
        joinedload(CrimeCase.location),
        joinedload(CrimeCase.firs)
        .joinedload(FIR.criminal_links)
        .joinedload(FIRCriminalLink.criminal),
        joinedload(CrimeCase.firs)
        .joinedload(FIR.victim_links)
        .joinedload(FIRVictimLink.victim),
    ).filter(CrimeCase.id == primary_case_id).first()

    if primary is None:
        return {"error": "Primary case not found", "comparisons": []}

    comparisons: list[dict[str, Any]] = []

    for rid in related_case_ids:
        if rid == primary_case_id:
            continue
        related = db.query(CrimeCase).options(
            joinedload(CrimeCase.category),
            joinedload(CrimeCase.location),
            joinedload(CrimeCase.firs)
            .joinedload(FIR.criminal_links)
            .joinedload(FIRCriminalLink.criminal),
            joinedload(CrimeCase.firs)
            .joinedload(FIR.victim_links)
            .joinedload(FIRVictimLink.victim),
        ).filter(CrimeCase.id == rid).first()

        if related is None:
            continue

        items: list[dict[str, Any]] = []

        # Category
        p_cat = primary.category.name if primary.category else None
        r_cat = related.category.name if related.category else None
        items.append({
            "attribute": "crime_category",
            "primary_value": p_cat,
            "related_value": r_cat,
            "status": "match" if p_cat and r_cat and p_cat == r_cat else ("missing_in_related" if not r_cat else ("missing_in_primary" if not p_cat else "different")),
            "confidence": "confirmed",
            "source_records": [
                {"record_type": "case", "record_id": _to_str_id(primary.id)},
                {"record_type": "case", "record_id": _to_str_id(related.id)},
            ],
        })

        # District
        p_dist = primary.location.district if primary.location else None
        r_dist = related.location.district if related.location else None
        items.append({
            "attribute": "district",
            "primary_value": p_dist,
            "related_value": r_dist,
            "status": "match" if p_dist and r_dist and p_dist == r_dist else ("missing_in_related" if not r_dist else ("missing_in_primary" if not p_dist else "different")),
            "confidence": "confirmed",
            "source_records": [
                {"record_type": "location", "record_id": _to_str_id(primary.location_id) if primary.location_id else ""},
                {"record_type": "location", "record_id": _to_str_id(related.location_id) if related.location_id else ""},
            ],
        })

        # Status
        items.append({
            "attribute": "case_status",
            "primary_value": primary.status,
            "related_value": related.status,
            "status": "match" if primary.status == related.status else "different",
            "confidence": "confirmed",
            "source_records": [
                {"record_type": "case", "record_id": _to_str_id(primary.id)},
                {"record_type": "case", "record_id": _to_str_id(related.id)},
            ],
        })

        # Priority
        items.append({
            "attribute": "priority",
            "primary_value": primary.priority,
            "related_value": related.priority,
            "status": "match" if primary.priority and related.priority and primary.priority == related.priority else "different",
            "confidence": "confirmed",
            "source_records": [
                {"record_type": "case", "record_id": _to_str_id(primary.id)},
                {"record_type": "case", "record_id": _to_str_id(related.id)},
            ],
        })

        # Shared criminals
        p_criminals = set()
        for fir in primary.firs:
            for lk in fir.criminal_links:
                if lk.criminal:
                    p_criminals.add(lk.criminal.full_name)
        r_criminals = set()
        for fir in related.firs:
            for lk in fir.criminal_links:
                if lk.criminal:
                    r_criminals.add(lk.criminal.full_name)
        shared_crims = p_criminals & r_criminals
        if shared_crims:
            items.append({
                "attribute": "shared_criminals",
                "primary_value": sorted(p_criminals),
                "related_value": sorted(r_criminals),
                "status": "match",
                "confidence": "confirmed",
                "source_records": [{"shared_names": sorted(shared_crims)}],
            })
        elif p_criminals and r_criminals:
            items.append({
                "attribute": "shared_criminals",
                "primary_value": sorted(p_criminals),
                "related_value": sorted(r_criminals),
                "status": "different",
                "confidence": "confirmed",
                "source_records": [],
            })

        # MO tags
        p_mo = set(t.strip() for t in (primary.mo_tags or "").split(",") if t.strip())
        r_mo = set(t.strip() for t in (related.mo_tags or "").split(",") if t.strip())
        shared_mo = p_mo & r_mo
        if shared_mo:
            items.append({
                "attribute": "shared_mo_tags",
                "primary_value": sorted(p_mo),
                "related_value": sorted(r_mo),
                "status": "match",
                "confidence": "probable",
                "source_records": [{"shared_tags": sorted(shared_mo)}],
            })

        matches = sum(1 for it in items if it["status"] == "match")
        total = len(items)
        comparisons.append({
            "related_case_id": _to_str_id(related.id),
            "related_case_number": related.case_number,
            "match_ratio": round(matches / total, 2) if total else 0,
            "items": items,
        })

    comparisons.sort(key=lambda c: -c["match_ratio"])
    return {
        "primary_case_id": _to_str_id(primary.id),
        "primary_case_number": primary.case_number,
        "comparisons": comparisons,
    }


# ---------------------------------------------------------------------------
# e) _build_crime_dna
# ---------------------------------------------------------------------------

def _build_crime_dna(
    db: Session,
    entity_type: str,
    entity: Any,
    related_firs: list[FIR],
) -> dict[str, Any]:
    """Generate a structured analytical profile (crime DNA) from related FIRs."""
    categories: Counter[str] = Counter()
    hour_buckets: Counter[str] = Counter()
    day_buckets: Counter[str] = Counter()
    district_buckets: Counter[str] = Counter()
    victim_genders: Counter[str] = Counter()
    victim_ages: list[int] = []
    tools: Counter[str] = Counter()
    sections_freq: Counter[str] = Counter()
    mo_parts: list[str] = []

    for fir in related_firs:
        if fir.filed_at:
            hour_buckets[_time_bucket(fir.filed_at.hour)] += 1
            day_buckets[fir.filed_at.strftime("%A")] += 1

        case = fir.crime_case
        if case:
            if case.category:
                categories[case.category.name] += 1
            if case.location:
                district_buckets[case.location.district] += 1
            if case.mo_tags:
                mo_parts.append(case.mo_tags)

        if fir.sections:
            for s in [x.strip() for x in fir.sections.split(",") if x.strip()]:
                sections_freq[s] += 1

        for lk in fir.victim_links:
            if lk.victim:
                v = lk.victim
                if v.gender:
                    victim_genders[v.gender] += 1
                if v.age is not None:
                    victim_ages.append(v.age)

    # NER extraction across all narratives
    all_text = " ".join(fir.narrative or "" for fir in related_firs)
    extracted: dict[str, list[str]] = {}
    try:
        from app.services.mo_semantic_service import extract_entities as _extract
        ner = _extract(all_text)
        extracted = ner.get("entities", {})
        for w in extracted.get("weapons", []):
            tools[w] += 1
        for d in extracted.get("controlled_substances", []):
            tools[d] += 1
    except Exception:
        pass

    # Components
    components: list[dict[str, Any]] = []

    if categories:
        top = categories.most_common(3)
        components.append({
            "pattern_type": "crime_type",
            "description": f"Primary categories: {', '.join(c for c, _ in top)}",
            "frequency": top[0][1] if top else 0,
            "details": {c: n for c, n in top},
        })

    if hour_buckets:
        top = hour_buckets.most_common(2)
        components.append({
            "pattern_type": "time",
            "description": f"Primary time windows: {', '.join(b for b, _ in top)}",
            "frequency": top[0][1] if top else 0,
            "details": {b: n for b, n in hour_buckets.most_common()},
        })

    if day_buckets:
        top = day_buckets.most_common(3)
        components.append({
            "pattern_type": "day_of_week",
            "description": f"Peak days: {', '.join(d for d, _ in top)}",
            "frequency": top[0][1] if top else 0,
            "details": {d: n for d, n in day_buckets.most_common()},
        })

    if district_buckets:
        top = district_buckets.most_common(3)
        components.append({
            "pattern_type": "location",
            "description": f"Primary districts: {', '.join(d for d, _ in top)}",
            "frequency": top[0][1] if top else 0,
            "details": {d: n for d, n in district_buckets.most_common()},
        })

    if mo_parts:
        components.append({
            "pattern_type": "method",
            "description": f"MO indicators drawn from {len(mo_parts)} record(s)",
            "frequency": len(mo_parts),
            "details": {"mo_summaries": list(set(mo_parts))[:5]},
        })

    if victim_ages:
        avg_age = round(sum(victim_ages) / len(victim_ages), 1)
        components.append({
            "pattern_type": "target",
            "description": f"Victim age range {min(victim_ages)}-{max(victim_ages)}, avg {avg_age}",
            "frequency": len(victim_ages),
            "details": {
                "age_range": [min(victim_ages), max(victim_ages)],
                "average_age": avg_age,
                "gender_distribution": dict(victim_genders),
            },
        })

    if tools:
        top = tools.most_common(5)
        components.append({
            "pattern_type": "tools_weapons",
            "description": f"Common tools/weapons: {', '.join(t for t, _ in top)}",
            "frequency": top[0][1] if top else 0,
            "details": {t: n for t, n in top},
        })

    if sections_freq:
        top = sections_freq.most_common(5)
        components.append({
            "pattern_type": "legal_sections",
            "description": f"Most common sections: {', '.join(s for s, _ in top)}",
            "frequency": top[0][1] if top else 0,
            "details": {s: n for s, n in top},
        })

    # Similarity search
    similarities: list[dict[str, Any]] = []
    query_text = " ".join(mo_parts[:3]) if mo_parts else (all_text[:500] if all_text else "")
    if query_text.strip():
        try:
            from app.services.mo_semantic_service import search_similar_mo
            result = search_similar_mo(db, query_text, top_k=_MAX_SIMILARITIES)
            for match in result.get("results", []):
                doc_id = match.get("doc_id", "")
                kind = match.get("kind", "unknown")
                title = match.get("title", "")
                doc_uuid = doc_id.split("-", 1)[1] if "-" in doc_id else doc_id
                similarities.append({
                    "doc_id": doc_id,
                    "kind": kind,
                    "id": doc_uuid,
                    "case_number": title,
                    "source": f"{kind}:{title}",
                    "score": match.get("similarity"),
                    "matching_attributes": [],
                    "explanation": f"Semantic similarity via {result.get('embedding_method', 'unknown')} — {match.get('excerpt', '')[:100]}",
                })
        except Exception:
            pass

    # Frontend-facing profile (flat attribute -> value map)
    profile: dict[str, str] = {}
    for comp in components:
        profile.setdefault(comp.get("pattern_type", "attribute"), comp.get("description", ""))

    similar_cases: list[dict[str, Any]] = []
    for sim in similarities:
        similar_cases.append({
            "case_id": sim.get("id", ""),
            "case_number": sim.get("case_number") or sim.get("source", ""),
            "similarity_score": float(sim.get("score") or 0),
            "matching_attributes": sim.get("matching_attributes", []),
            "explanation": sim.get("explanation", ""),
            "kind": sim.get("kind", "unknown"),
            "source": sim.get("source", ""),
        })

    return {
        "components": components,
        "profile": profile,
        "similarities": similarities,
        "similar_cases": similar_cases,
        "method": "crime_dna_profile from FIR narratives, MO tags, and NER extraction",
    }


# ---------------------------------------------------------------------------
# f) _rank_investigation_leads
# ---------------------------------------------------------------------------

def _rank_investigation_leads(
    db: Session,
    connections: list[dict[str, Any]],
    common_threads: list[dict[str, Any]],
    crime_dna: dict[str, Any],
) -> list[dict[str, Any]]:
    """Rank the most relevant items for investigation."""
    leads: list[dict[str, Any]] = []
    rank = 0
    sim_score = lambda s: round(min(1.0, max(0.0, float(s or 0))), 2)

    # Related cases from similarities
    for sim in crime_dna.get("similarities", [])[:5]:
        rank += 1
        leads.append({
            "rank": rank,
            "entity_type": "case",
            "entity_id": sim.get("source", ""),
            "entity_name": sim.get("source", ""),
            "entity_detail": "Semantic MO similarity match — cross-reference case records and evidence.",
            "reason": sim.get("explanation", "")[:200],
            "relevance_score": sim_score(sim.get("score")),
            "source_records": [],
        })

    # People to investigate
    for conn in connections:
        if conn["entity_type"] in ("criminal",) and conn["confidence"] in ("confirmed", "probable"):
            rank += 1
            leads.append({
                "rank": rank,
                "entity_type": conn["entity_type"],
                "entity_id": conn["entity_id"],
                "entity_name": conn["entity_name"],
                "entity_detail": conn.get("entity_detail") or conn.get("relationship"),
                "reason": f"{conn.get('relationship', '')} — {conn.get('explanation', '')}",
                "relevance_score": round(conn.get("confidence_score", 0.7), 2),
                "source_records": conn.get("source_records", []),
            })
            if rank >= _MAX_LEADS:
                break

    # Locations to visit
    for conn in connections:
        if conn["entity_type"] == "location" and rank < _MAX_LEADS:
            rank += 1
            leads.append({
                "rank": rank,
                "entity_type": conn["entity_type"],
                "entity_id": conn["entity_id"],
                "entity_name": conn["entity_name"],
                "entity_detail": "Frequent jurisdiction — prioritize field verification.",
                "reason": conn.get("explanation", ""),
                "relevance_score": round(conn.get("confidence_score", 0.7), 2),
                "source_records": conn.get("source_records", []),
            })

    # Evidence to review (from crime_dna extracted entities)
    for sim in crime_dna.get("similarities", [])[:3]:
        if rank >= _MAX_LEADS:
            break
        rank += 1
        leads.append({
            "rank": rank,
            "entity_type": "case",
            "entity_id": sim.get("source", ""),
            "entity_name": f"Review: {sim.get('source', '')}",
            "entity_detail": "High similarity match warrants evidence cross-reference.",
            "reason": sim.get("explanation", "")[:200],
            "relevance_score": sim_score(sim.get("score")),
            "source_records": [],
        })

    # Add thread-based leads for shared patterns
    for thread in common_threads[:3]:
        if rank >= _MAX_LEADS:
            break
        rank += 1
        leads.append({
            "rank": rank,
            "entity_type": "pattern",
            "entity_id": thread.get("attribute", ""),
            "entity_name": thread.get("value", thread.get("attribute", "")),
            "entity_detail": f"Shared attribute: {thread.get('attribute', '')}",
            "reason": thread.get("explanation", ""),
            "relevance_score": 0.8,
            "source_records": thread.get("source_records", []),
        })

    leads = leads[:_MAX_LEADS]
    for i, lead in enumerate(leads):
        lead["rank"] = i + 1
    return leads


# ---------------------------------------------------------------------------
# g) _build_timeline
# ---------------------------------------------------------------------------

def _build_timeline(
    db: Session,
    entity_type: str,
    entity: Any,
    related_firs: list[FIR],
    related_cases: list[CrimeCase],
) -> list[dict[str, Any]]:
    """Combine events chronologically from all related records."""
    events: list[dict[str, Any]] = []

    for fir in related_firs:
        if fir.filed_at:
            events.append({
                "timestamp": _ts(fir.filed_at),
                "event": f"FIR {fir.fir_number} registered — Sections: {fir.sections or 'N/A'}",
                "source_type": "fir",
                "source_id": _to_str_id(fir.id),
            })
        if fir.status == "closed" and fir.created_at:
            events.append({
                "timestamp": _ts(fir.created_at),
                "event": f"FIR {fir.fir_number} closed",
                "source_type": "fir",
                "source_id": _to_str_id(fir.id),
            })

    for case in related_cases:
        if case.reported_at:
            events.append({
                "timestamp": _ts(case.reported_at),
                "event": f"Case {case.case_number} reported — Status: {case.status}",
                "source_type": "crime_case",
                "source_id": _to_str_id(case.id),
            })

        # Evidence collection events
        evidence_list = db.query(Evidence).filter(Evidence.case_id == case.id).all()
        for ev in evidence_list:
            if ev.created_at:
                events.append({
                    "timestamp": _ts(ev.created_at),
                    "event": f"Evidence collected: {ev.title} ({ev.evidence_type})",
                    "source_type": "evidence",
                    "source_id": _to_str_id(ev.id),
                })

        # Investigation notes
        notes = db.query(InvestigationNote).filter(InvestigationNote.case_id == case.id).all()
        for note in notes:
            if note.created_at:
                events.append({
                    "timestamp": _ts(note.created_at),
                    "event": f"Investigation note by {note.officer_name}",
                    "source_type": "investigation_note",
                    "source_id": _to_str_id(note.id),
                })

    # Audit log entries for the cases
    from app.models.audit_log import AuditLog
    case_ids_str = [_to_str_id(c.id) for c in related_cases]
    if case_ids_str:
        audit_entries = (
            db.query(AuditLog)
            .filter(AuditLog.resource_id.in_(case_ids_str))
            .order_by(AuditLog.timestamp.asc())
            .limit(50)
            .all()
        )
        for entry in audit_entries:
            if entry.timestamp:
                events.append({
                    "timestamp": _ts(entry.timestamp),
                    "event": f"Audit: {entry.action} on {entry.resource_type} — {entry.details or ''}",
                    "source_type": "audit_log",
                    "source_id": _to_str_id(entry.id),
                })

    events.sort(key=lambda e: e["timestamp"] or "")
    return events


# ---------------------------------------------------------------------------
# g2) _analyze_temporal_velocity
# ---------------------------------------------------------------------------

def _analyze_temporal_velocity(
    related_firs: list[FIR],
) -> dict[str, Any]:
    """Compute escalation velocity and active period metrics from FIR timestamps."""
    timestamps: list[datetime] = []
    for fir in related_firs:
        if fir.filed_at:
            timestamps.append(fir.filed_at)
    if len(timestamps) < 2:
        return {"status": "insufficient_data", "firs_analyzed": len(related_firs), "metrics": {}}
    timestamps.sort()
    gaps: list[float] = []
    for i in range(1, len(timestamps)):
        delta = (timestamps[i] - timestamps[i - 1]).total_seconds() / 86400.0
        gaps.append(round(delta, 1))
    avg_gap = round(sum(gaps) / len(gaps), 1) if gaps else 0
    min_gap = round(min(gaps), 1) if gaps else 0
    max_gap = round(max(gaps), 1) if gaps else 0
    total_span_days = round((timestamps[-1] - timestamps[0]).total_seconds() / 86400.0, 1)
    return {
        "status": "computed",
        "firs_analyzed": len(related_firs),
        "metrics": {
            "total_span_days": total_span_days,
            "avg_gap_days": avg_gap,
            "min_gap_days": min_gap,
            "max_gap_days": max_gap,
            "fir_count": len(timestamps),
            "first_fir": _ts(timestamps[0]),
            "last_fir": _ts(timestamps[-1]),
            "escalation_trend": "accelerating" if gaps and gaps[-1] < gaps[0] else "decelerating" if gaps and gaps[-1] > gaps[0] else "stable",
        },
    }


# ---------------------------------------------------------------------------
# g3) _cross_reference_evidence
# ---------------------------------------------------------------------------

def _cross_reference_evidence(
    db: Session,
    related_firs: list[FIR],
    extracted_entities: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Cross-reference NER-extracted entities (plates, weapons, phones) against evidence records."""
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    all_values: list[str] = []
    for kind, vals in extracted_entities.items():
        for v in vals:
            all_values.append(v)
    if not all_values:
        return refs
    for fir in related_firs:
        if not fir.crime_case_id:
            continue
        evidence_list = db.query(Evidence).filter(Evidence.case_id == fir.crime_case_id).all()
        for ev in evidence_list:
            title_lower = (ev.title or "").lower()
            desc_lower = (ev.description or "").lower()
            combined = f"{title_lower} {desc_lower}"
            for val in all_values:
                if val.lower() in combined and val not in seen:
                    seen.add(val)
                    refs.append({
                        "entity_type": "extracted_entity",
                        "entity_id": val,
                        "entity_name": val,
                        "connection_type": "evidence_cross_reference",
                        "entity_detail": f"NER-extracted '{val}' matches evidence record '{ev.title}'",
                        "confidence_score": 0.7,
                        "confidence": "probable",
                        "explanation": f"Extracted entity '{val}' appears in evidence metadata for case FIR {fir.fir_number}",
                        "source_records": [{"record_type": "evidence", "record_id": _to_str_id(ev.id), "record_number": ev.title}],
                    })
    return refs


# ---------------------------------------------------------------------------
# h) _detect_pattern_breaks
# ---------------------------------------------------------------------------

def _detect_pattern_breaks(
    db: Session,
    entity_type: str,
    entity: Any,
    related_firs: list[FIR],
    common_threads: list[dict[str, Any]],
) -> dict[str, Any]:
    """Identify unusual behavior ONLY when sufficient data exists."""
    if len(related_firs) < 3:
        return {
            "status": "insufficient_data",
            "message": f"Only {len(related_firs)} FIR(s) available — pattern break detection requires at least 3 records",
            "pattern_breaks": [],
        }

    # Build baselines from all FIRs
    hour_buckets: Counter[str] = Counter()
    district_buckets: Counter[str] = Counter()
    category_buckets: Counter[str] = Counter()

    for fir in related_firs:
        if fir.filed_at:
            hour_buckets[_time_bucket(fir.filed_at.hour)] += 1
        if fir.crime_case:
            if fir.crime_case.location:
                district_buckets[fir.crime_case.location.district] += 1
            if fir.crime_case.category:
                category_buckets[fir.crime_case.category.name] += 1

    pattern_breaks: list[dict[str, Any]] = []

    # Time pattern break: if one FIR is in an unusual time window
    if hour_buckets:
        dominant_time = hour_buckets.most_common(1)[0]
        for fir in related_firs:
            if fir.filed_at:
                bucket = _time_bucket(fir.filed_at.hour)
                if bucket != dominant_time[0] and hour_buckets[bucket] == 1:
                    pattern_breaks.append({
                        "pattern_type": "unusual_time",
                        "baseline": f"Most incidents during {dominant_time[0]} ({dominant_time[1]}/{len(related_firs)} FIRs)",
                        "deviation": f"FIR {fir.fir_number} filed during {bucket} — deviates from established pattern",
                        "confidence": "possible",
                        "supporting_records": [{"record_type": "fir", "record_id": _to_str_id(fir.id), "record_number": fir.fir_number}],
                    })

    # District pattern break
    if len(district_buckets) > 1:
        dominant_dist = district_buckets.most_common(1)[0]
        for fir in related_firs:
            if fir.crime_case and fir.crime_case.location:
                dist = fir.crime_case.location.district
                if dist != dominant_dist[0] and district_buckets[dist] == 1:
                    pattern_breaks.append({
                        "pattern_type": "unusual_location",
                        "baseline": f"Primary operational area: {dominant_dist[0]} ({dominant_dist[1]}/{len(related_firs)} FIRs)",
                        "deviation": f"FIR {fir.fir_number} in {dist} — outside usual geographic pattern",
                        "confidence": "possible",
                        "supporting_records": [{"record_type": "fir", "record_id": _to_str_id(fir.id), "record_number": fir.fir_number}],
                    })

    # Crime type pattern break
    if len(category_buckets) > 1:
        dominant_cat = category_buckets.most_common(1)[0]
        for fir in related_firs:
            if fir.crime_case and fir.crime_case.category:
                cat = fir.crime_case.category.name
                if cat != dominant_cat[0] and category_buckets[cat] == 1:
                    pattern_breaks.append({
                        "pattern_type": "unusual_crime_type",
                        "baseline": f"Primary crime type: {dominant_cat[0]} ({dominant_cat[1]}/{len(related_firs)} FIRs)",
                        "deviation": f"FIR {fir.fir_number} classified as {cat} — inconsistent with established pattern",
                        "confidence": "possible",
                        "supporting_records": [{"record_type": "fir", "record_id": _to_str_id(fir.id), "record_number": fir.fir_number}],
                    })

    return {
        "status": "sufficient_data" if pattern_breaks else "no_breaks_detected",
        "message": f"Analyzed {len(related_firs)} FIRs — found {len(pattern_breaks)} potential pattern break(s)" if pattern_breaks else f"Analyzed {len(related_firs)} FIRs — no significant pattern breaks detected",
        "pattern_breaks": pattern_breaks,
    }


# ---------------------------------------------------------------------------
# i) build_intelligence  — MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def build_intelligence(db: Session, entity_type: str, entity_id: str) -> dict[str, Any]:
    """Orchestrate all analysis functions and return a unified intelligence report."""
    if entity_type not in _VALID_ENTITY_TYPES:
        raise ValueError(f"Invalid entity_type '{entity_type}'. Must be one of {sorted(_VALID_ENTITY_TYPES)}")

    # 1. Resolve entity
    resolved = _resolve_entity(db, entity_type, entity_id)
    entity = resolved["entity"]
    related_fir_ids = resolved["related_fir_ids"]
    related_case_ids = resolved["related_case_ids"]

    # 2. Load related FIRs for timeline and DNA
    related_firs = (
        db.query(FIR)
        .options(
            joinedload(FIR.crime_case).joinedload(CrimeCase.category),
            joinedload(FIR.crime_case).joinedload(CrimeCase.location),
            joinedload(FIR.criminal_links).joinedload(FIRCriminalLink.criminal),
            joinedload(FIR.victim_links).joinedload(FIRVictimLink.victim),
            joinedload(FIR.investigating_officer),
        )
        .filter(FIR.id.in_(related_fir_ids))
        .all()
    ) if related_fir_ids else []

    # 3. Load related cases
    related_cases = (
        db.query(CrimeCase)
        .options(
            joinedload(CrimeCase.category),
            joinedload(CrimeCase.location),
        )
        .filter(CrimeCase.id.in_(related_case_ids))
        .all()
    ) if related_case_ids else []

    # 4. Connections
    connections = _find_connections(db, entity_type, entity, related_fir_ids)

    # 5. Common threads
    common_threads = _find_common_threads(db, related_fir_ids, related_case_ids)

    # 6. Case comparison (for cases and FIRs with linked cases)
    case_comparison = None
    if entity_type == "case" and len(related_case_ids) > 1:
        other_ids = [cid for cid in related_case_ids if cid != uuid.UUID(entity_id)]
        if other_ids:
            case_comparison = _compare_cases(db, uuid.UUID(entity_id), other_ids)
    elif entity_type == "fir" and len(related_case_ids) > 1:
        # Compare the FIR's case against sibling cases
        fir_case_id = related_case_ids[0] if related_case_ids else None
        other_ids = [cid for cid in related_case_ids if cid != fir_case_id]
        if fir_case_id and other_ids:
            case_comparison = _compare_cases(db, fir_case_id, other_ids)

    # 7. Crime DNA
    crime_dna = _build_crime_dna(db, entity_type, entity, related_firs)

    # 8. Investigation leads
    investigation_leads = _rank_investigation_leads(db, connections, common_threads, crime_dna)

    # 9. Timeline
    timeline = _build_timeline(db, entity_type, entity, related_firs, related_cases)

    # 10. Pattern breaks
    pattern_breaks = _detect_pattern_breaks(db, entity_type, entity, related_firs, common_threads)

    # 11. Network snapshot (focused subset — SQL fallback when Neo4j unavailable)
    network_snapshot = None
    try:
        from app.services.network.network_service import get_person_network_graph, get_case_network_graph
        if entity_type in ("criminal", "victim"):
            net_resp = get_person_network_graph(db, f"{entity_type}-{entity_id}", depth=1)
            network_snapshot = {
                "nodes": [{"id": n.id, "name": n.name, "type": n.category.value, "category": n.category.value, "riskScore": n.riskScore} for n in net_resp.nodes],
                "edges": [{"source": e.source, "target": e.target, "relationship": e.relationship, "confidence": e.confidence} for e in net_resp.edges],
            }
        elif entity_type == "case":
            net_resp = get_case_network_graph(db, entity_id)
            network_snapshot = {
                "nodes": [{"id": n.id, "name": n.name, "type": n.category.value, "category": n.category.value, "riskScore": n.riskScore} for n in net_resp.nodes],
                "edges": [{"source": e.source, "target": e.target, "relationship": e.relationship, "confidence": e.confidence} for e in net_resp.edges],
            }
    except Exception:
        # SQL-only fallback: build network directly from FIR relationships
        try:
            _nodes_map: dict[str, dict[str, Any]] = {}
            _edges: list[dict[str, Any]] = []
            for fir in related_firs:
                case_node_id = f"case-{_to_str_id(fir.crime_case_id)}" if fir.crime_case_id else None
                if case_node_id and case_node_id not in _nodes_map:
                    _nodes_map[case_node_id] = {"id": case_node_id, "name": fir.crime_case.case_number if fir.crime_case else "Case", "type": "case", "category": "case", "riskScore": 60.0}
                for lk in fir.criminal_links:
                    if lk.criminal:
                        cn_id = f"criminal-{_to_str_id(lk.criminal.id)}"
                        if cn_id not in _nodes_map:
                            _nodes_map[cn_id] = {"id": cn_id, "name": lk.criminal.full_name, "type": "criminal", "category": "criminal", "riskScore": 70.0}
                        if case_node_id:
                            _edges.append({"source": cn_id, "target": case_node_id, "relationship": "LINKED_TO", "confidence": "confirmed"})
                for lk in fir.victim_links:
                    if lk.victim:
                        vn_id = f"victim-{_to_str_id(lk.victim.id)}"
                        if vn_id not in _nodes_map:
                            _nodes_map[vn_id] = {"id": vn_id, "name": lk.victim.full_name, "type": "victim", "category": "victim", "riskScore": 0.0}
                        if case_node_id:
                            _edges.append({"source": vn_id, "target": case_node_id, "relationship": "VICTIM_OF", "confidence": "confirmed"})
                if fir.investigating_officer:
                    on_id = f"officer-{_to_str_id(fir.investigating_officer.id)}"
                    if on_id not in _nodes_map:
                        _nodes_map[on_id] = {"id": on_id, "name": fir.investigating_officer.name, "type": "officer", "category": "officer", "riskScore": 0.0}
                    if case_node_id:
                        _edges.append({"source": on_id, "target": case_node_id, "relationship": "INVESTIGATING", "confidence": "confirmed"})
            if _nodes_map:
                network_snapshot = {"nodes": list(_nodes_map.values()), "edges": _edges}
        except Exception:
            network_snapshot = None

    # 12. Confidence summary
    confirmed_count = sum(1 for c in connections if c["confidence"] == "confirmed")
    probable_count = sum(1 for c in connections if c["confidence"] == "probable")
    possible_count = sum(1 for c in connections if c["confidence"] == "possible")
    confidence_summary = {
        "confirmed": confirmed_count,
        "probable": probable_count,
        "possible": possible_count,
        "insufficient": 0,
        "total_insights": confirmed_count + probable_count + possible_count,
    }

    # 13. Temporal velocity analysis
    temporal_velocity = _analyze_temporal_velocity(related_firs)

    # 14. Evidence cross-references (NER entities vs evidence metadata)
    _extracted: dict[str, list[str]] = defaultdict(list)
    for fir in related_firs:
        if fir.narrative:
            try:
                from app.services.mo_semantic_service import extract_entities
                ner = extract_entities(fir.narrative)
                for kind in ("phone_numbers", "vehicle_plates", "weapons"):
                    for val in ner.get("entities", {}).get(kind, []):
                        _extracted[kind].append(val)
            except Exception:
                pass
    evidence_refs = _cross_reference_evidence(db, related_firs, _extracted)
    connections.extend(evidence_refs)

    # 15. Summary (2-3 sentence intelligence summary)
    summary_parts = []
    summary_parts.append(f"Intelligence report for {resolved['label']}: {len(related_firs)} related FIR(s) and {len(related_case_ids)} related case(s) identified.")
    if common_threads:
        top_thread = common_threads[0]
        summary_parts.append(f"Primary common thread: {top_thread['attribute']} = {top_thread['value']} (across {top_thread['case_count']} cases).")
    if investigation_leads:
        summary_parts.append(f"{len(investigation_leads)} investigative lead(s) ranked by relevance.")
    summary = " ".join(summary_parts)

    # 14. Explainability
    pattern_break_list = pattern_breaks.get("pattern_breaks", [])
    explainability = {
        "method": "Deterministic aggregation over the crime registry: FIR/criminal/victim link graph, crime case metadata, MO semantic similarity (LSA cosine) and temporal pattern analysis.",
        "data_sources": [
            "crime_cases", "firs", "fir_criminal_links", "fir_victim_links",
            "criminals", "victims", "evidence", "investigation_notes",
        ],
        "limitations": [
            "Inferred and possible connections are analytical hypotheses — they must be corroborated with field intelligence before acting on them.",
            "Results are limited to records present in the authorized database; missing records imply absent connections, not exculpation.",
            "Pattern break detection requires at least 3 related FIRs.",
        ],
        "entity_type": entity_type,
        "entity_id": entity_id,
        "related_firs_analyzed": len(related_firs),
        "related_cases_analyzed": len(related_cases),
        "connections_found": len(connections),
        "threads_found": len(common_threads),
        "leads_ranked": len(investigation_leads),
        "timeline_events": len(timeline),
        "pattern_breaks_detected": len(pattern_break_list),
        "pattern_break_status": pattern_breaks.get("status", "unknown"),
        "semantic_search_used": bool(crime_dna.get("similarities")),
        "network_available": network_snapshot is not None,
    }

    # 15. Normalize source records to the {type, id, label} contract
    for c in connections:
        c["source_records"] = _normalize_sources(c.get("source_records"))
    for t in common_threads:
        t["source_records"] = _normalize_sources(t.get("source_records"))
    for l in investigation_leads:
        l["source_records"] = _normalize_sources(l.get("source_records"))
    normalized_pattern_breaks: list[dict[str, Any]] = []
    for p in pattern_break_list:
        p = dict(p)
        p["supporting_records"] = _normalize_sources(p.get("supporting_records"))
        normalized_pattern_breaks.append(p)

    return {
        "entity_info": resolved["info"],
        "summary": summary,
        "connections": connections,
        "common_threads": common_threads,
        "case_comparison": case_comparison,
        "crime_dna": crime_dna,
        "investigation_leads": investigation_leads,
        "timeline": timeline,
        "temporal_velocity": temporal_velocity,
        "network_snapshot": network_snapshot,
        "pattern_breaks": normalized_pattern_breaks,
        "confidence_summary": confidence_summary,
        "explainability": explainability,
    }
