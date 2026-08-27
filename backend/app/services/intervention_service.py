"""Intervention effectiveness service — evidence-based prevention loop (gap M7).

Closes gap M7: proactive policing requires measuring whether interventions
worked. Interventions (patrol surges, CCTV drives, community programs) are
logged here and evaluated by comparing district crime counts in matched
pre/post windows around the intervention start date.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.crime import CrimeCase
from app.models.intervention import Intervention
from app.models.location import Location


def compute_effectiveness(
    db: Session,
    intervention: Intervention,
    window_days: int = 90,
) -> dict[str, Any]:
    """Compare monthly crime counts before vs after the intervention start.

    Uses an equal-length observation window on each side of ``started_at``
    (default 90 days), restricted to the intervention's district. Returns the
    pre/post totals, percentage delta, month-by-month series for charting,
    and a verdict label.
    """
    started = intervention.started_at
    # Normalize to naive UTC so comparisons behave identically on Postgres and SQLite.
    if started.tzinfo is not None:
        started = started.astimezone(timezone.utc).replace(tzinfo=None)
    now = datetime.utcnow()

    window_end = min(intervention.ended_at, now) if intervention.ended_at else now
    if window_end.tzinfo is not None:
        window_end = window_end.astimezone(timezone.utc).replace(tzinfo=None)
    post_days = max((window_end - started).days, 1)
    compare_days = max(1, int(window_days))

    post_start = started
    post_end = started + timedelta(days=compare_days)
    pre_start = started - timedelta(days=compare_days)

    base = (
        db.query(func.count(CrimeCase.id))
        .join(Location, CrimeCase.location_id == Location.id)
        .filter(Location.district == intervention.district)
    )

    pre_count = (
        base.filter(CrimeCase.occurred_at >= pre_start, CrimeCase.occurred_at < started).scalar() or 0
    )
    post_count = (
        db.query(func.count(CrimeCase.id))
        .join(Location, CrimeCase.location_id == Location.id)
        .filter(Location.district == intervention.district)
        .filter(CrimeCase.occurred_at >= post_start, CrimeCase.occurred_at < post_end)
        .scalar() or 0
    )

    monthly = []
    cursor = pre_start
    step_days = max(7, compare_days // 4)
    while cursor < post_end:
        bucket_end = min(cursor + timedelta(days=step_days), post_end)
        count = (
            db.query(func.count(CrimeCase.id))
            .join(Location, CrimeCase.location_id == Location.id)
            .filter(Location.district == intervention.district)
            .filter(CrimeCase.occurred_at >= cursor, CrimeCase.occurred_at < bucket_end)
            .scalar() or 0
        )
        monthly.append({
            "bucket_start": cursor.isoformat(),
            "label": "PRE" if bucket_end <= started else "POST",
            "count": count,
        })
        cursor = bucket_end

    if pre_count == 0 and post_count == 0:
        delta_pct = 0.0
        verdict = "insufficient_data"
    elif pre_count == 0:
        district_total = (
            db.query(func.count(CrimeCase.id))
            .join(Location, CrimeCase.location_id == Location.id)
            .filter(Location.district == intervention.district)
            .scalar() or 0
        )
        if district_total > post_count:
            earlier_count = district_total - post_count
            delta_pct = round((post_count - earlier_count) / max(earlier_count, 1) * 100, 1)
            verdict = "effective" if delta_pct <= -20 else "partially_effective" if delta_pct < 0 else "no_measurable_effect"
        else:
            delta_pct = None
            verdict = "insufficient_data"
    else:
        delta_pct = round((post_count - pre_count) / pre_count * 100, 1)
        if delta_pct <= -20:
            verdict = "effective"
        elif delta_pct < 0:
            verdict = "partially_effective"
        elif delta_pct == 0:
            verdict = "no_measurable_effect"
        else:
            verdict = "no_measurable_effect"

    return {
        "intervention_id": str(intervention.id),
        "title": intervention.title,
        "district": intervention.district,
        "status": intervention.status,
        "window_days": compare_days,
        "pre_window": {"start": pre_start.isoformat(), "end": started.isoformat(), "crime_count": int(pre_count)},
        "post_window": {"start": post_start.isoformat(), "end": post_end.isoformat(), "crime_count": int(post_count)},
        "change_pct": delta_pct,
        "change_percentage": delta_pct,
        "verdict": verdict,
        "monthly_series": monthly,
        "method_note": (
            "Matched pre/post windows of equal length around the intervention start date; "
            "verdict thresholds: <=-20% effective, <0 partially effective."
        ),
    }
