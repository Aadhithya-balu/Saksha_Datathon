"""Tests for Issue #164: Data Provenance & Seed Data Integrity."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.postgres import Base


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# ImportProvenanceMixin tests
# ---------------------------------------------------------------------------

class TestImportProvenanceMixin:
    def test_crime_case_has_provenance_columns(self, db):
        from datetime import datetime, timezone
        from app.models.crime import CrimeCase
        from app.models.location import Location
        from app.models.crime_category import CrimeCategory

        location = Location(district="Test", latitude=12.0, longitude=77.0)
        category = CrimeCategory(name="TestCat")
        db.add_all([location, category])
        db.flush()

        case = CrimeCase(
            case_number="PROV-001",
            category_id=category.id,
            location_id=location.id,
            occurred_at=datetime.now(timezone.utc),
            status="open",
            dataset_provenance="demo",
            source_file="test.csv",
            source_row_ref="row-1",
        )
        db.add(case)
        db.flush()

        assert case.dataset_provenance == "demo"
        assert case.source_file == "test.csv"
        assert case.source_row_ref == "row-1"

    def test_location_has_provenance_columns(self, db):
        from app.models.location import Location

        loc = Location(
            district="Bengaluru",
            latitude=12.97,
            longitude=77.59,
            dataset_provenance="live",
        )
        db.add(loc)
        db.flush()

        assert loc.dataset_provenance == "live"

    def test_fir_has_provenance_columns(self, db):
        from datetime import datetime, timezone
        from app.models.fir import FIR
        from app.models.location import Location
        from app.models.crime_category import CrimeCategory
        from app.models.crime import CrimeCase

        location = Location(district="Test", latitude=12.0, longitude=77.0)
        category = CrimeCategory(name="TestCat")
        db.add_all([location, category])
        db.flush()

        case = CrimeCase(
            case_number="PROV-FIR-001",
            category_id=category.id,
            location_id=location.id,
            occurred_at=datetime.now(timezone.utc),
            status="open",
        )
        db.add(case)
        db.flush()

        fir = FIR(
            fir_number="FIR-PROV-001",
            crime_case_id=case.id,
            complainant_name="Test Complainant",
            dataset_provenance="migrated",
            source_import_job_id=uuid.uuid4(),
        )
        db.add(fir)
        db.flush()

        assert fir.dataset_provenance == "migrated"
        assert fir.source_import_job_id is not None

    def test_officer_has_provenance_columns(self, db):
        from app.models.officer import Officer

        officer = Officer(
            name="Test Officer",
            badge_number="BADGE-001",
            station="TestStation",
            dataset_provenance="demo",
        )
        db.add(officer)
        db.flush()

        assert officer.dataset_provenance == "demo"

    def test_evidence_has_provenance_columns(self, db):
        from datetime import datetime, timezone
        from app.models.evidence import Evidence
        from app.models.location import Location
        from app.models.crime_category import CrimeCategory
        from app.models.crime import CrimeCase

        location = Location(district="Test", latitude=12.0, longitude=77.0)
        category = CrimeCategory(name="TestCat")
        db.add_all([location, category])
        db.flush()

        case = CrimeCase(
            case_number="PROV-EV-001",
            category_id=category.id,
            location_id=location.id,
            occurred_at=datetime.now(timezone.utc),
            status="open",
        )
        db.add(case)
        db.flush()

        evidence = Evidence(
            case_id=case.id,
            title="Test Evidence",
            evidence_type="document",
            dataset_provenance="demo",
        )
        db.add(evidence)
        db.flush()

        assert evidence.dataset_provenance == "demo"


# ---------------------------------------------------------------------------
# Data quality service tests
# ---------------------------------------------------------------------------

class TestDataQualityService:
    def test_provenance_summary_empty_db(self, db):
        from app.services.data_quality_service import get_provenance_summary

        result = get_provenance_summary(db)
        assert result["total_records"] == 0
        assert result["by_provenance"]["demo"] == 0
        assert result["by_provenance"]["live"] == 0

    def test_provenance_summary_with_records(self, db):
        from app.models.location import Location
        from app.services.data_quality_service import get_provenance_summary

        db.add(Location(district="A", latitude=12.0, longitude=77.0, dataset_provenance="demo"))
        db.add(Location(district="B", latitude=13.0, longitude=78.0, dataset_provenance="live"))
        db.add(Location(district="C", latitude=14.0, longitude=79.0, dataset_provenance="demo"))
        db.flush()

        result = get_provenance_summary(db)
        assert result["total_records"] == 3
        assert result["by_provenance"]["demo"] == 2
        assert result["by_provenance"]["live"] == 1

    def test_data_quality_warnings_unknown_provenance(self, db):
        from app.models.location import Location
        from app.services.data_quality_service import get_data_quality_warnings

        loc = Location(district="X", latitude=12.0, longitude=77.0)
        # Simulate a record that was never properly tagged (e.g. from legacy import)
        loc.dataset_provenance = "unknown"
        db.add(loc)
        db.flush()

        warnings = get_data_quality_warnings(db)
        unknown_warnings = [w for w in warnings if w["type"] == "unknown_provenance"]
        assert len(unknown_warnings) > 0

    def test_admin_report_structure(self, db):
        from app.services.data_quality_service import get_admin_data_quality_report

        report = get_admin_data_quality_report(db)
        assert "summary" in report
        assert "entity_breakdown" in report
        assert "warnings" in report
        assert "provenance_values" in report
        assert set(report["provenance_values"]) == {"live", "migrated", "demo", "unknown"}


# ---------------------------------------------------------------------------
# Admin data-quality endpoint tests
# ---------------------------------------------------------------------------

class TestAdminDataQualityEndpoint:
    def test_data_quality_requires_admin(self, client):
        """Non-admin users should be denied."""
        resp = client.get("/api/v2/admin/data-quality")
        assert resp.status_code in (401, 403)

    def test_data_quality_report(self, client, db_session):
        """Authenticated admin should get the report."""
        from app.core.security import hash_password, create_access_token
        from app.models.user import User
        from app.models.role import Role

        role = Role(name="admin")
        db_session.add(role)
        db_session.flush()

        user = User(
            username="admin_test",
            email="admin@test.com",
            full_name="Admin Test",
            hashed_password=hash_password("testpass12345678"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()

        token = create_access_token(subject=user.username, role="admin")

        resp = client.get(
            "/api/v2/admin/data-quality",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "entity_breakdown" in data
        assert "warnings" in data
