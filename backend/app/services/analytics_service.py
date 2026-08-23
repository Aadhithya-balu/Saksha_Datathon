"""Database-backed analytics used by the prototype UI.

These functions are intentionally rule-based: they make the app dynamic and
complete without pretending an ML model is already trained.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.location import Location
from app.models.officer import Officer
from app.models.victim import Victim

SEVERITY_WEIGHT = {"low": 0.8, "medium": 1.0, "high": 1.25, None: 1.0}


def recent_activity(db: Session, days: int = 0) -> dict[str, Any]:
    """Time-aware activity summary so the chat can answer 'any records today?'.

    days=0 means since local midnight (i.e. today); otherwise a rolling window.
    """
    from app.models.evidence import Evidence

    now = datetime.now()
    if days <= 0:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = f"today ({start.strftime('%Y-%m-%d')})"
    else:
        start = now - timedelta(days=days)
        period_label = f"{start.strftime('%Y-%m-%d %H:%M')} to {now.strftime('%Y-%m-%d %H:%M')}"

    new_cases = db.query(CrimeCase).filter(CrimeCase.created_at >= start).count()
    new_firs = db.query(FIR).filter(FIR.created_at >= start).count()
    new_evidence = db.query(Evidence).filter(Evidence.created_at >= start).count()
    new_criminals = db.query(Criminal).filter(Criminal.created_at >= start).count()

    latest_case = db.query(CrimeCase).order_by(CrimeCase.created_at.desc()).first()
    latest_fir = db.query(FIR).order_by(FIR.created_at.desc()).first()

    return {
        "period_label": period_label,
        "new_cases": new_cases,
        "new_firs": new_firs,
        "new_evidence": new_evidence,
        "new_criminals": new_criminals,
        "latest_case": (
            f"{latest_case.case_number} registered {latest_case.created_at.strftime('%Y-%m-%d %H:%M')}"
            if latest_case and latest_case.created_at else "none on file"
        ),
        "latest_fir": (
            f"{latest_fir.fir_number} filed {latest_fir.created_at.strftime('%Y-%m-%d %H:%M')}"
            if latest_fir and latest_fir.created_at else "none on file"
        ),
        "now": now.strftime("%Y-%m-%d %H:%M"),
    }

SEASON_MAP = {
    1: "Winter", 2: "Winter", 3: "Summer",
    4: "Summer", 5: "Summer", 6: "Monsoon",
    7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
    10: "Post-Monsoon", 11: "Post-Monsoon", 12: "Winter",
}

SEASON_ORDER = ["Summer", "Monsoon", "Post-Monsoon", "Winter"]


def get_season(month: int) -> str:
    return SEASON_MAP.get(month, "Unknown")


@dataclass(frozen=True)
class DistrictAggregate:
    district: str
    total: int
    open_cases: int
    high_severity: int
    recent_cases: int
    top_category: str
    lat: float
    lng: float


def dashboard_summary(db: Session, date_from: datetime | None = None, date_to: datetime | None = None) -> dict[str, Any]:
    query = db.query(CrimeCase)
    if date_from:
        query = query.filter(CrimeCase.occurred_at >= date_from)
    if date_to:
        query = query.filter(CrimeCase.occurred_at <= date_to)

    total_crimes = query.count()
    open_crimes = query.filter(CrimeCase.status == "open").count()
    resolved = query.filter(CrimeCase.status == "closed").count()

    return {
        "total_crimes": total_crimes,
        "open_crimes": open_crimes,
        "total_firs": db.query(FIR).count(),
        "total_criminals": db.query(Criminal).count(),
        "resolution_rate_percent": round((resolved / total_crimes) * 100, 2) if total_crimes else 0.0,
    }


def crime_trends(db: Session) -> list[dict[str, Any]]:
    rows = db.query(CrimeCase.occurred_at).order_by(CrimeCase.occurred_at).all()
    buckets: Counter[str] = Counter()
    for (occurred_at,) in rows:
        if occurred_at:
            buckets[occurred_at.date().replace(day=1).isoformat()] += 1
    return [{"date": date, "count": count} for date, count in sorted(buckets.items())]


def category_breakdown(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(CrimeCategory.name, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.category_id == CrimeCategory.id)
        .group_by(CrimeCategory.name)
        .order_by(func.count(CrimeCase.id).desc())
        .all()
    )
    return [{"category": name, "count": count} for name, count in rows]


def district_comparison(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(Location.district, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .group_by(Location.district)
        .order_by(func.count(CrimeCase.id).desc())
        .all()
    )
    return [{"district": district, "count": count} for district, count in rows]


def _district_aggregates(db: Session) -> list[DistrictAggregate]:
    cases = (
        db.query(CrimeCase)
        .options(joinedload(CrimeCase.location), joinedload(CrimeCase.category))
        .all()
    )
    if not cases:
        return []

    grouped: dict[str, list[CrimeCase]] = defaultdict(list)
    for case in cases:
        if case.location:
            grouped[case.location.district].append(case)

    aggregates: list[DistrictAggregate] = []
    for district, district_cases in grouped.items():
        category_counts = Counter(case.category.name for case in district_cases if case.category)
        lat = sum(case.location.latitude for case in district_cases) / len(district_cases)
        lng = sum(case.location.longitude for case in district_cases) / len(district_cases)
        aggregates.append(
            DistrictAggregate(
                district=district,
                total=len(district_cases),
                open_cases=sum(1 for case in district_cases if case.status == "open"),
                high_severity=sum(1 for case in district_cases if case.category and case.category.severity == "high"),
                recent_cases=sum(1 for case in district_cases if _within_days(case.occurred_at, 30)),
                top_category=category_counts.most_common(1)[0][0] if category_counts else "Unclassified",
                lat=lat,
                lng=lng,
            )
        )
    return sorted(aggregates, key=lambda item: item.total, reverse=True)


def risk_scores(db: Session, district_id: str | None = None, window: str = "next_7d") -> dict[str, Any]:
    aggregates = _district_aggregates(db)
    if district_id:
        aggregates = [item for item in aggregates if item.district == district_id]

    max_total = max((item.total for item in aggregates), default=1)
    max_recent = max((item.recent_cases for item in aggregates), default=1)
    predictions = []
    for item in aggregates:
        open_ratio = item.open_cases / item.total if item.total else 0
        severity_ratio = item.high_severity / item.total if item.total else 0
        volume_component = (item.total / max_total) * 40
        recency_component = (item.recent_cases / max_recent) * 25
        score = min(100, round(20 + volume_component + recency_component + open_ratio * 10 + severity_ratio * 5))
        predictions.append(
            {
                "district": item.district,
                "risk_score": score,
                "confidence": round(min(0.95, 0.58 + (item.total / max_total) * 0.32), 2),
            }
        )

    return {
        "district_id": district_id,
        "window": window,
        "grid_predictions": sorted(predictions, key=lambda row: row["risk_score"], reverse=True),
        "model_version": "rule-based-sql-v2",
    }


def hotspots(db: Session, district_id: str | None = None) -> dict[str, Any]:
    query = db.query(Location).join(CrimeCase, CrimeCase.location_id == Location.id)
    if district_id:
        query = query.filter(Location.district == district_id)
    locations = query.options(joinedload(Location.crimes).joinedload(CrimeCase.category)).all()

    max_count = max((len(location.crimes) for location in locations), default=1)
    rows = []
    for location in locations:
        crimes = location.crimes
        if not crimes:
            continue
        categories = Counter(case.category.name for case in crimes if case.category)
        recent = sum(1 for case in crimes if _within_days(case.occurred_at, 30))
        previous = max(len(crimes) - recent, 0)
        trend = "up" if recent > previous else "down" if recent < previous else "stable"
        score = min(100, round(35 + (len(crimes) / max_count) * 55 + recent * 2))
        rows.append(
            {
                "district_id": location.district,
                "name": location.station or location.address or location.district,
                "lat": location.latitude,
                "lng": location.longitude,
                "score": score,
                "category": categories.most_common(1)[0][0] if categories else "Unclassified",
                "trend": trend,
            }
        )
    return {"hotspots": sorted(rows, key=lambda row: row["score"], reverse=True)}


def anomalies(db: Session) -> dict[str, Any]:
    firs = (
        db.query(FIR)
        .options(joinedload(FIR.crime_case).joinedload(CrimeCase.category), joinedload(FIR.crime_case).joinedload(CrimeCase.location))
        .order_by(FIR.filed_at.desc())
        .limit(30)
        .all()
    )
    rows = []
    for fir in firs:
        case = fir.crime_case
        if not case:
            continue
        severity = case.category.severity if case.category else "medium"
        score = 0.45
        reasons = []
        if severity == "high":
            score += 0.22
            reasons.append("high severity category")
        if case.status == "open":
            score += 0.12
            reasons.append("open investigation")
        if case.mo_tags:
            score += min(0.16, len([tag for tag in case.mo_tags.split(",") if tag.strip()]) * 0.04)
            reasons.append("modus-operandi tags present")
        if fir.criminal_links and len(fir.criminal_links) > 1:
            score += 0.08
            reasons.append("multiple linked suspects")

        if score >= 0.62:
            label = f"{case.category.name if case.category else 'Incident'} anomaly"
            rows.append(
                {
                    "case_id": fir.fir_number,
                    "label": label,
                    "score": round(min(score, 0.98), 2),
                    "reason": ", ".join(reasons) if reasons else "case diverges from current baseline",
                }
            )
    return {"anomalies": sorted(rows, key=lambda row: row["score"], reverse=True)}


def offender_dossiers(db: Session) -> list[dict[str, Any]]:
    criminals = db.query(Criminal).options(joinedload(Criminal.fir_links).joinedload(FIRCriminalLink.fir)).all()
    rows = []
    for criminal in criminals:
        firs = [link.fir for link in criminal.fir_links if link.fir]
        districts = sorted({fir.crime_case.location.district for fir in firs if fir.crime_case and fir.crime_case.location})
        categories = [fir.crime_case.category.name for fir in firs if fir.crime_case and fir.crime_case.category]
        linked_count = len(firs)
        risk = min(100, 35 + linked_count * 12 + (10 if criminal.status == "at_large" else 0))
        classification = "A-CATEGORY" if risk >= 80 else "B-CATEGORY" if risk >= 60 else "WATCHLIST"
        status = "ACTIVE" if criminal.status == "at_large" else "INCARCERATED" if criminal.status in {"arrested", "convicted"} else "UNDER_SURVEILLANCE"
        rows.append(
            {
                "id": str(criminal.id),
                "name": criminal.full_name,
                "alias": criminal.aliases or criminal.full_name,
                "age": _age_from_dob(criminal.date_of_birth),
                "gender": criminal.gender or "Unknown",
                "classification": classification,
                "activeDistricts": districts,
                "status": status,
                "riskScore": risk,
                "gangAffiliation": Counter(categories).most_common(1)[0][0] if categories else "Unclassified",
                "mugshotDesc": criminal.identifying_marks or criminal.mo_summary or "No biometric descriptor recorded",
            }
        )
    return sorted(rows, key=lambda row: row["riskScore"], reverse=True)


def network_person(db: Session, person_id: str, depth: int = 1) -> dict[str, Any]:
    del depth
    firs = (
        db.query(FIR)
        .options(
            joinedload(FIR.crime_case).joinedload(CrimeCase.location),
            joinedload(FIR.criminal_links).joinedload(FIRCriminalLink.criminal),
            joinedload(FIR.victim_links).joinedload(FIRVictimLink.victim),
        )
        .order_by(FIR.filed_at.desc())
        .limit(25)
        .all()
    )

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []

    def add_node(node_id: str, **payload):
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, **payload}

    for fir in firs:
        case = fir.crime_case
        location_id = f"location-{case.location_id}" if case else None
        if case and case.location:
            add_node(
                location_id,
                name=case.location.station or case.location.district,
                category="location",
                riskScore=65,
                details=f"{case.location.district} jurisdiction linked to {fir.fir_number}",
                casesCount=len(case.location.crimes),
            )

        for link in fir.criminal_links:
            criminal = link.criminal
            node_id = f"criminal-{criminal.id}"
            add_node(
                node_id,
                name=criminal.full_name,
                category="suspect" if criminal.status == "at_large" else "offender",
                riskScore=min(100, 45 + len(criminal.fir_links) * 12),
                details=criminal.mo_summary or criminal.identifying_marks or "Linked through FIR records",
                casesCount=len(criminal.fir_links),
            )
            if location_id:
                edges.append({"source": node_id, "target": location_id, "relationship": "Linked crime location"})

            for victim_link in fir.victim_links:
                victim = victim_link.victim
                victim_id = f"victim-{victim.id}"
                add_node(
                    victim_id,
                    name=victim.full_name,
                    category="victim",
                    riskScore=10,
                    details=victim.statement or "Victim/complainant in FIR record",
                    casesCount=len(victim.fir_links),
                )
                edges.append({"source": node_id, "target": victim_id, "relationship": "Named in same FIR"})

    return {"nodes": list(nodes.values()), "edges": edges}


def chat_answer(db: Session, message: str) -> dict[str, Any]:
    summary = dashboard_summary(db)
    districts = district_comparison(db)[:5]
    categories = category_breakdown(db)[:5]
    answer = (
        f"Current backend records show {summary['total_crimes']} crime cases, "
        f"{summary['open_crimes']} open cases, {summary['total_firs']} FIRs, and "
        f"{summary['resolution_rate_percent']}% resolution."
    )
    return {
        "answer": answer,
        "data": [{"query": message, "summary": summary, "top_districts": districts, "top_categories": categories}],
        "sources": ["crime_cases", "firs", "criminals", "locations", "crime_categories"],
        "chart_suggestion": "bar" if districts else None,
    }


def season_breakdown(db: Session) -> dict[str, Any]:
    rows = db.query(CrimeCase.occurred_at).all()
    season_counts: Counter[str] = Counter()
    season_by_district: dict[str, Counter[str]] = defaultdict(Counter)
    total = 0

    for (occurred_at,) in rows:
        if not occurred_at:
            continue
        season = get_season(occurred_at.month)
        season_counts[season] += 1
        total += 1

    cases_with_location = (
        db.query(CrimeCase.occurred_at, Location.district)
        .join(Location, CrimeCase.location_id == Location.id)
        .all()
    )
    for occurred_at, district in cases_with_location:
        if occurred_at and district:
            season_by_district[get_season(occurred_at.month)][district] += 1

    result = []
    for season in SEASON_ORDER:
        count = season_counts.get(season, 0)
        pct = round((count / total) * 100, 1) if total else 0.0
        top_district = ""
        if season_by_district[season]:
            top_district = season_by_district[season].most_common(1)[0][0]
        result.append({
            "season": season,
            "count": count,
            "percentage": pct,
            "top_district": top_district,
        })

    return {
        "seasons": result,
        "total_cases": total,
        "karnataka_climate_note": "Karnataka seasons: Summer (Mar-May), Monsoon (Jun-Sep), Post-Monsoon (Oct-Nov), Winter (Dec-Feb)",
    }


def _age_from_dob(date_of_birth):
    if not date_of_birth:
        return 0
    today = datetime.now().date()
    return today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))



def _within_days(value, days: int) -> bool:
    if not value:
        return False
    now = datetime.now(value.tzinfo) if value.tzinfo else datetime.now()
    return value >= now - timedelta(days=days)
