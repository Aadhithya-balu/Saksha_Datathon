"""Strategic Intelligence service — high-level intelligence briefing for command staff.

Aggregates crime analytics, AI predictions, risk scores, emerging trends,
and deployment recommendations into a unified strategic intelligence view.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink
from app.models.location import Location
from app.models.officer import Officer
from app.models.victim import Victim
from app.models.evidence import Evidence
from app.models.notification import Notification


def get_strategic_briefing(db: Session) -> dict[str, Any]:
    """Generate a comprehensive strategic intelligence briefing."""
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    total_crimes = db.query(CrimeCase).count()
    recent_crimes = db.query(CrimeCase).filter(CrimeCase.occurred_at >= thirty_days_ago).count()
    weekly_crimes = db.query(CrimeCase).filter(CrimeCase.occurred_at >= seven_days_ago).count()
    open_cases = db.query(CrimeCase).filter(CrimeCase.status == "open").count()
    high_priority = db.query(CrimeCase).filter(CrimeCase.priority == "high").count()
    total_firs = db.query(FIR).count()
    total_criminals = db.query(Criminal).count()
    at_large = db.query(Criminal).filter(Criminal.status == "at_large").count()
    total_victims = db.query(Victim).count()
    total_officers = db.query(Officer).count()
    total_evidence = db.query(Evidence).count()

    resolution_rate = 0
    if total_crimes > 0:
        closed = db.query(CrimeCase).filter(CrimeCase.status == "closed").count()
        resolution_rate = round((closed / total_crimes) * 100, 1)

    categories = (
        db.query(CrimeCategory.name, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.category_id == CrimeCategory.id)
        .group_by(CrimeCategory.name)
        .order_by(func.count(CrimeCase.id).desc())
        .all()
    )

    districts = (
        db.query(Location.district, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .group_by(Location.district)
        .order_by(func.count(CrimeCase.id).desc())
        .all()
    )

    monthly_trend = []
    cases = db.query(CrimeCase.occurred_at).filter(CrimeCase.occurred_at.isnot(None)).order_by(CrimeCase.occurred_at).all()
    month_buckets: Counter[str] = Counter()
    for (occurred_at,) in cases:
        if occurred_at:
            month_buckets[occurred_at.strftime("%Y-%m")] += 1
    for month_key in sorted(month_buckets.keys()):
        monthly_trend.append({"month": month_key, "count": month_buckets[month_key]})

    top_criminals = (
        db.query(Criminal)
        .join(FIRCriminalLink, FIRCriminalLink.criminal_id == Criminal.id)
        .group_by(Criminal.id)
        .order_by(func.count(FIRCriminalLink.id).desc())
        .limit(5)
        .all()
    )

    recent_firs = db.query(FIR).order_by(FIR.filed_at.desc()).limit(5).all()

    pending_evidence = db.query(Evidence).filter(Evidence.status.in_(["pending", "assigned"])).count()

    unread_notifs = db.query(Notification).filter(Notification.is_read == False).count()

    crime_change = 0
    if recent_crimes > 0 and total_crimes > recent_crimes:
        prev_period = total_crimes - recent_crimes
        crime_change = round(((recent_crimes - prev_period) / max(prev_period, 1)) * 100, 1)

    districts_at_risk = []
    for district, count in districts:
        ref = _get_district_risk_factors(db, district)
        districts_at_risk.append({
            "district": district,
            "crime_count": count,
            "risk_level": ref["risk_level"],
            "trend": ref["trend"],
            "factors": ref["factors"],
        })
    districts_at_risk.sort(key=lambda x: x["crime_count"], reverse=True)

    top_categories = [{"category": name, "count": count} for name, count in categories[:5]]

    emerging_trends = _detect_emerging_trends(db)

    deployment_suggestions = _generate_deployment_suggestions(districts_at_risk, top_categories, emerging_trends)

    return {
        "generated_at": now.isoformat(),
        "summary": {
            "total_crimes": total_crimes,
            "recent_crimes_30d": recent_crimes,
            "weekly_crimes": weekly_crimes,
            "open_cases": open_cases,
            "high_priority_cases": high_priority,
            "resolution_rate": resolution_rate,
            "crime_trend_change": crime_change,
            "total_firs": total_firs,
            "total_criminals": total_criminals,
            "at_large_criminals": at_large,
            "total_victims": total_victims,
            "total_officers": total_officers,
            "total_evidence": total_evidence,
            "pending_evidence": pending_evidence,
            "unread_notifications": unread_notifs,
        },
        "top_categories": top_categories,
        "districts_at_risk": districts_at_risk,
        "monthly_trend": monthly_trend,
        "emerging_trends": emerging_trends,
        "deployment_suggestions": deployment_suggestions,
        "top_criminals": [
            {
                "id": str(c.id),
                "name": c.full_name,
                "status": c.status,
                "aliases": c.aliases,
                "risk_factors": c.mo_summary[:200] if c.mo_summary else None,
            }
            for c in top_criminals
        ],
        "recent_firs": [
            {
                "id": str(f.id),
                "fir_number": f.fir_number,
                "complainant": f.complainant_name,
                "status": f.status,
                "filed_at": f.filed_at.isoformat() if f.filed_at else None,
            }
            for f in recent_firs
        ],
    }


def get_high_risk_districts(db: Session) -> list[dict[str, Any]]:
    """Return districts ranked by crime density and risk factors."""
    rows = (
        db.query(Location.district, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .group_by(Location.district)
        .order_by(func.count(CrimeCase.id).desc())
        .all()
    )

    result = []
    for district, count in rows:
        ref = _get_district_risk_factors(db, district)
        result.append({
            "district": district,
            "crime_count": count,
            **ref,
        })
    return result


def get_emerging_crime_types(db: Session) -> list[dict[str, Any]]:
    """Detect emerging crime type trends."""
    return _detect_emerging_trends(db)


def get_resource_allocation(db: Session) -> dict[str, Any]:
    """Generate resource allocation recommendations."""
    districts = (
        db.query(Location.district, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .group_by(Location.district)
        .order_by(func.count(CrimeCase.id).desc())
        .all()
    )

    total_crimes = sum(c for _, c in districts) or 1
    allocations = []
    for district, count in districts:
        pct = round(count / total_crimes * 100, 1)
        if pct > 20:
            priority = "CRITICAL"
        elif pct > 12:
            priority = "HIGH"
        elif pct > 6:
            priority = "MEDIUM"
        else:
            priority = "LOW"
        allocations.append({
            "district": district,
            "crime_share_pct": pct,
            "crime_count": count,
            "allocation_priority": priority,
            "suggested_patrol_ratio": round(pct / 10, 1),
        })

    return {
        "allocations": allocations,
        "total_districts": len(allocations),
        "generated_at": datetime.utcnow().isoformat(),
    }


def get_daily_intelligence_summary(db: Session) -> dict[str, Any]:
    """Generate a daily intelligence summary for the command dashboard."""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    yesterday_start = today_start - timedelta(days=1)

    today_crimes = db.query(CrimeCase).filter(CrimeCase.occurred_at >= today_start).count()
    yesterday_crimes = db.query(CrimeCase).filter(
        CrimeCase.occurred_at >= yesterday_start, CrimeCase.occurred_at < today_start
    ).count()

    today_firs = db.query(FIR).filter(FIR.filed_at >= today_start).count()
    open_cases = db.query(CrimeCase).filter(CrimeCase.status == "open").count()
    at_large = db.query(Criminal).filter(Criminal.status == "at_large").count()

    categories_today = (
        db.query(CrimeCategory.name, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.category_id == CrimeCategory.id)
        .filter(CrimeCase.occurred_at >= today_start)
        .group_by(CrimeCategory.name)
        .order_by(func.count(CrimeCase.id).desc())
        .all()
    )

    districts_today = (
        db.query(Location.district, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .filter(CrimeCase.occurred_at >= today_start)
        .group_by(Location.district)
        .order_by(func.count(CrimeCase.id).desc())
        .all()
    )

    trend = "increasing" if today_crimes > yesterday_crimes else "decreasing" if today_crimes < yesterday_crimes else "stable"

    return {
        "date": today.isoformat(),
        "today_crimes": today_crimes,
        "yesterday_crimes": yesterday_crimes,
        "trend": trend,
        "today_firs": today_firs,
        "open_cases": open_cases,
        "at_large_criminals": at_large,
        "categories_today": [{"category": n, "count": c} for n, c in categories_today],
        "districts_today": [{"district": d, "count": c} for d, c in districts_today],
    }


def _get_district_risk_factors(db: Session, district: str) -> dict[str, Any]:
    """Compute risk factors for a specific district."""
    open_count = (
        db.query(CrimeCase)
        .join(Location, CrimeCase.location_id == Location.id)
        .filter(Location.district == district, CrimeCase.status == "open")
        .count()
    )
    high_count = (
        db.query(CrimeCase)
        .join(Location, CrimeCase.location_id == Location.id)
        .filter(Location.district == district, CrimeCase.priority == "high")
        .count()
    )
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent = (
        db.query(CrimeCase)
        .join(Location, CrimeCase.location_id == Location.id)
        .filter(Location.district == district, CrimeCase.occurred_at >= thirty_days_ago)
        .count()
    )

    factors = []
    if open_count > 5:
        factors.append("High open case backlog")
    if high_count > 2:
        factors.append("Multiple high-priority incidents")
    if recent > 8:
        factors.append("Elevated recent activity")

    if open_count > 8 or high_count > 3:
        risk = "CRITICAL"
    elif open_count > 5 or high_count > 2:
        risk = "HIGH"
    elif open_count > 2:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    trend = "increasing" if recent > 5 else "stable"

    return {"risk_level": risk, "trend": trend, "factors": factors, "open_cases": open_count, "high_priority": high_count}


def _detect_emerging_trends(db: Session) -> list[dict[str, Any]]:
    """Detect emerging crime trends by comparing recent vs historical patterns."""
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)

    recent_cats = (
        db.query(CrimeCategory.name, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.category_id == CrimeCategory.id)
        .filter(CrimeCase.occurred_at >= thirty_days_ago)
        .group_by(CrimeCategory.name)
        .all()
    )
    historical_cats = (
        db.query(CrimeCategory.name, func.count(CrimeCase.id))
        .join(CrimeCase, CrimeCase.category_id == CrimeCategory.id)
        .filter(CrimeCase.occurred_at >= sixty_days_ago, CrimeCase.occurred_at < thirty_days_ago)
        .group_by(CrimeCategory.name)
        .all()
    )

    recent_map = {name: count for name, count in recent_cats}
    historical_map = {name: count for name, count in historical_cats}

    trends = []
    for name, recent_count in recent_map.items():
        hist_count = historical_map.get(name, 0)
        if hist_count > 0:
            change_pct = round(((recent_count - hist_count) / hist_count) * 100, 1)
        else:
            change_pct = 100.0 if recent_count > 0 else 0.0

        if change_pct > 20:
            direction = "increasing"
        elif change_pct < -20:
            direction = "decreasing"
        else:
            direction = "stable"

        trends.append({
            "category": name,
            "recent_count": recent_count,
            "historical_count": hist_count,
            "change_percentage": change_pct,
            "direction": direction,
        })

    trends.sort(key=lambda x: abs(x["change_percentage"]), reverse=True)
    return trends


def _generate_deployment_suggestions(
    districts_at_risk: list[dict],
    top_categories: list[dict],
    emerging_trends: list[dict],
) -> list[dict[str, Any]]:
    """Generate actionable deployment suggestions based on intelligence."""
    suggestions = []

    critical_districts = [d for d in districts_at_risk if d["risk_level"] == "CRITICAL"]
    for d in critical_districts[:3]:
        suggestions.append({
            "priority": "CRITICAL",
            "action": f"Deploy additional patrol units to {d['district']}",
            "reason": f"Crime count: {d['crime_count']}, Risk level: CRITICAL",
            "district": d["district"],
            "resource_type": "patrol",
        })

    increasing_trends = [t for t in emerging_trends if t["direction"] == "increasing"]
    for t in increasing_trends[:2]:
        suggestions.append({
            "priority": "HIGH",
            "action": f"Launch {t['category']} crackdown operation",
            "reason": f"{t['category']} increased by {t['change_percentage']}% in last 30 days",
            "district": "State-wide",
            "resource_type": "special_operation",
        })

    if not suggestions:
        suggestions.append({
            "priority": "MEDIUM",
            "action": "Maintain current deployment posture",
            "reason": "No critical alerts detected. Continue routine patrols.",
            "district": "State-wide",
            "resource_type": "routine",
        })

    return suggestions
