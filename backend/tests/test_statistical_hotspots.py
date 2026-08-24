"""Tests for statistically-grounded hotspot scoring and temporal analytics
(issue #143: gaps 131.1 Gi*/KDE/Moran's I, 131.3 hour x day matrix,
131.4 temporal deployment suggestions)."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.location import Location
from app.models.role import Role
from app.models.user import User
from app.services.analytics_service import (
    gaussian_kde_density,
    getis_ord_gi_star,
    hotspots,
    morans_i,
)
from app.services.sociological_service import get_temporal_hotspot_matrix
from app.services.strategic_service import (
    _district_temporal_windows,
    _generate_deployment_suggestions,
)

TM = "/api/v2/sociological/temporal-matrix"


@pytest.fixture
def analyst_client(client, db_session):
    role = db_session.query(Role).filter_by(name="crime_analyst").first()
    if role is None:
        role = Role(name="crime_analyst", description="Crime Analyst")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="hs-analyst",
        email="hs-analyst@example.com",
        full_name="Hotspot Analyst",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield client, user
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def spatial_fixture(db_session):
    """One dense crime location and one sparse one, far apart geographically."""
    category = CrimeCategory(name="Theft & Burglaries", section_code="IPC 379", severity="high")
    dense_loc = Location(district="Bengaluru Urban", station="KR Puram", latitude=13.01, longitude=77.70)
    sparse_loc = Location(district="Mysuru", station="Nanjangud", latitude=12.11, longitude=76.68)
    db_session.add_all([category, dense_loc, sparse_loc])
    db_session.flush()

    now = datetime.now(timezone.utc)
    cases = []
    for i in range(12):  # dense cluster, all recent
        cases.append(CrimeCase(
            case_number=f"CR-HS-D{i:02d}", category_id=category.id, location_id=dense_loc.id,
            occurred_at=now - timedelta(days=i % 10), status="open",
        ))
    for i in range(2):  # sparse, older
        cases.append(CrimeCase(
            case_number=f"CR-HS-S{i:02d}", category_id=category.id, location_id=sparse_loc.id,
            occurred_at=now - timedelta(days=90 + i), status="closed",
        ))
    db_session.add_all(cases)
    db_session.commit()
    return {"dense": dense_loc, "sparse": sparse_loc}


# ---------------------------------------------------------------------------
# Unit-level statistics helpers (131.1)
# ---------------------------------------------------------------------------

def test_getis_ord_flags_planted_cluster():
    """A planted high-count cluster on a ring scores z > 2 with p < 0.05."""
    counts = np.array([15.0] + [1.0] * 19)
    n = len(counts)
    weights = np.zeros((n, n))
    for i in range(n):
        weights[i, i] = 1.0
        weights[i, (i - 1) % n] = 1.0
        weights[i, (i + 1) % n] = 1.0
    z_scores, p_values = getis_ord_gi_star(counts, weights)
    assert z_scores[0] > 2.0
    assert p_values[0] < 0.05


def test_morans_i_detects_spatial_autocorrelation():
    counts = np.array([5.0, 6.0, 7.0, 1.0, 1.0, 2.0])
    n = len(counts)
    weights = np.zeros((n, n))
    for i in range(n):
        for j in {max(i - 1, 0), min(i + 1, n - 1)}:
            if i != j:
                weights[i, j] = 1.0
    result = morans_i(counts, weights)
    assert result["moran_i"] is not None
    assert result["moran_i"] > 0.4
    assert result["z_score"] > 1.0


def test_kde_separates_dense_from_sparse():
    rng = np.random.default_rng(42)
    cluster = np.column_stack([rng.normal(13.0, 0.005, 40), rng.normal(77.7, 0.005, 40)])
    outliers = np.column_stack([rng.normal(15.0, 0.02, 4), rng.normal(75.0, 0.02, 4)])
    points = np.vstack([cluster, outliers])
    eval_at_cluster = np.array([[13.0, 77.7]])
    eval_at_outlier = np.array([[15.0, 75.0]])
    d_cluster = gaussian_kde_density(points[:, 0], points[:, 1], eval_at_cluster[:, 0], eval_at_cluster[:, 1])[0]
    d_outlier = gaussian_kde_density(points[:, 0], points[:, 1], eval_at_outlier[:, 0], eval_at_outlier[:, 1])[0]
    assert d_cluster > d_outlier * 5


# ---------------------------------------------------------------------------
# Service integration (131.1)
# ---------------------------------------------------------------------------

def test_hotspots_response_contract(spatial_fixture, db_session):
    body = hotspots(db_session)
    stats = body["statistics"]
    assert stats["method"] == "getis_ord_gi_star+kde+morans_i"
    assert stats["locations_assessed"] == 2
    assert stats["incidents_assessed"] == 14
    for key in ("moran_i", "expected_i", "z_score", "p_value", "bandwidth_km"):
        assert key in stats

    rows = body["hotspots"]
    assert len(rows) == 2
    top = rows[0]
    for key in ("score", "z_score", "p_value", "kde_percentile", "significant", "count"):
        assert key in top
    dense_row = next(r for r in rows if r["name"] == "KR Puram")
    sparse_row = next(r for r in rows if r["name"] == "Nanjangud")
    assert dense_row["score"] >= sparse_row["score"]
    assert dense_row["count"] == 12
    assert dense_row["trend"] == "up"
    assert sparse_row["trend"] == "down"


def test_hotspots_empty_db_is_honest(db_session):
    body = hotspots(db_session)
    assert body["hotspots"] == []
    assert body["statistics"]["locations_assessed"] == 0
    assert body["statistics"]["incidents_assessed"] == 0


# ---------------------------------------------------------------------------
# Hour x day matrix (131.3)
# ---------------------------------------------------------------------------

def test_temporal_matrix_counts_and_peaks(spatial_fixture, db_session):
    """Known seeded datetimes must reproduce exact cross-tab totals."""
    body = get_temporal_hotspot_matrix(db_session)
    assert body["grand_total"] == 14
    assert sum(row["total"] for row in body["matrix"]) == 14
    assert sum(d["count"] for d in body["day_totals"]) == 14
    assert body["filters"] == {"district": None, "location_id": None}
    assert len(body["matrix"]) == 24
    assert [cell["day"] for cell in body["matrix"][0]["cells"]] == \
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def test_temporal_matrix_district_filter(spatial_fixture, db_session):
    filtered = get_temporal_hotspot_matrix(db_session, district="Mysuru")
    assert filtered["grand_total"] == 2
    unfiltered = get_temporal_hotspot_matrix(db_session, district="Nowhere")
    assert unfiltered["grand_total"] == 0


def test_temporal_matrix_endpoint(analyst_client, spatial_fixture):
    c, _ = analyst_client
    r = c.get(TM)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["grand_total"] == 14
    r_filtered = c.get(f"{TM}?district=Mysuru")
    assert r_filtered.status_code == 200
    assert r_filtered.json()["grand_total"] == 2


# ---------------------------------------------------------------------------
# Temporal deployment guidance (131.4)
# ---------------------------------------------------------------------------

def test_deployment_suggestions_include_night_patrol():
    districts_at_risk = [
        {"district": "Nightfall Nagar", "risk_level": "HIGH", "crime_count": 40},
    ]
    windows = {
        "Nightfall Nagar": {
            "peak_window_label": "18:00-24:00",
            "peak_window_share_pct": 55.0,
            "night_share_pct": 60.0,
            "weekend_share_pct": 10.0,
            "busiest_day": "Friday",
            "total_incidents": 40,
        }
    }
    suggestions = _generate_deployment_suggestions(districts_at_risk, [], [], temporal_windows=windows)
    night = [s for s in suggestions if s["resource_type"] == "night_patrol"]
    assert len(night) == 1
    assert "Nightfall Nagar" in night[0]["action"]
    assert night[0]["reason"].startswith("60.0% of incidents occur between 20:00 and 02:00")


def test_deployment_suggestions_weekend_patrol_fallback():
    districts_at_risk = [
        {"district": "Weekendpur", "risk_level": "MEDIUM", "crime_count": 10},
    ]
    windows = {
        "Weekendpur": {
            "peak_window_label": "06:00-12:00",
            "peak_window_share_pct": 30.0,
            "night_share_pct": 10.0,
            "weekend_share_pct": 50.0,
            "busiest_day": "Sunday",
            "total_incidents": 10,
        }
    }
    suggestions = _generate_deployment_suggestions(districts_at_risk, [], [], temporal_windows=windows)
    weekend = [s for s in suggestions if s["resource_type"] == "weekend_patrol"]
    assert len(weekend) == 1
    assert "Sunday" in weekend[0]["action"]


def test_district_temporal_windows_shape(spatial_fixture, db_session):
    profiles = _district_temporal_windows(db_session)
    assert set(profiles) == {"Bengaluru Urban", "Mysuru"}
    for profile in profiles.values():
        for key in ("total_incidents", "peak_window_label", "night_share_pct", "weekend_share_pct", "busiest_day"):
            assert key in profile
