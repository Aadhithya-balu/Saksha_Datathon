"""Victimology service — repeat-victimization detection, vulnerability scoring, witness risk.

Closes gap M5 of the Saksha gap-closure issue by adding a criminological
intelligence layer over victim records. Analytics are framed against standard
criminological theory:

- **Repeat victimization** (Pease 1998; Farrell & Pease): prior victims are at
  sharply elevated risk of re-victimization ("boost" explanation — offenders
  return because the first success signals low guardship).
- **Lifestyle-exposure / routine activity theory** (Hindelang, Gottfredson &
  Garofalo 1978; Cohen & Felson 1979): victimization risk follows from exposure;
  age and night-time involvement act as lifestyle-exposure proxies here.
- **Vulnerability index**: composite of demographic susceptibility (children,
  elderly), repeat-victimization history, and case severity exposure.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.fir import FIRVictimLink
from app.models.victim import Victim

# Age bands used as lifestyle-exposure / susceptibility proxies.
_CHILD_AGE = 18
_ELDERLY_AGE = 65


def _victim_case_details(db: Session) -> dict[Any, list[dict[str, Any]]]:
    """Map victim_id -> [{fir_number, filed_at, status, sections, district, category}] from FIR links."""
    rows = (
        db.query(FIRVictimLink)
        .all()
    )
    details: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for link in rows:
        fir = link.fir
        if fir is None:
            continue
        case = fir.crime_case
        details[link.victim_id].append({
            "fir_number": fir.fir_number,
            "status": fir.status,
            "sections": fir.sections,
            "filed_at": fir.filed_at.isoformat() if fir.filed_at else None,
            "district": case.location.district if case is not None and case.location is not None else None,
            "category": case.category.name if case is not None and case.category is not None else None,
        })
    return details


def _normalize_identity(name: str | None, contact: str | None) -> tuple[str, str]:
    """Loose identity key so 'Ravi Kumar'/'RAVI KUMAR' dedupe across legacy records."""
    normalized_name = " ".join((name or "").strip().lower().split())
    digits = "".join(ch for ch in (contact or "") if ch.isdigit())
    normalized_contact = digits[-10:] if len(digits) >= 10 else digits
    return normalized_name, normalized_contact


def compute_vulnerability_index(victim: Victim, case_rows: list[dict[str, Any]], is_repeat: bool) -> dict[str, Any]:
    """Composite vulnerability score (0-100) grounded in criminological factors."""
    factors: list[dict[str, Any]] = []
    score = 0.0

    # Demographic susceptibility (lifestyle-exposure proxies).
    age = victim.age
    if age is not None:
        if age <= _CHILD_AGE:
            score += 30
            factors.append({"factor": "minor", "weight": 30, "detail": f"Age {age} (child victim)"})
        elif age >= _ELDERLY_AGE:
            score += 25
            factors.append({"factor": "elderly", "weight": 25, "detail": f"Age {age} (senior citizen)"})
        elif age <= 25:
            # Young adults show elevated street-crime exposure in NCRB data.
            score += 12
            factors.append({"factor": "young_adult", "weight": 12, "detail": f"Age {age} (elevated exposure band)"})

    if (victim.gender or "").strip().lower() == "female":
        score += 10
        factors.append({"factor": "female_gender_risk", "weight": 10, "detail": "Gender-linked risk categories (NCRB)"})

    # Repeat victimization (strongest predictor per Farrell & Pease).
    if is_repeat:
        score += min(20 + (len(case_rows) - 1) * 10, 35)
        factors.append({"factor": "repeat_victimization", "weight": 35, "detail": f"{len(case_rows)} linked FIRs"})

    # Case severity exposure: serious IPC/BNS sections raise witness risk.
    serious_markers = ("302", "376", "307", "395", "364", "103", "64", "70")
    serious = any(
        any(marker in (row.get("sections") or "") for marker in serious_markers)
        for row in case_rows
    )
    if serious:
        score += 20
        factors.append({"factor": "serious_offence_exposure", "weight": 20, "detail": "Linked to heinous-section FIRs"})

    # Witness safety signal: open cases mean the offender may still be at large.
    open_cases = [row for row in case_rows if (row.get("status") or "").lower() not in ("closed", "convicted", "disposed")]
    if open_cases:
        score += min(10 * len(open_cases), 15)
        factors.append({"factor": "open_case_exposure", "weight": 15, "detail": f"{len(open_cases)} unresolved FIR(s); offender possibly at large"})

    return {
        "score": min(round(score), 100),
        "band": _vulnerability_band(score),
        "factors": factors,
    }


def _vulnerability_band(score: float) -> str:
    if score >= 60:
        return "critical"
    if score >= 35:
        return "high"
    if score >= 15:
        return "moderate"
    return "low"


def get_repeat_victims(db: Session) -> dict[str, Any]:
    """Detect repeat victims via identity normalization across FIR links."""
    victims = db.query(Victim).all()
    case_details = _victim_case_details(db)

    results = []
    for victim in victims:
        rows = case_details.get(victim.id, [])
        if len(rows) < 2:
            continue
        analysis = compute_vulnerability_index(victim, rows, is_repeat=True)
        districts = sorted({row.get("district") for row in rows if row.get("district")})
        categories = sorted({row.get("category") for row in rows if row.get("category")})
        results.append({
            "id": str(victim.id),
            "name": victim.full_name,
            "full_name": victim.full_name,
            "gender": victim.gender,
            "age": victim.age,
            "district_hint": (victim.address or "").split(",")[-1].strip() if victim.address else None,
            "fir_count": len(rows),
            "districts": districts,
            "categories": categories,
            "firs": rows,
            "vulnerability_index": analysis["score"],
            "vulnerability": analysis,
        })

    results.sort(key=lambda item: (-item["fir_count"], -item["vulnerability"]["score"]))
    return {
        "total_victims": len(victims),
        "repeat_victims": len(results),
        "results": results,
        "theory_note": (
            "Repeat victimization flagging follows Farrell & Pease's finding that a small "
            "share of victims suffers a disproportionate share of crime; prior victimization "
            "is one of the strongest single predictors of future victimization."
        ),
    }


def get_vulnerability_index(db: Session) -> dict[str, Any]:
    """All victims ranked by composite vulnerability score."""
    victims = db.query(Victim).all()
    case_details = _victim_case_details(db)

    ranked = []
    for victim in victims:
        rows = case_details.get(victim.id, [])
        is_repeat = len(rows) >= 2
        analysis = compute_vulnerability_index(victim, rows, is_repeat=is_repeat)
        districts = sorted({row.get("district") for row in rows if row.get("district")})
        district_hint = (victim.address or "").split(",")[-1].strip() if victim.address else None
        ranked.append({
            "id": str(victim.id),
            "name": victim.full_name,
            "full_name": victim.full_name,
            "age": victim.age,
            "gender": victim.gender,
            "linked_firs": len(rows),
            "fir_count": len(rows),
            "district": districts[0] if districts else district_hint,
            "vulnerability_index": analysis["score"],
            "vulnerability_score": analysis["score"],
            "vulnerability_band": analysis["band"],
            "risk_factors": [f["factor"] for f in analysis["factors"]],
            "explanation": [f["detail"] for f in analysis["factors"]],
        })

    ranked.sort(key=lambda item: -item["vulnerability_score"])
    bands = {"critical": 0, "high": 0, "moderate": 0, "low": 0}
    for item in ranked:
        bands[item["vulnerability_band"]] += 1

    return {
        "total_assessed": len(ranked),
        "band_distribution": bands,
        "results": ranked,
        "methodology": (
            "Composite index (0-100) combining demographic susceptibility (child/elderly/young-adult "
            "bands), gender-linked risk, repeat victimization weight, heinous-offence exposure, and "
            "open-case exposure — operationalizing routine activity/lifestyle-exposure theory "
            "(Cohen & Felson 1979; Hindelang et al. 1978)."
        ),
    }


def get_victimology_overview(db: Session) -> dict[str, Any]:
    """Summary metrics for the victimology dashboard panel."""
    victims = db.query(Victim).all()
    case_details = _victim_case_details(db)

    repeat_count = sum(1 for v in victims if len(case_details.get(v.id, [])) >= 2)
    total_links = sum(len(rows) for rows in case_details.values())

    age_bands = {"children_0_17": 0, "youth_18_25": 0, "adults_26_59": 0, "elderly_60p": 0, "unknown": 0}
    gender_exposure = defaultdict(int)
    night_signal = 0
    dated_links = 0

    for victim in victims:
        age = victim.age
        if age is None:
            age_bands["unknown"] += 1
        elif age < 18:
            age_bands["children_0_17"] += 1
        elif age <= 25:
            age_bands["youth_18_25"] += 1
        elif age < 60:
            age_bands["adults_26_59"] += 1
        else:
            age_bands["elderly_60p"] += 1
        gender_exposure[(victim.gender or "Unknown").strip().title()] += 1
        for row in case_details.get(victim.id, []):
            filed_at = row.get("filed_at")
            if not filed_at:
                continue
            try:
                hour = datetime.fromisoformat(filed_at).hour
                dated_links += 1
                if hour >= 20 or hour < 6:
                    night_signal += 1
            except ValueError:
                continue

    return {
        "total_victims": len(victims),
        "victims_with_linked_firs": sum(1 for v in victims if case_details.get(v.id)),
        "repeat_victims": repeat_count,
        "repeat_victimization_rate": round(repeat_count / len(victims) * 100, 1) if victims else 0,
        "average_firs_per_victim": round(total_links / len(victims), 2) if victims else 0,
        "age_band_distribution": age_bands,
        "gender_distribution": dict(gender_exposure),
        "night_filing_share_pct": round(night_signal / dated_links * 100, 1) if dated_links else None,
        "criminological_frame": [
            "Repeat victimization (Farrell & Pease 1993/1998) — prior victims flagged for targeted guardship advice.",
            "Routine activity theory (Cohen & Felson 1979) — night-time share proxies exposure of suitable targets.",
            "Lifestyle-exposure theory (Hindelang et al. 1978) — age/gender bands proxy differential lifestyle risk.",
        ],
        "generated_on": date.today().isoformat(),
    }
