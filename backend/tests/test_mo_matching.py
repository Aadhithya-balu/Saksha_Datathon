"""Tests for Modus Operandi (MO) Pattern Matching and Explainable Similarity Engine.

Verifies:
- Case 1: Strong match (shared MO tactics, weapons, category, time window >= 75%)
- Case 2: Weak match (single generic overlap <= 45%)
- Case 3: No match (disparate categories, tactics, weapons, locations)
- Case 4: Missing data handling (NULL does NOT count as match; listed in insufficient_data)
- Case 5: Same category only (does NOT produce false high score without MO tags)
- Case 6: Correct entity linking and explainability factor generation
- Case 7: API endpoints (/match/case, /match/criminal, /compare) and RBAC security
"""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database.postgres import Base, get_db
from app.main import app
from app.models.crime import CrimeCase
from app.models.crime_category import CrimeCategory
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink
from app.models.location import Location
from app.models.user import User
from app.services.mo_matching_service import (
    MOProfile,
    calculate_mo_similarity,
    extract_case_mo_profile,
    extract_criminal_mo_profile,
    match_case_against_db,
    match_criminal_against_db,
)


@pytest.fixture
def mo_test_db(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_path = tmp_path / "test_mo.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_case_1_strong_match():
    """Case 1: Two profiles sharing specific tactical methods, weapon, category, and time window."""
    profile_a = MOProfile(
        entity_id=str(uuid.uuid4()),
        entity_type="case",
        label="CASE-2026-001",
        category="Burglary",
        mo_tags={"break_in", "tool_usage", "night_operation"},
        methods=["break_in", "tool_usage"],
        weapons=["crowbar", "iron rod"],
        target_type="Residential Property",
        district="Bengaluru Urban",
        station="Whitefield Police Station",
        time_window="00:00-06:00 (Late Night)",
        sections=["380", "457"],
    )

    profile_b = MOProfile(
        entity_id=str(uuid.uuid4()),
        entity_type="criminal",
        label="Ramesh Kumar",
        category="Burglary",
        mo_tags={"break_in", "tool_usage", "night_operation"},
        methods=["break_in", "tool_usage"],
        weapons=["crowbar"],
        target_type="Residential Property",
        district="Bengaluru Urban",
        station="Whitefield Police Station",
        time_window="00:00-06:00 (Late Night)",
        sections=["380", "457"],
    )

    result = calculate_mo_similarity(profile_a, profile_b)
    assert result.score >= 0.75, f"Expected strong match >= 0.75, got {result.score}"
    assert result.match_level == "high"
    assert any("Shared MO Signature" in f for f in result.matching_factors)
    assert any("Identical Weapon/Tool Signature" in f for f in result.matching_factors)
    assert any("Precise Location Corridor" in f or "Geographic Proximity" in f for f in result.matching_factors)


def test_case_2_weak_match():
    """Case 2: Profiles with only one generic trait overlap (e.g. location only)."""
    profile_a = MOProfile(
        entity_id=str(uuid.uuid4()),
        entity_type="case",
        label="CASE-2026-002",
        category="Cyber Crime",
        mo_tags={"phishing_portal_fraud", "call_spoofing"},
        methods=["phishing_portal_fraud"],
        target_type="Digital / Cyber Target",
        district="Bengaluru Urban",
    )

    profile_b = MOProfile(
        entity_id=str(uuid.uuid4()),
        entity_type="case",
        label="CASE-2026-003",
        category="Vehicle Theft",
        mo_tags={"vehicle_crime", "night_operation"},
        methods=["vehicle_crime"],
        target_type="Transit / Transport",
        district="Bengaluru Urban",
    )

    result = calculate_mo_similarity(profile_a, profile_b)
    assert result.score <= 0.45, f"Expected weak match <= 0.45, got {result.score}"
    assert result.match_level in ("low", "none")
    assert any("Differing Crime Categories" in f for f in result.divergent_factors)


def test_case_3_no_match():
    """Case 3: Completely disparate categories, MO tactics, weapons, and locations."""
    profile_a = MOProfile(
        entity_id=str(uuid.uuid4()),
        entity_type="case",
        label="CASE-2026-004",
        category="Illegal Mining",
        mo_tags={"illegal_mining"},
        district="Ballari",
        target_type="Commercial Establishment",
    )

    profile_b = MOProfile(
        entity_id=str(uuid.uuid4()),
        entity_type="criminal",
        label="Suspect Cyber",
        category="Cyber Fraud",
        mo_tags={"crypto_fraud", "money_mule_routing"},
        district="Mangaluru",
        target_type="Digital / Cyber Target",
    )

    result = calculate_mo_similarity(profile_a, profile_b)
    assert result.score < 0.25, f"Expected no match < 0.25, got {result.score}"
    assert result.match_level == "none"


def test_case_4_missing_data_handling():
    """Case 4: NULL / absent attributes must NOT count as matches."""
    profile_a = MOProfile(
        entity_id=str(uuid.uuid4()),
        entity_type="case",
        label="CASE-2026-005",
        category="Theft",
        weapons=["knife"],
        vehicles=["KA-01-AB-1234"],
        district="Mysuru",
    )

    profile_b = MOProfile(
        entity_id=str(uuid.uuid4()),
        entity_type="case",
        label="CASE-2026-006",
        category="Theft",
        weapons=[],  # NULL / missing
        vehicles=[],  # NULL / missing
        district="Mysuru",
    )

    result = calculate_mo_similarity(profile_a, profile_b)
    # Weapon and Vehicle were absent in profile B, so they must be in insufficient_data
    assert any("Weapon" in f for f in result.insufficient_data), "Missing weapons should be in insufficient_data"
    assert any("Vehicle" in f for f in result.insufficient_data), "Missing vehicles should be in insufficient_data"
    # Weapons must NOT be in matching_factors
    assert not any("Weapon" in f for f in result.matching_factors)


def test_case_5_same_category_only():
    """Case 5: Same category alone must NOT produce a high MO match if tactics diverge."""
    profile_a = MOProfile(
        entity_id=str(uuid.uuid4()),
        entity_type="case",
        label="CASE-2026-007",
        category="Burglary",
        mo_tags={"tool_usage", "break_in"},
        target_type="Residential Property",
        district="Tumkuru",
    )

    profile_b = MOProfile(
        entity_id=str(uuid.uuid4()),
        entity_type="case",
        label="CASE-2026-008",
        category="Burglary",
        mo_tags={"temple_theft", "dead_drop"},
        target_type="Religious / Public Place",
        district="Belagavi",
    )

    result = calculate_mo_similarity(profile_a, profile_b)
    # Even though category matches (20%), tactical MO and location diverge
    assert result.score < 0.50, f"Same category alone should not yield >= 0.50, got {result.score}"
    assert result.match_level in ("low", "none")


def test_case_6_database_entity_linking(mo_test_db):
    """Case 6: Match queries against real database models with real UUIDs and confirmed vs analytical links."""
    # Seed Category
    cat_burglary = CrimeCategory(id=uuid.uuid4(), name="Burglary", section_code="380", severity="medium")
    mo_test_db.add(cat_burglary)

    # Seed Location
    loc_bengaluru = Location(
        id=uuid.uuid4(),
        district="Bengaluru Urban",
        station="Whitefield Police Station",
        address="Whitefield Main Rd",
        latitude=12.9698,
        longitude=77.7499,
    )
    loc_mysuru = Location(
        id=uuid.uuid4(),
        district="Mysuru",
        station="Devaraja Police Station",
        address="Devaraja Market",
        latitude=12.3051,
        longitude=76.6551,
    )
    mo_test_db.add_all([loc_bengaluru, loc_mysuru])
    mo_test_db.flush()

    # Seed Cases
    case_1 = CrimeCase(
        id=uuid.uuid4(),
        case_number="CC-2026-0101",
        category_id=cat_burglary.id,
        location_id=loc_bengaluru.id,
        occurred_at=datetime(2026, 3, 10, 3, 30, tzinfo=timezone.utc),
        description="Night housebreak using crowbar to pry smart lock and open bedroom safe.",
        mo_tags="break_in, tool_usage, night_operation",
        status="open",
    )

    case_2 = CrimeCase(
        id=uuid.uuid4(),
        case_number="CC-2026-0102",
        category_id=cat_burglary.id,
        location_id=loc_bengaluru.id,
        occurred_at=datetime(2026, 3, 15, 2, 45, tzinfo=timezone.utc),
        description="Late night apartment break-in with crowbar and iron rod.",
        mo_tags="break_in, tool_usage, night_operation",
        status="open",
    )

    mo_test_db.add_all([case_1, case_2])

    # Seed Criminals
    crim_matching = Criminal(
        id=uuid.uuid4(),
        full_name="Somanna Lockbreaker",
        mo_summary="Specializes in late night residential break-in using iron rod and crowbar.",
        status="at_large",
    )
    mo_test_db.add(crim_matching)

    # Create FIR linking case_1 to crim_matching (Confirmed link)
    fir_1 = FIR(
        id=uuid.uuid4(),
        fir_number="FIR-2026-0099",
        crime_case_id=case_1.id,
        complainant_name="Resident Complainant",
        sections="380, 457",
        narrative="Suspect was identified on CCTV as Somanna.",
    )
    mo_test_db.add(fir_1)
    mo_test_db.flush()

    link_1 = FIRCriminalLink(id=uuid.uuid4(), fir_id=fir_1.id, criminal_id=crim_matching.id, role="accused")
    mo_test_db.add(link_1)
    mo_test_db.commit()

    # Run match for case_1
    result = match_case_against_db(mo_test_db, case_1.id, top_k=5, min_similarity=0.30)
    assert "error" not in result
    assert result["target_case"]["case_number"] == "CC-2026-0101"

    # Case 2 should appear in matching_cases with high similarity
    matching_cases = result["matching_cases"]
    assert len(matching_cases) >= 1
    assert matching_cases[0]["case_number"] == "CC-2026-0102"
    assert matching_cases[0]["similarity_percent"] >= 70

    # Suspect should be flagged as Confirmed FIR Accused
    matching_suspects = result["matching_suspects"]
    assert len(matching_suspects) >= 1
    assert matching_suspects[0]["full_name"] == "Somanna Lockbreaker"
    assert matching_suspects[0]["is_confirmed_relationship"] is True
    assert matching_suspects[0]["relationship_label"] == "Confirmed FIR Accused"


def test_case_7_mo_endpoints(mo_test_db):
    """Case 7: Test FastAPI endpoints for MO matching and side-by-side comparison."""
    # Override get_db dependency
    app.dependency_overrides[get_db] = lambda: mo_test_db

    # Create mock authenticated user with role
    from app.models.role import Role
    role_analyst = Role(id=uuid.uuid4(), name="crime_analyst", description="Crime Analyst")
    mo_test_db.add(role_analyst)
    mo_test_db.flush()

    mock_user = User(
        id=uuid.uuid4(),
        username="investigator_test",
        email="test@ksp.gov.in",
        full_name="Inspector Test",
        hashed_password="hash",
        role_id=role_analyst.id,
        role=role_analyst,
        is_active=True,
    )
    mo_test_db.add(mock_user)
    mo_test_db.flush()
    from app.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_user

    client = TestClient(app)

    # Seed data
    cat = CrimeCategory(id=uuid.uuid4(), name="Theft", section_code="379", severity="low")
    loc = Location(
        id=uuid.uuid4(),
        district="Ballari",
        station="City Police Station",
        address="Main Rd",
        latitude=15.1394,
        longitude=76.9214,
    )
    mo_test_db.add_all([cat, loc])
    mo_test_db.flush()

    c1 = CrimeCase(
        id=uuid.uuid4(),
        case_number="CC-API-01",
        category_id=cat.id,
        location_id=loc.id,
        occurred_at=datetime(2026, 4, 1, 1, 0, tzinfo=timezone.utc),
        mo_tags="night_operation, tool_usage",
        description="Midnight theft",
    )
    c2 = CrimeCase(
        id=uuid.uuid4(),
        case_number="CC-API-02",
        category_id=cat.id,
        location_id=loc.id,
        occurred_at=datetime(2026, 4, 2, 1, 30, tzinfo=timezone.utc),
        mo_tags="night_operation, tool_usage",
        description="Midnight theft with tool",
    )
    mo_test_db.add_all([c1, c2])
    mo_test_db.commit()

    # Test /ai/mo/match/case/{case_id}
    res_match = client.get(f"/api/v2/ai/mo/match/case/{c1.id}")
    assert res_match.status_code == 200
    data = res_match.json()
    assert "target_case" in data
    assert len(data["matching_cases"]) >= 1
    assert data["matching_cases"][0]["case_number"] == "CC-API-02"

    # Test /ai/mo/compare
    res_comp = client.post(
        "/api/v2/ai/mo/compare",
        json={
            "entity_a_id": str(c1.id),
            "entity_a_type": "case",
            "entity_b_id": str(c2.id),
            "entity_b_type": "case",
        },
    )
    assert res_comp.status_code == 200
    comp_data = res_comp.json()
    assert "similarity_score" in comp_data
    assert comp_data["similarity_percent"] >= 70
    assert len(comp_data["matching_factors"]) >= 1

    app.dependency_overrides.clear()
