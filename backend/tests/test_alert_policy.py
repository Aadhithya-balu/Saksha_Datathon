"""Alert policy tests — Issue #10 P2 acceptance criteria.

14 automated tests covering:
  1.  Normal crime level (no red-zone alert)
  2.  Crime spike (correct alert type and severity)
  3.  Insufficient baseline (INSUFFICIENT_DATA)
  4.  Minimum evidence (alert suppressed below threshold)
  5.  District ranking (documented metric)
  6.  Crime category ranking (documented policy)
  7.  Demo data (provenance = DEMO or UNKNOWN, warning included)
  8.  Mixed data (provenance = MIXED when both live and non-live records)
  9.  Unknown provenance (not classified as LIVE)
  10. Alert evidence (valid supporting record references)
  11. Deduplication (no unlimited duplicate alerts)
  12. Policy version (recorded on every alert)
  13. Priority (severity follows documented rules)
  14. Authorization (unrestricted admin-only endpoint)
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.dependencies import get_current_user
from app.core.alert_policy import (
    ALERT_POLICY_VERSION,
    AlertSeverity,
    AlertType,
    AnomalyThresholds,
    BaselineStatus,
    Confidence,
    DistrictRanking,
    Provenance,
    RedZoneThresholds,
    get_current_policy,
)
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.location import Location
from app.models.notification import Notification
from app.models.role import Role
from app.models.user import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_user(db_session, username, role_name):
    role = db_session.query(Role).filter_by(name=role_name).first()
    if role is None:
        role = Role(name=role_name, description=role_name)
        db_session.add(role)
        db_session.flush()
    user = User(
        username=username,
        email=f"{username}@test.example.com",
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
    user = _make_user(db_session, "alert-analyst", "crime_analyst")
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def admin_client(client, db_session):
    user = _make_user(db_session, "alert-admin", "admin")
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def viewer_client(client, db_session):
    user = _make_user(db_session, "alert-viewer", "viewer")
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client
    client.app.dependency_overrides.pop(get_current_user, None)


def _seed_districts(db_session):
    """Seed two districts, two categories, and time references."""
    cat_high = CrimeCategory(name="Burglary", section_code="IPC 380", severity="high")
    cat_low = CrimeCategory(name="Trespass", section_code="IPC 447", severity="low")
    loc_a = Location(district="Mysuru", station="Devaraja PS", latitude=12.305, longitude=76.648)
    loc_b = Location(district="Bengaluru Urban", station="Whitefield PS", latitude=12.97, longitude=77.75)
    db_session.add_all([cat_high, cat_low, loc_a, loc_b])
    db_session.flush()

    now = datetime.now(timezone.utc)

    def _ago(days, hour=12):
        return (now - timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)

    return {"cat_high": cat_high, "cat_low": cat_low, "loc_a": loc_a, "loc_b": loc_b, "now": now, "_ago": _ago}


# ---------------------------------------------------------------------------
# Test 1 — Normal crime level (no red-zone alert)
# ---------------------------------------------------------------------------

def test_no_alert_when_within_baseline(db_session):
    """Crime activity remains within baseline -> no red-zone alert."""
    world = _seed_districts(db_session)
    cases = []
    # 2 incidents in current window, 6 in baseline -> no spike (2 < MIN_CURRENT_COUNT=3)
    for i in range(2):
        cases.append(CrimeCase(
            case_number=f"CR-NORM-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_a"].id, occurred_at=world["_ago"](5 + i),
            status="open", description="normal",
        ))
    for i in range(6):
        cases.append(CrimeCase(
            case_number=f"CR-NORM-B{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_a"].id, occurred_at=world["_ago"](40 + i),
            status="closed", description="baseline",
        ))
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones
    result = detect_red_zones(db_session)
    # 2 current < MIN_CURRENT_COUNT (3) -> no alert
    assert result["total_alerts"] == 0


# ---------------------------------------------------------------------------
# Test 2 — Crime spike (correct alert type and severity)
# ---------------------------------------------------------------------------

def test_crime_spike_generates_alert(db_session):
    """Crime activity exceeds threshold -> correct alert type and severity."""
    world = _seed_districts(db_session)
    cases = []
    # 5 recent incidents, 0 baseline -> spike
    for i in range(5):
        cases.append(CrimeCase(
            case_number=f"CR-SPIKE-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](2 + i),
            status="open", description="spike incident",
        ))
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones
    result = detect_red_zones(db_session)
    assert result["total_alerts"] >= 1

    alert = result["red_zones"][0]
    assert alert["type"] == AlertType.RED_ZONE_SPIKE.value
    assert alert["severity"] == AlertSeverity.CRITICAL.value
    assert alert["district"] == "Bengaluru Urban"
    assert alert["crime_category"] == "Burglary"
    assert alert["evidence"]["current_count"] == 5
    assert alert["evidence"]["baseline_count"] == 0.0


# ---------------------------------------------------------------------------
# Test 3 — Insufficient baseline (INSUFFICIENT_DATA)
# ---------------------------------------------------------------------------

def test_insufficient_baseline_marks_insufficient_data(db_session):
    """No historical data -> confidence = INSUFFICIENT_DATA."""
    world = _seed_districts(db_session)
    cases = []
    # 4 recent incidents, zero baseline
    for i in range(4):
        cases.append(CrimeCase(
            case_number=f"CR-INSUF-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](1 + i),
            status="open", description="new incident",
        ))
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones
    result = detect_red_zones(db_session)
    assert result["total_alerts"] >= 1
    alert = result["red_zones"][0]
    assert alert["confidence"] == Confidence.INSUFFICIENT_DATA.value
    assert alert["evidence"]["baseline_observations"] == 0
    # Should have INSUFFICIENT_BASELINE warning
    codes = [w["code"] for w in alert["warnings"]]
    assert "INSUFFICIENT_BASELINE" in codes


# ---------------------------------------------------------------------------
# Test 4 — Minimum evidence (alert suppressed below threshold)
# ---------------------------------------------------------------------------

def test_below_minimum_evidence_suppressed(db_session):
    """Fewer than MIN_CURRENT_COUNT incidents -> no alert generated."""
    world = _seed_districts(db_session)
    cases = []
    # Only 2 incidents (below default MIN_CURRENT_COUNT=3)
    for i in range(2):
        cases.append(CrimeCase(
            case_number=f"CR-MINEV-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_a"].id, occurred_at=world["_ago"](3 + i),
            status="open", description="few incidents",
        ))
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones
    result = detect_red_zones(db_session, min_current=3)
    assert result["total_alerts"] == 0


# ---------------------------------------------------------------------------
# Test 5 — District ranking (documented metric)
# ---------------------------------------------------------------------------

def test_district_ranking_follows_metric(db_session):
    """Districts ranked by incident_count in descending order."""
    world = _seed_districts(db_session)
    cases = []
    # 5 incidents in loc_b, 2 in loc_a
    for i in range(5):
        cases.append(CrimeCase(
            case_number=f"CR-RANK-B-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](5 + i),
            status="open", description="ranking test",
        ))
    for i in range(2):
        cases.append(CrimeCase(
            case_number=f"CR-RANK-A-{i:02d}", category_id=world["cat_low"].id,
            location_id=world["loc_a"].id, occurred_at=world["_ago"](5 + i),
            status="open", description="ranking test",
        ))
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import rank_districts
    rankings = rank_districts(db_session, window_days=30)
    assert len(rankings) >= 2
    # Bengaluru Urban has more incidents -> ranked first
    assert rankings[0]["district"] == "Bengaluru Urban"
    assert rankings[0]["incident_count"] == 5
    assert rankings[0]["metric"] == DistrictRanking.METRIC
    # Ranks are sequential
    assert rankings[0]["rank"] < rankings[1]["rank"]


# ---------------------------------------------------------------------------
# Test 6 — Crime category ranking (documented policy)
# ---------------------------------------------------------------------------

def test_category_ranking_follows_policy(db_session):
    """Crime categories ranked by incident_count, with change_percentage."""
    world = _seed_districts(db_session)
    cases = []
    # 4 Burglary in current window
    for i in range(4):
        cases.append(CrimeCase(
            case_number=f"CR-CRANK-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_a"].id, occurred_at=world["_ago"](5 + i),
            status="open", description="category ranking",
        ))
    # 1 Trespass in current window, 3 in prior (decreasing)
    cases.append(CrimeCase(
        case_number="CR-CRANK-T-00", category_id=world["cat_low"].id,
        location_id=world["loc_a"].id, occurred_at=world["_ago"](5),
        status="closed", description="cat low recent",
    ))
    for i in range(3):
        cases.append(CrimeCase(
            case_number=f"CR-CRANK-T-P{i:02d}", category_id=world["cat_low"].id,
            location_id=world["loc_a"].id, occurred_at=world["_ago"](40 + i),
            status="closed", description="cat low prior",
        ))
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import rank_categories
    rankings = rank_categories(db_session, window_days=30)
    assert len(rankings) >= 2
    # Burglary has more incidents
    assert rankings[0]["category"] == "Burglary"
    assert rankings[0]["incident_count"] == 4
    assert rankings[0]["change_percentage"] is not None


# ---------------------------------------------------------------------------
# Test 7 — Demo data (provenance = DEMO or UNKNOWN with warning)
# ---------------------------------------------------------------------------

def test_demo_provenance_tagged_and_warned(db_session):
    """Alert from seed/demo data -> provenance is not LIVE, warning included."""
    world = _seed_districts(db_session)
    cases = []
    for i in range(5):
        case = CrimeCase(
            case_number=f"CR-DEMO-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](2 + i),
            status="open", description="demo incident",
        )
        # Seed data: no import_job_id -> dataset_provenance defaults to "live"
        # but has no source_import_job_id, so we mark it explicitly for the test
        case.dataset_provenance = "seed"
        cases.append(case)
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones
    result = detect_red_zones(db_session)
    assert result["total_alerts"] >= 1
    alert = result["red_zones"][0]
    # "seed" provenance -> should be classified as DEMO (not LIVE)
    assert alert["provenance"] != Provenance.LIVE.value
    assert alert["provenance"] in (Provenance.DEMO.value, Provenance.MIXED.value, Provenance.UNKNOWN.value)
    codes = [w["code"] for w in alert["warnings"]]
    assert len(codes) > 0  # Should have at least one warning


# ---------------------------------------------------------------------------
# Test 8 — Mixed data (provenance = MIXED)
# ---------------------------------------------------------------------------

def test_mixed_provenance_detected(db_session):
    """Alert from both LIVE and seed records -> provenance = MIXED."""
    world = _seed_districts(db_session)
    cases = []
    for i in range(4):
        case = CrimeCase(
            case_number=f"CR-MIX-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](2 + i),
            status="open", description="mixed incident",
        )
        # Mix: first case is live, rest are seed
        if i == 0:
            case.dataset_provenance = "live"
        else:
            case.dataset_provenance = "seed"
        cases.append(case)
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones
    result = detect_red_zones(db_session)
    assert result["total_alerts"] >= 1
    alert = result["red_zones"][0]
    assert alert["provenance"] == Provenance.MIXED.value
    codes = [w["code"] for w in alert["warnings"]]
    assert "MIXED_PROVENANCE" in codes


# ---------------------------------------------------------------------------
# Test 9 — Unknown provenance (not classified as LIVE)
# ---------------------------------------------------------------------------

def test_unknown_provenance_not_live(db_session):
    """Unknown provenance -> never classified as LIVE."""
    world = _seed_districts(db_session)
    cases = []
    # Enough current (4) and baseline (3) to avoid INSUFFICIENT_DATA
    for i in range(4):
        case = CrimeCase(
            case_number=f"CR-UNKN-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](2 + i),
            status="open", description="unknown provenance",
        )
        case.dataset_provenance = "unknown_value"
        cases.append(case)
    for i in range(3):
        case = CrimeCase(
            case_number=f"CR-UNKN-B{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](50 + i),
            status="closed", description="baseline",
        )
        case.dataset_provenance = "unknown_value"
        cases.append(case)
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones
    result = detect_red_zones(db_session)
    assert result["total_alerts"] >= 1
    alert = result["red_zones"][0]
    assert alert["provenance"] != Provenance.LIVE.value
    # With unknown provenance, confidence should be LOW (not HIGH)
    assert alert["confidence"] in (Confidence.LOW.value, Confidence.MEDIUM.value, Confidence.INSUFFICIENT_DATA.value)


# ---------------------------------------------------------------------------
# Test 10 — Alert evidence (valid supporting record references)
# ---------------------------------------------------------------------------

def test_alert_evidence_contains_record_ids(db_session):
    """Every alert contains valid supporting_record_ids."""
    world = _seed_districts(db_session)
    cases = []
    for i in range(4):
        cases.append(CrimeCase(
            case_number=f"CR-EVID-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](2 + i),
            status="open", description="evidence test",
        ))
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones
    result = detect_red_zones(db_session)
    assert result["total_alerts"] >= 1
    alert = result["red_zones"][0]
    evidence = alert["evidence"]
    assert evidence["supporting_records"] >= 1
    assert len(evidence["supporting_record_ids"]) >= 1
    # All IDs are valid UUIDs
    for rid in evidence["supporting_record_ids"]:
        uuid.UUID(rid)


# ---------------------------------------------------------------------------
# Test 11 — Deduplication (no unlimited duplicate alerts)
# ---------------------------------------------------------------------------

def test_deduplication_suppresses_duplicates(db_session):
    """Repeated notify_red_zones calls do not create duplicate notifications."""
    world = _seed_districts(db_session)
    cases = []
    for i in range(5):
        cases.append(CrimeCase(
            case_number=f"CR-DEDUP-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](2 + i),
            status="open", description="dedup test",
        ))
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones, notify_red_zones
    result = detect_red_zones(db_session)
    zones = result["red_zones"]

    # First call creates notifications
    first = notify_red_zones(db_session, zones)
    assert first["created"] >= 1
    assert first["skipped"] == 0

    # Second call skips all (deduplication)
    second = notify_red_zones(db_session, zones)
    assert second["created"] == 0
    assert second["skipped"] == first["created"]

    # Verify only one notification per resource_id
    stored = db_session.query(Notification).filter_by(notification_type="red_zone_spike").all()
    resource_ids = [n.resource_id for n in stored]
    assert len(resource_ids) == len(set(resource_ids))


# ---------------------------------------------------------------------------
# Test 12 — Policy version (recorded on every alert)
# ---------------------------------------------------------------------------

def test_policy_version_recorded(db_session):
    """Every generated alert records the policy version."""
    world = _seed_districts(db_session)
    cases = []
    for i in range(5):
        cases.append(CrimeCase(
            case_number=f"CR-PVER-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](2 + i),
            status="open", description="policy version test",
        ))
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones
    result = detect_red_zones(db_session)
    assert result["policy_version"] == ALERT_POLICY_VERSION
    for alert in result["red_zones"]:
        assert alert["policy_version"] == ALERT_POLICY_VERSION


# ---------------------------------------------------------------------------
# Test 13 — Priority (severity follows documented rules)
# ---------------------------------------------------------------------------

def test_severity_follows_documented_rules(db_session):
    """Severity classification follows policy: critical for zero-baseline+5 or ratio>=2.5."""
    world = _seed_districts(db_session)
    cases = []

    # Case A: 5 incidents, zero baseline -> CRITICAL (zero baseline + count >= 5)
    for i in range(5):
        cases.append(CrimeCase(
            case_number=f"CR-SEV-A-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](2 + i),
            status="open", description="critical candidate",
        ))

    # Case B: 3 incidents, 2 baseline -> ratio = 3/(2*30/90) = 3/0.67 ~ 4.5 -> CRITICAL
    for i in range(3):
        cases.append(CrimeCase(
            case_number=f"CR-SEV-B-{i:02d}", category_id=world["cat_low"].id,
            location_id=world["loc_a"].id, occurred_at=world["_ago"](2 + i),
            status="open", description="high candidate",
        ))
    for i in range(2):
        cases.append(CrimeCase(
            case_number=f"CR-SEV-BL-{i:02d}", category_id=world["cat_low"].id,
            location_id=world["loc_a"].id, occurred_at=world["_ago"](50 + i),
            status="closed", description="baseline",
        ))

    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones
    result = detect_red_zones(db_session)
    zones = {(z["district"], z["crime_category"]): z for z in result["red_zones"]}

    # Bengaluru/Burglary: 5 current, 0 baseline -> CRITICAL
    key_a = ("Bengaluru Urban", "Burglary")
    assert key_a in zones
    assert zones[key_a]["severity"] == AlertSeverity.CRITICAL.value

    # Mysuru/Trespass: high ratio -> at least HIGH
    key_b = ("Mysuru", "Trespass")
    assert key_b in zones
    assert zones[key_b]["severity"] in (AlertSeverity.CRITICAL.value, AlertSeverity.HIGH.value)


# ---------------------------------------------------------------------------
# Test 14 — Authorization (unauthorized users cannot access admin endpoint)
# ---------------------------------------------------------------------------

def test_policy_endpoint_requires_admin(admin_client, db_session):
    """Admin policy endpoint is restricted to admin role — admin can access."""
    resp = admin_client.get("/api/v2/alerts/policy")
    assert resp.status_code == 200
    body = resp.json()
    assert body["policy_version"] == ALERT_POLICY_VERSION
    assert "red_zone" in body
    assert "anomaly" in body


def test_policy_endpoint_rejects_non_admin(analyst_client, db_session):
    """Admin policy endpoint rejects non-admin roles -> 403."""
    resp = analyst_client.get("/api/v2/alerts/policy")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Additional tests: alert structure, ranking routes, baseline status
# ---------------------------------------------------------------------------

def test_alert_structure_matches_schema(db_session):
    """Alert items contain all required fields per AlertItem schema."""
    world = _seed_districts(db_session)
    cases = []
    for i in range(4):
        cases.append(CrimeCase(
            case_number=f"CR-SCHEMA-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](2 + i),
            status="open", description="schema test",
        ))
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones
    result = detect_red_zones(db_session)
    required_fields = {
        "alert_id", "type", "severity", "status", "district", "crime_category",
        "policy_version", "provenance", "confidence", "evidence", "explanation",
        "warnings", "detection_timestamp",
    }
    for alert in result["red_zones"]:
        assert required_fields.issubset(alert.keys()), f"Missing fields: {required_fields - alert.keys()}"
        # Evidence sub-fields
        evidence_fields = {
            "current_count", "baseline_count", "spike_ratio",
            "supporting_records", "supporting_record_ids", "baseline_observations", "stations",
        }
        assert evidence_fields.issubset(alert["evidence"].keys())


def test_ranking_routes(analyst_client, db_session):
    """Ranking routes return valid structured responses."""
    world = _seed_districts(db_session)
    cases = []
    for i in range(4):
        cases.append(CrimeCase(
            case_number=f"CR-ROUTE-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](5 + i),
            status="open", description="route test",
        ))
    db_session.add_all(cases)
    db_session.commit()

    # District ranking
    resp = analyst_client.get("/api/v2/alerts/ranking/districts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["metric"] == "incident_count"
    assert len(body["districts"]) >= 1

    # Category ranking
    resp = analyst_client.get("/api/v2/alerts/ranking/categories")
    assert resp.status_code == 200
    body = resp.json()
    assert body["metric"] == "incident_count"
    assert len(body["categories"]) >= 1


def test_baseline_status_sufficient_when_enough_data(db_session):
    """When baseline has >= MIN_BASELINE_OBSERVATIONS, status = SUFFICIENT."""
    world = _seed_districts(db_session)
    cases = []
    # 4 current, 3 baseline -> baseline_observations = 3 >= 1
    for i in range(4):
        cases.append(CrimeCase(
            case_number=f"CR-BSUF-{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](2 + i),
            status="open", description="sufficient baseline",
        ))
    for i in range(3):
        cases.append(CrimeCase(
            case_number=f"CR-BSUF-B{i:02d}", category_id=world["cat_high"].id,
            location_id=world["loc_b"].id, occurred_at=world["_ago"](50 + i),
            status="closed", description="baseline data",
        ))
    db_session.add_all(cases)
    db_session.commit()

    from app.services.redzone_service import detect_red_zones
    result = detect_red_zones(db_session)
    assert result["total_alerts"] >= 1
    alert = result["red_zones"][0]
    assert alert["evidence"]["baseline_observations"] == 3
    # With 3 baseline observations and seed provenance, confidence is not INSUFFICIENT_DATA
    assert alert["confidence"] != Confidence.INSUFFICIENT_DATA.value


def test_get_current_policy_returns_all_sections():
    """get_current_policy() returns all documented policy sections."""
    policy = get_current_policy()
    assert policy["policy_version"] == ALERT_POLICY_VERSION
    assert "red_zone" in policy
    assert "anomaly" in policy
    assert "incident_priority" in policy
    assert "district_ranking" in policy
    assert "category_ranking" in policy
    assert "evidence_requirements" in policy
    assert "dedup_window_minutes" in policy
    # Verify red zone thresholds match constants
    assert policy["red_zone"]["current_window_days"] == RedZoneThresholds.CURRENT_WINDOW_DAYS
    assert policy["red_zone"]["baseline_window_days"] == RedZoneThresholds.BASELINE_WINDOW_DAYS
    assert policy["red_zone"]["min_current_count"] == RedZoneThresholds.MIN_CURRENT_COUNT
    assert policy["red_zone"]["ratio_threshold"] == RedZoneThresholds.RATIO_THRESHOLD
