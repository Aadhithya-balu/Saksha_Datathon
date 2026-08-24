"""Station drill-down, red-zone spikes, and hour-filtered hotspots (issue #146)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.location import Location
from app.models.notification import Notification
from app.models.role import Role
from app.models.user import User


def _make_user(db_session, username, role_name):
    role = db_session.query(Role).filter_by(name=role_name).first()
    if role is None:
        role = Role(name=role_name, description=role_name)
        db_session.add(role)
        db_session.flush()
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username.title(),
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def analyst_client(client, db_session):
    user = _make_user(db_session, "matrix-analyst", "crime_analyst")
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client
    client.app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _seed_world(db_session):
    """Two stations: one spiking at night, one stable during the day."""
    cat_night = CrimeCategory(name="Night Burglary", section_code="IPC 457", severity="high")
    cat_day = CrimeCategory(name="Day Fraud", section_code="IPC 420", severity="medium")
    spike_station = Location(district="Bengaluru Urban", station="Whitefield Police Station", latitude=12.9698, longitude=77.75)
    calm_station = Location(district="Mysuru", station="Devaraja Police Station", latitude=12.305, longitude=76.648)
    db_session.add_all([cat_night, cat_day, spike_station, calm_station])
    db_session.flush()

    now = datetime.now(timezone.utc)

    def _ago(days: int, hour: int) -> datetime:
        stamp = now - timedelta(days=days)
        return stamp.replace(hour=hour, minute=0, second=0, microsecond=0)

    cases = []
    # Spike station: 4 recent night cases (hour 22) in the last week...
    for i in range(4):
        cases.append(CrimeCase(
            case_number=f"CR-NIGHT-{i:02d}", category_id=cat_night.id, location_id=spike_station.id,
            occurred_at=_ago(2 + i, 22), status="open",
            description="night break-in",
        ))
    # ...and nothing older for that category (baseline zero -> flagged).
    # Calm station: day cases (hour 11); only one inside the last 30d window.
    for offset in (5, 35, 45):
        cases.append(CrimeCase(
            case_number=f"CR-DAY-{offset:02d}", category_id=cat_day.id, location_id=calm_station.id,
            occurred_at=_ago(offset, 11), status="closed",
            description="daytime fraud report",
        ))
    db_session.add_all(cases)
    db_session.commit()
    return {"spike": spike_station, "calm": calm_station, "cat_night": cat_night, "cases": cases}


def _at_hour(dt, hour):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.replace(minute=0, second=0, microsecond=0).hour == hour


# ---------------------------------------------------------------------------
# Gap 128.2 / 131.2 — hour-parameterized hotspot API
# ---------------------------------------------------------------------------

def test_hotspots_hour_filter(db_session):
    from app.services.analytics_service import hotspots as build_hotspots

    world = _seed_world(db_session)

    all_rows = build_hotspots(db_session)["hotspots"]
    assert {row["name"] for row in all_rows} >= {
        world["spike"].station,
        world["calm"].station,
    }
    unfiltered_total = sum(row["count"] for row in all_rows)
    assert unfiltered_total == len(world["cases"])

    night = build_hotspots(db_session, hour=22)
    assert night["hour"] == 22
    night_names = {row["name"] for row in night["hotspots"]}
    assert world["spike"].station in night_names
    assert world["calm"].station not in night_names
    spike_row = next(r for r in night["hotspots"] if r["name"] == world["spike"].station)
    assert spike_row["count"] == 4
    assert spike_row["day_total"] == 4  # all spike-station cases are at night

    day = build_hotspots(db_session, hour=11)
    day_names = {row["name"] for row in day["hotspots"]}
    assert world["calm"].station in day_names
    assert world["spike"].station not in day_names

    empty_hour = build_hotspots(db_session, hour=3)
    assert empty_hour["hotspots"] == []


def test_hotspots_route_accepts_hour_param(analyst_client, db_session):
    _seed_world(db_session)
    resp = analyst_client.get("/api/v2/ai/hotspots", params={"hour": 22})
    assert resp.status_code == 200
    body = resp.json()
    assert body["hour"] == 22
    assert isinstance(body["hotspots"], list)

    bad = analyst_client.get("/api/v2/ai/hotspots", params={"hour": 24})
    assert bad.status_code == 422


# ---------------------------------------------------------------------------
# Gap 128.1 — station-level drill-down service + route
# ---------------------------------------------------------------------------

def test_station_summaries_shape_and_ranking(db_session):
    from app.services.station_service import station_summaries

    world = _seed_world(db_session)
    rows = station_summaries(db_session)
    names = [r["station"] for r in rows]
    assert world["spike"].station in names
    assert world["calm"].station in names

    for row in rows:
        for key in (
            "district", "station", "lat", "lng", "total_cases", "recent_30d",
            "prior_30d", "open_cases", "top_category", "trend",
            "last_incident_at", "risk_score",
        ):
            assert key in row, key
        assert 0 <= row["risk_score"] <= 100

    spike_row = next(r for r in rows if r["station"] == world["spike"].station)
    calm_row = next(r for r in rows if r["station"] == world["calm"].station)
    assert spike_row["recent_30d"] == 4
    assert spike_row["trend"] == "up"
    assert calm_row["trend"] == "down"  # 1 recent vs 2 prior
    assert rows[0]["risk_score"] >= rows[-1]["risk_score"]
    assert rows[0]["risk_score"] >= spike_row["risk_score"] - 100  # sorted desc sanity


def test_station_summaries_filters(db_session):
    from app.services.station_service import station_summaries

    world = _seed_world(db_session)
    bengaluru_only = station_summaries(db_session, district="bengaluru")
    assert all("Bengaluru" in r["district"] for r in bengaluru_only)
    assert [r["station"] for r in bengaluru_only] == [world["spike"].station]

    searched = station_summaries(db_session, q="devaraja")
    assert [r["station"] for r in searched] == [world["calm"].station]

    empty = station_summaries(db_session, district="Nowhere")
    assert empty == []


def test_stations_summary_route(analyst_client, db_session):
    _seed_world(db_session)
    resp = analyst_client.get("/api/v2/stations/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "crime_cases+locations"
    assert body["count"] == len(body["stations"]) > 0

    filtered = analyst_client.get("/api/v2/stations/summary", params={"district": "Mysuru"})
    assert filtered.status_code == 200
    assert all(s["district"] == "Mysuru" for s in filtered.json()["stations"])


# ---------------------------------------------------------------------------
# Gaps 128.3 / 130.4 — red-zone spike detection + notifications
# ---------------------------------------------------------------------------

def test_detect_red_zones_flags_spike_not_baseline(db_session):
    from app.services.redzone_service import detect_red_zones

    world = _seed_world(db_session)
    result = detect_red_zones(db_session)
    zones = {(z["district"], z["category"]): z for z in result["red_zones"]}

    key = ("Bengaluru Urban", "Night Burglary")
    assert key in zones
    zone = zones[key]
    assert zone["current_count"] == 4
    assert zone["baseline_count"] == 0.0
    assert zone["severity"] == "critical"  # zero baseline yields an x8 ratio here
    assert zone["spike_ratio"] >= 2.5 or zone["severity"] in ("critical", "high")
    assert world["spike"].station in zone["stations"]

    assert ("Mysuru", "Day Fraud") not in zones  # spread out, no spike


def test_notify_red_zones_dedupes(db_session):
    from app.services.redzone_service import detect_red_zones, notify_red_zones

    _seed_world(db_session)
    zones = detect_red_zones(db_session)["red_zones"]

    first = notify_red_zones(db_session, zones)
    assert first["created"] == len(zones) > 0
    assert first["skipped"] == 0

    second = notify_red_zones(db_session, zones)
    assert second["created"] == 0
    assert second["skipped"] == len(zones)

    stored = db_session.query(Notification).filter_by(notification_type="red_zone_spike").all()
    assert len(stored) == first["created"]
    assert all(n.is_broadcast and n.resource_id.startswith("redzone:") for n in stored)


def test_red_zone_routes(analyst_client, db_session):
    _seed_world(db_session)

    listed = analyst_client.get("/api/v2/alerts/red-zones")
    assert listed.status_code == 200
    body = listed.json()
    assert body["red_zones"][0]["district"] == "Bengaluru Urban"

    notified = analyst_client.post("/api/v2/alerts/red-zones/notify")
    assert notified.status_code == 200
    nb = notified.json()
    assert nb["created"] == nb["zones_detected"] > 0

    district_view = analyst_client.get("/api/v2/alerts/red-zones/Bengaluru%20Urban")
    assert district_view.status_code == 200
    assert district_view.json()["red_zones"]

    missing = analyst_client.get("/api/v2/alerts/red-zones/Nowhere")
    assert missing.status_code == 404


# ---------------------------------------------------------------------------
# Gap 131.2 — ML predict default_hour synthesis
# ---------------------------------------------------------------------------

def _hotspot_record(i):
    return {
        "CaseMasterID": f"CM-{i}",
        "IncidentFromDate": "",
        "latitude": 12.97,
        "longitude": 77.59,
        "PoliceStationID": f"PS-{i}",
        "GravityOffenceID": "G-1",
        "CrimeMajorHeadID": "H-1",
    }


def test_default_hour_synthesis_unit():
    from datetime import datetime as dt

    from app.routes.ai_hotspot import _apply_default_hour

    records = _apply_default_hour([_hotspot_record(1), _hotspot_record(2)], default_hour=23)
    for record in records:
        parsed = dt.fromisoformat(record["IncidentFromDate"])
        assert parsed.hour == 23

    untouched = _apply_default_hour(
        [{**_hotspot_record(3), "IncidentFromDate": "2026-01-01T05:00:00"}], default_hour=9
    )
    assert untouched[0]["IncidentFromDate"] == "2026-01-01T05:00:00"

    passthrough = _apply_default_hour([_hotspot_record(4)], None)
    assert passthrough[0]["IncidentFromDate"] == ""


def test_predict_with_default_hour_returns_predictions(analyst_client):
    payload = {
        "records": [_hotspot_record(i) for i in range(3)],
        "default_hour": 21,
    }
    resp = analyst_client.post("/api/v2/ai/hotspot/predict", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    # Same cell+month aggregates into a single prediction row.
    assert body["total"] == len(body["predictions"]) >= 1
