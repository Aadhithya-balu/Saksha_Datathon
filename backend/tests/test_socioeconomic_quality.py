"""Evidence-driven socio-economic analytics tests (issue 7).

Covers district alias resolution, UNMAPPED handling, missing-value states,
per-record source-period provenance, coverage validation, and correlation
sample-size honesty.
"""
import pytest

from app.auth.dependencies import get_current_user
from app.core.security import hash_password
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.location import Location
from app.models.role import Role
from app.models.user import User
from app.services import sociological_service as svc
from datetime import datetime, timezone


@pytest.fixture(autouse=True)
def _clear_dataset_cache():
    svc._load_socioeconomic_dataset.cache_clear()
    yield
    svc._load_socioeconomic_dataset.cache_clear()


@pytest.fixture
def analyst(db_session, client):
    role = db_session.query(Role).filter_by(name="crime_analyst").first()
    if role is None:
        role = Role(name="crime_analyst", description="Crime Analyst")
        db_session.add(role)
        db_session.flush()
    user = User(
        username="soc-analyst",
        email="soc-analyst@example.com",
        full_name="Socio Analyst",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    yield user
    client.app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mixed_district_data(db_session):
    """Districts covering exact match, alias match, and an unmapped name."""
    category = CrimeCategory(name="Theft", section_code="IPC 379", severity="medium")
    db_session.add(category)
    db_session.flush()
    locations = {
        "Bengaluru Urban": Location(district="Bengaluru Urban", station="Whitefield Police Station", latitude=12.9, longitude=77.7),
        "Shimoga": Location(district="Shimoga", station="Shimoga Town Police Station", latitude=13.9, longitude=75.5),
        "Atlantis": Location(district="Atlantis", station="Atlantis Police Station", latitude=1.0, longitude=2.0),
    }
    for loc in locations.values():
        db_session.add(loc)
    db_session.flush()
    for i, (district, loc) in enumerate(locations.items()):
        db_session.add(CrimeCase(
            case_number=f"CR-SOC-{i:04d}", category_id=category.id, location_id=loc.id,
            occurred_at=datetime(2026, 1, 10, tzinfo=timezone.utc), status="open",
        ))
    db_session.commit()
    return locations


# ---------------------------------------------------------------------------
# Unit-level: resolution, coercion, provenance helpers
# ---------------------------------------------------------------------------

def test_resolve_exact_and_case_insensitive():
    reference = {"Bengaluru Urban": {}, "Mysuru": {}}
    assert svc.resolve_district("Bengaluru Urban", reference) == ("Bengaluru Urban", "exact")
    assert svc.resolve_district("mysuru", reference) == ("Mysuru", "case_insensitive")


def test_resolve_alias_spellings():
    reference = {k: {} for k in (
        "Bagalkot", "Yadgir", "Shivamogga", "Chikkaballapur", "Mangaluru", "Ballari",
    )}
    assert svc.resolve_district("Bagalkote", reference) == ("Bagalkot", "alias")
    assert svc.resolve_district("Yadagir", reference) == ("Yadgir", "alias")
    assert svc.resolve_district("Shimoga", reference) == ("Shivamogga", "alias")
    assert svc.resolve_district("Chikkaballapura", reference) == ("Chikkaballapur", "alias")
    assert svc.resolve_district("Dakshina Kannada", reference) == ("Mangaluru", "alias")


def test_resolve_unknown_returns_unmapped():
    reference = {"Mysuru": {}}
    key, method = svc.resolve_district("Atlantis", reference)
    assert key is None and method == "unmapped"
    key, method = svc.resolve_district("State HQ", reference)
    assert key is None and method == "unmapped"


def test_coerce_keeps_missing_values_none():
    entry = svc._coerce_indicator_entry({"district": "X", "population_lakhs": "", "literacy_rate": None})
    assert entry["population_lakhs"] is None
    assert entry["literacy_rate"] is None
    assert entry["type"] is None


def test_period_label_marks_census_data():
    period_value, label = svc._indicator_period_label({"data_year": 2011})
    assert period_value == 2011 and label == "Census 2011"


def test_indicator_state_never_fabricates():
    status_missing, value_missing = svc._indicator_state(None, "population_lakhs")
    assert (status_missing, value_missing) == (svc.DATA_UNAVAILABLE, None)
    status_zero, value_zero = svc._indicator_state({"unemployment_rate": 0.0}, "unemployment_rate")
    # A real recorded zero stays a zero — distinguishable from missing.
    assert (status_zero, value_zero) == (svc.DATA_AVAILABLE, 0.0)


# ---------------------------------------------------------------------------
# Endpoint-level behaviour
# ---------------------------------------------------------------------------

def test_overlay_reports_alias_match_and_unmapped(db_session, analyst, mixed_district_data):
    result = svc.get_socioeconomic_overlay(db_session)

    by_district = {o["district"]: o for o in result["districts"]}

    bengaluru = by_district["Bengaluru Urban"]
    assert bengaluru["mapping_status"] == svc.MAPPING_MATCHED
    assert bengaluru["match_method"] in ("exact", "case_insensitive")
    assert bengaluru["source_period"] == 2011
    assert bengaluru["period_label"] == "Census 2011"

    shimoga = by_district["Shimoga"]
    assert shimoga["mapping_status"] == svc.MAPPING_MATCHED
    assert shimoga["match_method"] == "alias"
    assert shimoga["canonical_district"] == "Shivamogga"
    assert shimoga["crime_per_lakh"] is not None

    atlantis = by_district["Atlantis"]
    assert atlantis["mapping_status"] == svc.MAPPING_UNMAPPED
    assert atlantis["limitation"]
    for column in svc._DATASET_NUMERIC_COLUMNS:
        assert atlantis["data_status"][column] == svc.DATA_UNAVAILABLE
        assert atlantis[column] is None
    assert atlantis["crime_per_lakh"] is None
    assert result["unmapped_districts"] == ["Atlantis"]


def test_overlay_correlation_details_expose_sample_size(db_session, analyst, mixed_district_data):
    result = svc.get_socioeconomic_overlay(db_session)
    details = result["correlation_details"]["literacy_vs_crime"]
    assert "sample_size" in details and "status" in details
    assert details["coefficient"] == details["coefficient"]  # no NaN


def test_urban_rural_buckets_unmapped_explicitly(db_session, analyst, mixed_district_data):
    result = svc.get_urban_rural_analysis(db_session)
    types = {row["type"]: row for row in result["urban_rural_distribution"]}
    assert set(types) >= {"urban", "semi_urban", "rural", "unmapped"}
    assert types["unmapped"]["count"] == 1  # Atlantis only
    assert "Atlantis" in result["unmapped_districts"]


def test_population_scatter_flags_unmapped(db_session, analyst, mixed_district_data):
    result = svc.get_population_crime_correlation(db_session)
    points = {p["district"]: p for p in result["scatter"]}
    assert points["Atlantis"]["mapping_status"] == svc.MAPPING_UNMAPPED
    assert points["Atlantis"]["population_density"] is None
    assert points["Shimoga"]["mapping_status"] == svc.MAPPING_MATCHED
    assert "density_crime_correlation" in result


def test_data_quality_report_computed_from_db(db_session, analyst, mixed_district_data):
    report = svc.get_data_quality_report(db_session)

    expected = report["expected_districts"]
    assert expected["count"] == 3
    assert set(expected["districts"]) == {"Bengaluru Urban", "Shimoga", "Atlantis"}

    mapping = report["mapping_validation"]
    assert mapping["matched_count"] == 2
    assert mapping["unmapped_count"] == 1
    alias_row = next(m for m in mapping["matched"] if m["district"] == "Shimoga")
    assert alias_row == {"district": "Shimoga", "canonical_district": "Shivamogga", "match_method": "alias"}

    coverage = {c["indicator"]: c for c in report["indicator_coverage"]}
    population_cov = coverage["population_lakhs"]
    assert population_cov["expected"] == 3
    assert population_cov["available"] == 2
    assert population_cov["missing_districts"] == ["Atlantis"]
    assert population_cov["coverage_pct"] == round(2 / 3 * 100, 1)
    # Approximations must be declared, never passed off as census evidence.
    assert coverage["avg_income_lakhs"]["approximated"] is True

    completeness = {r["district"]: r for r in report["record_completeness"]}
    assert completeness["Bengaluru Urban"]["period_label"] == "Census 2011"
    assert completeness["Bengaluru Urban"]["partial_record"] is False

    assert report["limitations"]


def test_data_quality_route(db_session, client, analyst, mixed_district_data):
    resp = client.get("/api/v2/sociological/data-quality")
    assert resp.status_code == 200
    body = resp.json()
    assert body["expected_districts"]["count"] == 3
    assert any(c["indicator"] == "literacy_rate" for c in body["indicator_coverage"])
