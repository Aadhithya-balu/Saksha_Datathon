"""Red-zone spike detection + alert notifications (issue #146, gaps 128.3/130.4).

A red zone is a (district, crime category) pair whose last-30-day volume
spikes against its own trailing 90-day baseline. Detected zones are exposed
via the alerts API and can be broadcast to the notification center.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.crime import CrimeCase


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def detect_red_zones(
    db: Session,
    *,
    min_current: int = 3,
    ratio_threshold: float = 1.5,
) -> dict[str, Any]:
    """Compare last-30-day volume per (district, category) vs prior 90 days."""
    now = datetime.now(timezone.utc)
    cutoff_current = now - timedelta(days=30)
    cutoff_baseline = now - timedelta(days=120)

    cases = (
        db.query(CrimeCase)
        .options(joinedload(CrimeCase.category), joinedload(CrimeCase.location))
        .filter(CrimeCase.occurred_at.isnot(None))
        .all()
    )

    current: dict[tuple[str, str], int] = defaultdict(int)
    baseline: dict[tuple[str, str], int] = defaultdict(int)
    stations: dict[tuple[str, str], set[str]] = defaultdict(set)

    for case in cases:
        ts = _aware(case.occurred_at)
        if ts is None or ts < cutoff_baseline:
            continue
        district = case.location.district if case.location else "Unknown"
        category = case.category.name if case.category else "Unclassified"
        key = (district, category)
        if ts >= cutoff_current:
            current[key] += 1
            station_name = case.location.station if case.location else None
            if station_name:
                stations[key].add(station_name)
        else:
            baseline[key] += 1

    zones: list[dict[str, Any]] = []
    for key, count in current.items():
        if count < min_current:
            continue
        prev = baseline.get(key, 0)
        baseline_30d = prev * (30.0 / 90.0)
        denom = max(baseline_30d, 0.5)
        ratio = count / denom
        if prev > 0 and ratio < ratio_threshold:
            continue
        severity = "critical" if (prev == 0 and count >= 5) or ratio >= 2.5 else "high"
        zones.append(
            {
                "district": key[0],
                "category": key[1],
                "current_count": count,
                "baseline_count": round(baseline_30d, 1),
                "spike_ratio": round(ratio, 2),
                "severity": severity,
                "stations": sorted(stations.get(key, set())),
                "window": "last 30d vs prior 90d baseline",
            }
        )

    zones.sort(key=lambda z: (z["spike_ratio"], z["current_count"]), reverse=True)
    return {
        "generated_at": now.isoformat(),
        "thresholds": {"min_current": min_current, "ratio_threshold": ratio_threshold},
        "red_zones": zones,
    }


def notify_red_zones(db: Session, zones: list[dict[str, Any]]) -> dict[str, int]:
    """Broadcast one unread notification per zone; dedupes on resource_id."""
    from app.models.notification import Notification

    existing = {
        row[0]
        for row in db.query(Notification.resource_id)
        .filter(
            Notification.notification_type == "red_zone_spike",
            Notification.is_read.is_(False),
        )
        .all()
        if row[0]
    }

    created = skipped = 0
    for zone in zones:
        resource_id = f"redzone:{zone['district']}:{zone['category']}"
        if resource_id in existing:
            skipped += 1
            continue
        db.add(
            Notification(
                user_id=None,
                subject="Red-zone spike detected",
                notification_type="red_zone_spike",
                category="crime_alert",
                title=f"Red zone: {zone['category']} spiking in {zone['district']}",
                message=(
                    f"{zone['current_count']} incidents in the last 30 days vs a "
                    f"baseline of {zone['baseline_count']} "
                    f"(x{zone['spike_ratio']}). Stations: "
                    f"{', '.join(zone['stations']) if zone['stations'] else 'district-wide'}."
                ),
                severity=zone["severity"],
                priority="high" if zone["severity"] == "critical" else "medium",
                status="unread",
                resource_type="red_zone",
                resource_id=resource_id,
                related_case_number=None,
                is_broadcast=True,
            )
        )
        existing.add(resource_id)
        created += 1

    if created:
        db.commit()
    return {"created": created, "skipped": skipped}
