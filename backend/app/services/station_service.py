"""Station-level drill-down analytics (issue #146, gap 128.1).

Replaces the frontend's hardcoded station registry with live per-station
aggregates straight from PostgreSQL so drill-downs reflect real records.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.crime import CrimeCase
from app.models.location import Location


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _trend(recent: int, prior: int) -> str:
    if recent > prior:
        return "up"
    if recent < prior:
        return "down"
    return "stable"


def station_summaries(
    db: Session,
    district: str | None = None,
    q: str | None = None,
) -> list[dict[str, Any]]:
    """Per-station aggregates powering the map drill-down layer."""
    now = datetime.now(timezone.utc)
    cutoff_recent = now - timedelta(days=30)
    cutoff_prior = now - timedelta(days=60)

    query = (
        db.query(Location)
        .join(CrimeCase, CrimeCase.location_id == Location.id)
        .options(joinedload(Location.crimes).joinedload(CrimeCase.category))
    )
    if district:
        query = query.filter(Location.district.ilike(f"%{district}%"))
    if q:
        like = f"%{q}%"
        query = query.filter((Location.station.ilike(like)) | (Location.address.ilike(like)))
    locations = query.all()

    volume_by_station: list[tuple[dict[str, Any], int]] = []
    rows: list[dict[str, Any]] = []

    for location in locations:
        crimes = [c for c in location.crimes]
        if not crimes:
            continue
        recent = sum(1 for c in crimes if (ts := _aware(c.occurred_at)) and ts >= cutoff_recent)
        prior = sum(
            1
            for c in crimes
            if (ts := _aware(c.occurred_at)) and cutoff_prior <= ts < cutoff_recent
        )
        open_cases = sum(1 for c in crimes if (c.status or "").lower() == "open")
        categories = Counter(c.category.name for c in crimes if c.category)
        top_category, top_count = ("Unclassified", len(crimes))
        if categories:
            top_category, top_count = categories.most_common(1)[0]
        last_incident = max((_aware(c.occurred_at) for c in crimes), default=None)

        row = {
            "district": location.district,
            "station": location.station or location.address or location.district,
            "lat": location.latitude,
            "lng": location.longitude,
            "total_cases": len(crimes),
            "recent_30d": recent,
            "prior_30d": prior,
            "open_cases": open_cases,
            "top_category": top_category,
            "top_category_count": top_count,
            "trend": _trend(recent, prior),
            "last_incident_at": last_incident.isoformat() if last_incident else None,
        }
        volume_by_station.append((row, len(crimes)))
        rows.append(row)

    if not rows:
        return []

    max_volume = float(max(v for _, v in volume_by_station))

    for row, volume in volume_by_station:
        recency_component = min(100.0, row["recent_30d"] * 12.5)
        volume_component = volume / max_volume * 100.0
        open_ratio = row["open_cases"] / max(volume, 1)
        momentum = 50.0 + (row["recent_30d"] - row["prior_30d"]) * 10.0
        risk = (
            0.40 * recency_component
            + 0.25 * volume_component
            + 0.15 * min(open_ratio * 100.0, 100.0)
            + 0.20 * max(0.0, min(momentum, 100.0))
        )
        row["risk_score"] = int(round(max(0.0, min(risk, 100.0))))

    rows.sort(key=lambda r: (r["risk_score"], r["total_cases"]), reverse=True)
    return rows
