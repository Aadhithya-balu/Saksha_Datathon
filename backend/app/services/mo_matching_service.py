"""Modus Operandi (MO) Pattern Matching and Explainable Similarity Engine.

Analyzes real database records (CrimeCase, Criminal, FIR, Location, Evidence, MOTag)
to construct normalized MO profiles, compute weighted multi-feature similarity,
properly handle missing/unknown data without false matches, and generate
evidence-grounded explainability factors.
"""
from __future__ import annotations

import logging
import re
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session, joinedload

from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink
from app.models.location import Location
from app.services.mo_pattern_service import (
    NIGHT_TAG_NAMES,
    VEHICLE_TAG_NAMES,
    WEAPON_TAG_NAMES,
    ensure_synced,
    tags_for_case_text,
    tags_for_text,
)
from app.services.mo_semantic_service import extract_entities


# ---------------------------------------------------------------------------
# Structured MO Profile Representation
# ---------------------------------------------------------------------------

@dataclass
class MOProfile:
    entity_id: str
    entity_type: str  # "case" | "criminal"
    label: str        # case_number or full_name
    category: str | None = None
    mo_tags: set[str] = field(default_factory=set)
    methods: list[str] = field(default_factory=list)
    weapons: list[str] = field(default_factory=list)
    vehicles: list[str] = field(default_factory=list)
    target_type: str | None = None
    district: str | None = None
    station: str | None = None
    time_window: str | None = None  # "00:00-06:00" | "06:00-12:00" | "12:00-18:00" | "18:00-24:00"
    day_of_week: str | None = None
    sections: list[str] = field(default_factory=list)
    gang_affiliation: str | None = None
    status: str | None = None
    raw_narrative: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["mo_tags"] = sorted(self.mo_tags)
        return data


def _get_time_window(hour: int) -> str:
    if 0 <= hour < 6:
        return "00:00-06:00 (Late Night)"
    if 6 <= hour < 12:
        return "06:00-12:00 (Morning)"
    if 12 <= hour < 18:
        return "12:00-18:00 (Afternoon/Evening)"
    return "18:00-24:00 (Night)"


def _infer_target_type(text: str) -> str | None:
    if not text:
        return None
    t = text.lower()
    if re.search(r"\b(residen|house|flat|apartment|home|dwelling|villa|bungalow)\b", t):
        return "Residential Property"
    if re.search(r"\b(bank|atm|cash|gold|jewel|vault|chest|loan|finance)\b", t):
        return "Financial / High Value"
    if re.search(r"\b(shop|store|mall|market|warehouse|godown|commercial|business|office)\b", t):
        return "Commercial Establishment"
    if re.search(r"\b(highway|truck|transit|transport|bus|road|toll|vehicle|cargo)\b", t):
        return "Transit / Transport"
    if re.search(r"\b(temple|hundi|shrine|mosque|church|religious)\b", t):
        return "Religious / Public Place"
    if re.search(r"\b(cyber|phishing|online|upi|portal|account|biometric|data)\b", t):
        return "Digital / Cyber Target"
    if re.search(r"\b(individual|pedestrian|senior|woman|elderly|commuter)\b", t):
        return "Individual / Person"
    return None


# ---------------------------------------------------------------------------
# Profile-level cache
# ---------------------------------------------------------------------------
# The dominant cold cost of matching is re-extracting the MO profile for every
# case and every criminal in the database per cache miss (~40s+ on real data).
# Cache the individual extracted profiles (keyed by entity id) so a later cold
# match only recomputes the single *target* profile, not the whole table.
_prof_cache: dict[str, tuple[float, str]] = {}
_prof_cache_lock = threading.Lock()
_PROF_CACHE_TTL = timedelta(minutes=10)


def _profile_cached(key: str, compute) -> str:
    """Return a cached serialized MO profile or compute+store a fresh one."""
    now = datetime.now(timezone.utc)
    with _prof_cache_lock:
        entry = _prof_cache.get(key)
        if entry is not None and entry[0] > now:
            return entry[1]
    value = compute()
    import json as _json
    serialized = _json.dumps(asdict(value), default=str, sort_keys=True)
    with _prof_cache_lock:
        _prof_cache[key] = (now + _PROF_CACHE_TTL, serialized)
    return serialized


def _profile_from_cache(key: str, build) -> MOProfile:
    """Build (or load from cache) an MOProfile for a stable entity id."""
    from dataclasses import fields as _fields

    def _compute() -> MOProfile:
        return build()

    raw = _profile_cached(key, _compute)
    import json as _json
    try:
        data = _json.loads(raw)
        kwargs = {f.name: data.get(f.name) for f in _fields(MOProfile)}
        kwargs["mo_tags"] = set(data.get("mo_tags") or [])
        return MOProfile(**kwargs)
    except Exception:
        return build()


def extract_case_mo_profile(db: Session, case: CrimeCase) -> MOProfile:
    def _build() -> MOProfile:
        return _extract_case_mo_profile_uncached(db, case)

    key = f"case:{case.id}"
    return _profile_from_cache(key, _build)


def _extract_case_mo_profile_uncached(db: Session, case: CrimeCase) -> MOProfile:
    """Extract structured MO profile from a real CrimeCase record and linked FIRs."""
    tags = tags_for_case_text(case)

    # Narrative combining description and FIR narratives
    narrative_parts = [case.description or "", case.mo_tags or ""]
    sections_list = []
    for fir in case.firs or []:
        if fir.narrative:
            narrative_parts.append(fir.narrative)
        if fir.sections:
            for s in fir.sections.split(","):
                clean_s = s.strip()
                if clean_s and clean_s not in sections_list:
                    sections_list.append(clean_s)

    combined_narrative = " ".join(filter(None, narrative_parts))
    extracted = extract_entities(combined_narrative) if combined_narrative else {"weapons": [], "vehicle_plates": []}

    time_win = _get_time_window(case.occurred_at.hour) if case.occurred_at else None
    day_name = case.occurred_at.strftime("%A") if case.occurred_at else None
    target = _infer_target_type(combined_narrative)

    # Compile methods from tags
    methods = [t for t in tags if t not in NIGHT_TAG_NAMES and t not in WEAPON_TAG_NAMES and t not in VEHICLE_TAG_NAMES]

    return MOProfile(
        entity_id=str(case.id),
        entity_type="case",
        label=case.case_number,
        category=case.category.name if case.category else None,
        mo_tags=tags,
        methods=methods,
        weapons=extracted.get("weapons", []),
        vehicles=extracted.get("vehicle_plates", []),
        target_type=target,
        district=case.location.district if case.location else None,
        station=case.location.station if case.location else None,
        time_window=time_win,
        day_of_week=day_name,
        sections=sections_list,
        status=case.status,
        raw_narrative=case.description or case.mo_tags or "",
    )


def extract_criminal_mo_profile(db: Session, criminal: Criminal) -> MOProfile:
    def _build() -> MOProfile:
        return _extract_criminal_mo_profile_uncached(db, criminal)

    key = f"criminal:{criminal.id}"
    return _profile_from_cache(key, _build)


def _extract_criminal_mo_profile_uncached(db: Session, criminal: Criminal) -> MOProfile:
    """Extract structured MO profile from a real Criminal record and historical cases."""
    tags = tags_for_text(criminal.mo_summary)

    # Aggregate information from linked FIR cases
    districts = set()
    stations = set()
    categories = set()
    time_windows = set()
    sections_list = []
    all_narratives = [criminal.mo_summary or ""]

    for link in criminal.fir_links or []:
        fir = link.fir
        if fir:
            if fir.narrative:
                all_narratives.append(fir.narrative)
            if fir.sections:
                for s in fir.sections.split(","):
                    clean_s = s.strip()
                    if clean_s and clean_s not in sections_list:
                        sections_list.append(clean_s)
            case = fir.crime_case
            if case:
                tags.update(tags_for_case_text(case))
                if case.category:
                    categories.add(case.category.name)
                if case.location:
                    if case.location.district:
                        districts.add(case.location.district)
                    if case.location.station:
                        stations.add(case.location.station)
                if case.occurred_at:
                    time_windows.add(_get_time_window(case.occurred_at.hour))

    combined = " ".join(filter(None, all_narratives))
    extracted = extract_entities(combined) if combined else {"weapons": [], "vehicle_plates": []}
    target = _infer_target_type(combined)
    methods = [t for t in tags if t not in NIGHT_TAG_NAMES and t not in WEAPON_TAG_NAMES and t not in VEHICLE_TAG_NAMES]

    primary_cat = sorted(categories)[0] if categories else None
    primary_district = sorted(districts)[0] if districts else None
    primary_station = sorted(stations)[0] if stations else None
    primary_time = sorted(time_windows)[0] if time_windows else ("00:00-06:00 (Late Night)" if tags & NIGHT_TAG_NAMES else None)

    return MOProfile(
        entity_id=str(criminal.id),
        entity_type="criminal",
        label=criminal.full_name,
        category=primary_cat,
        mo_tags=tags,
        methods=methods,
        weapons=extracted.get("weapons", []),
        vehicles=extracted.get("vehicle_plates", []),
        target_type=target,
        district=primary_district,
        station=primary_station,
        time_window=primary_time,
        sections=sections_list,
        gang_affiliation=criminal.gang_affiliation,
        status=criminal.status,
        raw_narrative=criminal.mo_summary or "",
    )


# ---------------------------------------------------------------------------
# Explainable Weighted Similarity Engine
# ---------------------------------------------------------------------------

FEATURE_WEIGHTS = {
    "mo_tags": 0.35,      # Tactical method & MO tags
    "category": 0.20,     # Crime category & section codes
    "weapons": 0.15,      # Weapon / tool overlap
    "time_window": 0.10,  # Temporal window overlap
    "location": 0.10,     # District / station corridor
    "target_type": 0.05,  # Target environment
    "vehicles": 0.05,     # Vehicle / transit signature
}


@dataclass
class SimilarityEvaluation:
    score: float  # 0.0 to 1.0
    match_level: str  # "high" (>= 0.75) | "medium" (0.50 - 0.74) | "low" (0.30 - 0.49) | "none" (< 0.30)
    confidence: float
    matching_factors: list[str]
    divergent_factors: list[str]
    insufficient_data: list[str]
    dimension_scores: dict[str, float]


def calculate_mo_similarity(a: MOProfile, b: MOProfile) -> SimilarityEvaluation:
    """Calculate multi-feature explainable MO similarity between two profiles.

    Strict rules:
    - Missing data (NULL / empty) in either profile is marked as 'insufficient_data'
      and does NOT count as a match or mismatch. Its weight is excluded from the denominator.
    - Two records sharing only a generic crime category receive a low score if MO tags diverge.
    - Scores and explainable reasons are mathematically grounded in the features.
    """
    applicable_weights = 0.0
    earned_score = 0.0

    matching_factors: list[str] = []
    divergent_factors: list[str] = []
    insufficient_data: list[str] = []
    dim_scores: dict[str, float] = {}

    # 1. MO Tags & Tactical Methods (Weight: 35%)
    w_mo = FEATURE_WEIGHTS["mo_tags"]
    if a.mo_tags and b.mo_tags:
        applicable_weights += w_mo
        shared_tags = a.mo_tags & b.mo_tags
        union_tags = a.mo_tags | b.mo_tags
        jaccard = len(shared_tags) / len(union_tags) if union_tags else 0.0
        # Boost if multiple specific tactics overlap
        score_val = jaccard
        earned_score += score_val * w_mo
        dim_scores["mo_tags"] = round(score_val, 3)

        if shared_tags:
            tag_list_str = ", ".join(sorted(shared_tags)[:3])
            matching_factors.append(f"Shared MO Signature: {len(shared_tags)} overlapping tactic(s) ({tag_list_str})")
        else:
            divergent_factors.append("Distinct Tactical Methods: No shared modus-operandi tags")
    else:
        insufficient_data.append("Tactical MO Tags: Insufficient structured notes in one or both records")
        dim_scores["mo_tags"] = 0.0

    # 2. Crime Category & Section Codes (Weight: 20%)
    w_cat = FEATURE_WEIGHTS["category"]
    if a.category and b.category:
        applicable_weights += w_cat
        cat_a = a.category.lower().strip()
        cat_b = b.category.lower().strip()

        shared_sections = set(a.sections) & set(b.sections) if (a.sections and b.sections) else set()

        if cat_a == cat_b or cat_a in cat_b or cat_b in cat_a:
            earned_score += 1.0 * w_cat
            dim_scores["category"] = 1.0
            sec_info = f" with shared legal sections: {', '.join(sorted(shared_sections))}" if shared_sections else ""
            matching_factors.append(f"Matching Crime Category: '{a.category}'{sec_info}")
        else:
            dim_scores["category"] = 0.0
            divergent_factors.append(f"Differing Crime Categories: '{a.category}' vs '{b.category}'")
    else:
        insufficient_data.append("Crime Category: Missing category classification")
        dim_scores["category"] = 0.0

    # 3. Weapons & Tools (Weight: 15%)
    w_wep = FEATURE_WEIGHTS["weapons"]
    if a.weapons and b.weapons:
        applicable_weights += w_wep
        shared_weps = set(a.weapons) & set(b.weapons)
        if shared_weps:
            earned_score += 1.0 * w_wep
            dim_scores["weapons"] = 1.0
            matching_factors.append(f"Identical Weapon/Tool Signature: {', '.join(sorted(shared_weps))}")
        else:
            dim_scores["weapons"] = 0.0
            divergent_factors.append(f"Different Weapon Classes: '{', '.join(a.weapons)}' vs '{', '.join(b.weapons)}'")
    else:
        # Crucial requirement: Missing weapon data MUST NOT count as match
        insufficient_data.append("Weapon / Tool Inventory: No specific weapons registered in one or both entities")
        dim_scores["weapons"] = 0.0

    # 4. Temporal / Time Window (Weight: 10%)
    w_time = FEATURE_WEIGHTS["time_window"]
    if a.time_window and b.time_window:
        applicable_weights += w_time
        if a.time_window == b.time_window:
            earned_score += 1.0 * w_time
            dim_scores["time_window"] = 1.0
            matching_factors.append(f"Operating Time Window: Both active during {a.time_window}")
        else:
            dim_scores["time_window"] = 0.0
            divergent_factors.append(f"Disparate Time Windows: '{a.time_window}' vs '{b.time_window}'")
    else:
        insufficient_data.append("Temporal Operating Window: Incident timestamp unrecorded")
        dim_scores["time_window"] = 0.0

    # 5. Geographic Location / District Corridor (Weight: 10%)
    w_loc = FEATURE_WEIGHTS["location"]
    if a.district and b.district:
        applicable_weights += w_loc
        dist_a = a.district.lower().strip()
        dist_b = b.district.lower().strip()

        if dist_a == dist_b:
            if a.station and b.station and a.station.lower() == b.station.lower():
                earned_score += 1.0 * w_loc
                dim_scores["location"] = 1.0
                matching_factors.append(f"Precise Location Corridor: Same police station jurisdiction ({a.station}, {a.district})")
            else:
                earned_score += 0.8 * w_loc
                dim_scores["location"] = 0.8
                matching_factors.append(f"Geographic Proximity: Same district jurisdiction ({a.district})")
        else:
            dim_scores["location"] = 0.0
            divergent_factors.append(f"Geographic Separation: {a.district} vs {b.district}")
    else:
        insufficient_data.append("Geographic Location: Location coordinates unavailable")
        dim_scores["location"] = 0.0

    # 6. Target Environment / Type (Weight: 5%)
    w_tgt = FEATURE_WEIGHTS["target_type"]
    if a.target_type and b.target_type:
        applicable_weights += w_tgt
        if a.target_type == b.target_type:
            earned_score += 1.0 * w_tgt
            dim_scores["target_type"] = 1.0
            matching_factors.append(f"Target Environment Match: {a.target_type}")
        else:
            dim_scores["target_type"] = 0.0
            divergent_factors.append(f"Target Type Variation: '{a.target_type}' vs '{b.target_type}'")
    else:
        insufficient_data.append("Target Environment: Target characteristics not explicitly categorized")
        dim_scores["target_type"] = 0.0

    # 7. Vehicle & Evasion Pattern (Weight: 5%)
    w_veh = FEATURE_WEIGHTS["vehicles"]
    if a.vehicles and b.vehicles:
        applicable_weights += w_veh
        shared_veh = set(a.vehicles) & set(b.vehicles)
        if shared_veh:
            earned_score += 1.0 * w_veh
            dim_scores["vehicles"] = 1.0
            matching_factors.append(f"Matching Vehicle / Plate Pattern: {', '.join(sorted(shared_veh))}")
        else:
            dim_scores["vehicles"] = 0.0
            divergent_factors.append("Vehicle Signature: Different vehicle identifiers")
    else:
        insufficient_data.append("Vehicle / Getaway: No vehicle descriptions logged")
        dim_scores["vehicles"] = 0.0

    # Calculate final normalized score based only on applicable weights
    final_score = (earned_score / applicable_weights) if applicable_weights > 0 else 0.0
    final_score = min(1.0, max(0.0, round(final_score, 4)))

    # Confidence is determined by the proportion of features evaluated
    confidence = round(applicable_weights / sum(FEATURE_WEIGHTS.values()), 2)

    # Classify match level
    if final_score >= 0.75 and confidence >= 0.5:
        match_level = "high"
    elif final_score >= 0.50:
        match_level = "medium"
    elif final_score >= 0.30:
        match_level = "low"
    else:
        match_level = "none"

    return SimilarityEvaluation(
        score=final_score,
        match_level=match_level,
        confidence=confidence,
        matching_factors=matching_factors,
        divergent_factors=divergent_factors,
        insufficient_data=insufficient_data,
        dimension_scores=dim_scores,
    )


# ---------------------------------------------------------------------------
# High-Level Investigative Match Queries (Database Source of Truth)
# ---------------------------------------------------------------------------

def _is_confirmed_link(db: Session, case_id: uuid.UUID, criminal_id: uuid.UUID) -> bool:
    """Check whether a criminal is already formally named/linked to this case's FIRs."""
    return bool(
        db.query(FIRCriminalLink.id)
        .join(FIR, FIRCriminalLink.fir_id == FIR.id)
        .filter(FIR.crime_case_id == case_id, FIRCriminalLink.criminal_id == criminal_id)
        .first()
    )


_match_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_match_cache_lock = threading.Lock()
# MO matching is expensive (full-table profile extraction, ~40s+ on real data).
# A 30s TTL forced a full recompute every half-minute; 5 minutes keeps repeat
# lookups fast while still self-healing against slow data changes.
_MATCH_CACHE_TTL = timedelta(seconds=300)


def _cached_match(key: str) -> dict[str, Any] | None:
    """Return a fresh-enough cached MO match, or None if missing/expired."""
    with _match_cache_lock:
        entry = _match_cache.get(key)
        if entry is None:
            return None
        expires_at, payload = entry
        if datetime.now(timezone.utc) > expires_at:
            _match_cache.pop(key, None)
            return None
        return payload


def _store_match(key: str, payload: dict[str, Any]) -> None:
    with _match_cache_lock:
        _match_cache[key] = (datetime.now(timezone.utc) + _MATCH_CACHE_TTL, payload)


def match_case_against_db(
    db: Session,
    case_id: uuid.UUID,
    top_k: int = 5,
    min_similarity: float = 0.30,
) -> dict[str, Any]:
    """Find other real cases and real suspects matching a case's MO pattern."""
    cache_key = f"case:{case_id}:{min_similarity}:{top_k}"
    cached = _cached_match(cache_key)
    if cached is not None:
        return cached

    ensure_synced(db)

    target_case = (
        db.query(CrimeCase)
        .options(
            joinedload(CrimeCase.category),
            joinedload(CrimeCase.location),
            joinedload(CrimeCase.firs).joinedload(FIR.criminal_links),
        )
        .filter(CrimeCase.id == case_id)
        .first()
    )

    if not target_case:
        return {"error": "Case not found"}

    target_profile = extract_case_mo_profile(db, target_case)

    # 1. Compare against other real CrimeCases in the DB
    matching_cases = []
    for other_case in (
        db.query(CrimeCase)
        .options(joinedload(CrimeCase.category), joinedload(CrimeCase.location))
        .filter(CrimeCase.id != case_id)
        .all()
    ):
        other_profile = extract_case_mo_profile(db, other_case)
        eval_res = calculate_mo_similarity(target_profile, other_profile)
        if eval_res.score >= min_similarity:
            matching_cases.append({
                "case_id": str(other_case.id),
                "case_number": other_case.case_number,
                "category": other_case.category.name if other_case.category else None,
                "district": other_case.location.district if other_case.location else None,
                "station": other_case.location.station if other_case.location else None,
                "status": other_case.status,
                "occurred_at": other_case.occurred_at.isoformat() if other_case.occurred_at else None,
                "similarity_score": round(eval_res.score, 4),
                "similarity_percent": int(round(eval_res.score * 100)),
                "match_level": eval_res.match_level,
                "confidence": eval_res.confidence,
                "matching_factors": eval_res.matching_factors,
                "divergent_factors": eval_res.divergent_factors,
                "insufficient_data": eval_res.insufficient_data,
            })

    matching_cases.sort(key=lambda x: -x["similarity_score"])

    # 2. Compare against real Criminals in the DB
    matching_suspects = []
    confirmed_criminal_ids = {
        link.criminal_id
        for fir in (target_case.firs or [])
        for link in (fir.criminal_links or [])
        if link.criminal_id is not None
    }
    for criminal in (
        db.query(Criminal)
        .options(joinedload(Criminal.fir_links).joinedload(FIRCriminalLink.fir))
        .all()
    ):
        crim_profile = extract_criminal_mo_profile(db, criminal)
        eval_res = calculate_mo_similarity(target_profile, crim_profile)

        is_confirmed = criminal.id in confirmed_criminal_ids

        if eval_res.score >= min_similarity or is_confirmed:
            matching_suspects.append({
                "criminal_id": str(criminal.id),
                "full_name": criminal.full_name,
                "aliases": criminal.aliases,
                "status": criminal.status,
                "gang_affiliation": criminal.gang_affiliation,
                "similarity_score": round(eval_res.score, 4),
                "similarity_percent": int(round(eval_res.score * 100)),
                "match_level": eval_res.match_level,
                "confidence": eval_res.confidence,
                "is_confirmed_relationship": is_confirmed,
                "relationship_label": "Confirmed FIR Accused" if is_confirmed else "Analytical MO Lead",
                "matching_factors": eval_res.matching_factors,
                "divergent_factors": eval_res.divergent_factors,
                "insufficient_data": eval_res.insufficient_data,
            })

    matching_suspects.sort(key=lambda x: (-int(x["is_confirmed_relationship"]), -x["similarity_score"]))

    result = {
        "target_case": {
            "case_id": str(target_case.id),
            "case_number": target_case.case_number,
            "category": target_case.category.name if target_case.category else None,
            "district": target_case.location.district if target_case.location else None,
            "profile": target_profile.to_dict(),
        },
        "matching_cases": matching_cases[:top_k],
        "matching_suspects": matching_suspects[:top_k],
        "total_cases_evaluated": db.query(CrimeCase).count(),
        "total_criminals_evaluated": db.query(Criminal).count(),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
    _store_match(cache_key, result)
    return result


def match_criminal_against_db(
    db: Session,
    criminal_id: uuid.UUID,
    top_k: int = 5,
    min_similarity: float = 0.30,
) -> dict[str, Any]:
    """Find real unsolved/open cases and similar offenders matching a criminal's MO."""
    cache_key = f"criminal:{criminal_id}:{min_similarity}:{top_k}"
    cached = _cached_match(cache_key)
    if cached is not None:
        return cached

    ensure_synced(db)

    target_criminal = (
        db.query(Criminal)
        .options(joinedload(Criminal.fir_links).joinedload(FIRCriminalLink.fir).joinedload(FIR.crime_case))
        .filter(Criminal.id == criminal_id)
        .first()
    )

    if not target_criminal:
        return {"error": "Criminal not found"}

    target_profile = extract_criminal_mo_profile(db, target_criminal)

    # Precompute the case ids this criminal is formally linked to (via its
    # FIRs) so we avoid an N+1 DB query per case inside the comparison loop.
    confirmed_case_ids = {
        link.fir.crime_case_id
        for link in (target_criminal.fir_links or [])
        if link.fir is not None and link.fir.crime_case_id is not None
    }

    # 1. Compare against all real CrimeCases in DB
    matching_cases = []
    for case in (
        db.query(CrimeCase)
        .options(joinedload(CrimeCase.category), joinedload(CrimeCase.location))
        .all()
    ):
        case_profile = extract_case_mo_profile(db, case)
        eval_res = calculate_mo_similarity(target_profile, case_profile)

        is_confirmed = case.id in confirmed_case_ids

        if eval_res.score >= min_similarity or is_confirmed:
            matching_cases.append({
                "case_id": str(case.id),
                "case_number": case.case_number,
                "category": case.category.name if case.category else None,
                "district": case.location.district if case.location else None,
                "station": case.location.station if case.location else None,
                "status": case.status,
                "occurred_at": case.occurred_at.isoformat() if case.occurred_at else None,
                "similarity_score": round(eval_res.score, 4),
                "similarity_percent": int(round(eval_res.score * 100)),
                "match_level": eval_res.match_level,
                "confidence": eval_res.confidence,
                "is_confirmed_relationship": is_confirmed,
                "relationship_label": "Formally Charged Case" if is_confirmed else "Potential Unsolved Link",
                "matching_factors": eval_res.matching_factors,
                "divergent_factors": eval_res.divergent_factors,
                "insufficient_data": eval_res.insufficient_data,
            })

    matching_cases.sort(key=lambda x: (-int(x["is_confirmed_relationship"]), -x["similarity_score"]))

    # 2. Compare against other real Criminals in DB
    similar_criminals = []
    for other_criminal in (
        db.query(Criminal)
        .options(joinedload(Criminal.fir_links).joinedload(FIRCriminalLink.fir))
        .filter(Criminal.id != criminal_id)
        .all()
    ):
        other_profile = extract_criminal_mo_profile(db, other_criminal)
        eval_res = calculate_mo_similarity(target_profile, other_profile)

        if eval_res.score >= min_similarity:
            similar_criminals.append({
                "criminal_id": str(other_criminal.id),
                "full_name": other_criminal.full_name,
                "aliases": other_criminal.aliases,
                "status": other_criminal.status,
                "gang_affiliation": other_criminal.gang_affiliation,
                "similarity_score": round(eval_res.score, 4),
                "similarity_percent": int(round(eval_res.score * 100)),
                "match_level": eval_res.match_level,
                "confidence": eval_res.confidence,
                "matching_factors": eval_res.matching_factors,
                "divergent_factors": eval_res.divergent_factors,
                "insufficient_data": eval_res.insufficient_data,
            })

    similar_criminals.sort(key=lambda x: -x["similarity_score"])

    result = {
        "target_criminal": {
            "criminal_id": str(target_criminal.id),
            "full_name": target_criminal.full_name,
            "status": target_criminal.status,
            "profile": target_profile.to_dict(),
        },
        "matching_cases": matching_cases[:top_k],
        "similar_criminals": similar_criminals[:top_k],
        "total_cases_evaluated": db.query(CrimeCase).count(),
        "total_criminals_evaluated": db.query(Criminal).count(),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
    _store_match(cache_key, result)
    return result


def compare_two_entities(
    db: Session,
    entity_a_id: uuid.UUID,
    entity_a_type: str,
    entity_b_id: uuid.UUID,
    entity_b_type: str,
) -> dict[str, Any]:
    """Side-by-side explainable comparison between any two real database entities."""
    ensure_synced(db)

    # Resolve profile A
    if entity_a_type == "case":
        case_a = db.query(CrimeCase).filter(CrimeCase.id == entity_a_id).first()
        if not case_a:
            return {"error": f"Case {entity_a_id} not found"}
        prof_a = extract_case_mo_profile(db, case_a)
    elif entity_a_type == "criminal":
        crim_a = db.query(Criminal).filter(Criminal.id == entity_a_id).first()
        if not crim_a:
            return {"error": f"Criminal {entity_a_id} not found"}
        prof_a = extract_criminal_mo_profile(db, crim_a)
    else:
        return {"error": f"Invalid entity_a_type: {entity_a_type}"}

    # Resolve profile B
    if entity_b_type == "case":
        case_b = db.query(CrimeCase).filter(CrimeCase.id == entity_b_id).first()
        if not case_b:
            return {"error": f"Case {entity_b_id} not found"}
        prof_b = extract_case_mo_profile(db, case_b)
    elif entity_b_type == "criminal":
        crim_b = db.query(Criminal).filter(Criminal.id == entity_b_id).first()
        if not crim_b:
            return {"error": f"Criminal {entity_b_id} not found"}
        prof_b = extract_criminal_mo_profile(db, crim_b)
    else:
        return {"error": f"Invalid entity_b_type: {entity_b_type}"}

    eval_res = calculate_mo_similarity(prof_a, prof_b)

    return {
        "entity_a": prof_a.to_dict(),
        "entity_b": prof_b.to_dict(),
        "similarity_score": round(eval_res.score, 4),
        "similarity_percent": int(round(eval_res.score * 100)),
        "match_level": eval_res.match_level,
        "confidence": eval_res.confidence,
        "matching_factors": eval_res.matching_factors,
        "divergent_factors": eval_res.divergent_factors,
        "insufficient_data": eval_res.insufficient_data,
        "dimension_scores": eval_res.dimension_scores,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
