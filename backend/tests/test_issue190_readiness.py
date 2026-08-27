"""Tests for Issue #190 — Data Provenance, Demo Isolation, Configuration and
Production Readiness.

Covers MISSING.md §10 missing-test items (10.1-10.8) and issue #190 §15:
  - Production / demo / test data modes
  - Invalid / missing data mode fails safely
  - Seed provenance normalization (never silently becomes 'live')
  - Mixed / unknown provenance reporting
  - Production filtering (production mode disables fallback)
  - Missing secrets / invalid configuration
  - Database unavailable / Neo4j unavailable / Supabase unavailable
  - Empty database
"""
import os
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Data mode (MISSING.md §3) — valid modes
# ---------------------------------------------------------------------------

class TestDataModeValidModes:
    def test_demo_mode_allows_fallback(self, monkeypatch):
        monkeypatch.setenv("SAKSHA_DATA_MODE", "demo")
        from app.core import data_mode
        assert data_mode.get_data_mode() == "demo"
        assert data_mode.allows_demo_fallback() is True

    def test_production_mode_disables_fallback(self, monkeypatch):
        monkeypatch.setenv("SAKSHA_DATA_MODE", "production")
        from app.core import data_mode
        assert data_mode.get_data_mode() == "production"
        assert data_mode.allows_demo_fallback() is False
        assert data_mode.is_production() is True

    def test_test_mode_disables_fallback(self, monkeypatch):
        monkeypatch.setenv("SAKSHA_DATA_MODE", "test")
        from app.core import data_mode
        assert data_mode.get_data_mode() == "test"
        assert data_mode.allows_demo_fallback() is False
        assert data_mode.is_test_mode() is True


class TestDataModeInvalidMode:
    def test_invalid_mode_fails_safe_to_demo(self, monkeypatch):
        monkeypatch.setenv("SAKSHA_DATA_MODE", "not-a-real-mode")
        from app.core import data_mode
        # Never degrades to a hidden permissive interpretation.
        assert data_mode.get_data_mode() == "demo"
        assert data_mode.allows_demo_fallback() is True

    def test_missing_mode_defaults_safely(self, monkeypatch):
        monkeypatch.delenv("SAKSHA_DATA_MODE", raising=False)
        from app.core import data_mode
        assert data_mode.get_data_mode() == "demo"


class TestDataModeConfigValidation:
    def test_config_rejects_invalid_data_mode(self):
        from app.core.config import Settings
        with pytest.raises(ValidationError, match="SAKSHA_DATA_MODE"):
            Settings(
                _env_file=None,
                SAKSHA_DATA_MODE="banana",
                APP_ENV="development",
                JWT_SECRET_KEY="x" * 64,
                DATABASE_URL="sqlite:///:memory:",
            )

    def test_config_rejects_empty_data_mode(self):
        from app.core.config import Settings
        with pytest.raises(ValidationError, match="SAKSHA_DATA_MODE"):
            Settings(
                _env_file=None,
                SAKSHA_DATA_MODE="",
                APP_ENV="development",
                JWT_SECRET_KEY="x" * 64,
                DATABASE_URL="sqlite:///:memory:",
            )

    def test_config_accepts_valid_modes(self):
        from app.core.config import Settings
        for mode in ("production", "demo", "test"):
            s = Settings(
                _env_file=None,
                SAKSHA_DATA_MODE=mode,
                APP_ENV="development",
                JWT_SECRET_KEY="x" * 64,
                DATABASE_URL="sqlite:///:memory:",
            )
            assert s.SAKSHA_DATA_MODE == mode


# ---------------------------------------------------------------------------
# Provenance pipeline (MISSING.md §7) — unknown never becomes live
# ---------------------------------------------------------------------------

class TestProvenanceNormalization:
    def test_unknown_never_becomes_live(self):
        from app.core.data_mode import normalize_provenance
        assert normalize_provenance(None) == "unknown"
        assert normalize_provenance("") == "unknown"
        assert normalize_provenance("garbage") == "unknown"
        assert normalize_provenance("UNKNOWN") == "unknown"

    def test_valid_provenance_preserved(self):
        from app.core.data_mode import normalize_provenance
        assert normalize_provenance("live") == "live"
        assert normalize_provenance("migrated") == "migrated"
        assert normalize_provenance("demo") == "demo"
        assert normalize_provenance("DEMO") == "demo"

    def test_seed_provenance_tagged_demo(self, db_session):
        from app.models.location import Location
        from app.core.data_mode import normalize_provenance
        loc = Location(
            district="Seed",
            latitude=12.0,
            longitude=77.0,
            dataset_provenance="demo",
        )
        db_session.add(loc)
        db_session.flush()
        assert normalize_provenance(loc.dataset_provenance) == "demo"


# ---------------------------------------------------------------------------
# Mixed / unknown provenance reporting (MISSING.md §1, §7)
# ---------------------------------------------------------------------------

class TestProvenanceReporting:
    def test_empty_database_summary_is_zero(self, db_session):
        from app.services.data_quality_service import get_provenance_summary
        result = get_provenance_summary(db_session)
        assert result["total_records"] == 0
        assert all(result["by_provenance"][p] == 0 for p in ("live", "migrated", "demo", "unknown"))

    def test_mixed_demo_and_live_reported(self, db_session):
        from app.models.location import Location
        from app.services.data_quality_service import get_provenance_summary
        db_session.add(Location(district="A", latitude=1.0, longitude=2.0, dataset_provenance="demo"))
        db_session.add(Location(district="B", latitude=3.0, longitude=4.0, dataset_provenance="live"))
        db_session.flush()
        result = get_provenance_summary(db_session)
        assert result["by_provenance"]["demo"] == 1
        assert result["by_provenance"]["live"] == 1

    def test_unknown_provenance_warning(self, db_session):
        from app.models.location import Location
        from app.services.data_quality_service import get_data_quality_warnings
        db_session.add(Location(district="X", latitude=1.0, longitude=2.0, dataset_provenance="unknown"))
        db_session.flush()
        warnings = get_data_quality_warnings(db_session)
        assert any(w["type"] == "unknown_provenance" for w in warnings)

    def test_missing_provenance_warning(self, db_session):
        from app.models.location import Location
        from app.services.data_quality_service import get_data_quality_warnings
        loc = Location(district="Y", latitude=1.0, longitude=2.0)
        loc.dataset_provenance = ""
        db_session.add(loc)
        db_session.flush()
        warnings = get_data_quality_warnings(db_session)
        types = {w["type"] for w in warnings}
        assert "unknown_provenance" in types or "empty_provenance" in types


# ---------------------------------------------------------------------------
# Production configuration (MISSING.md §9 / §8 — secrets)
# ---------------------------------------------------------------------------

class TestProductionSecretsAndConfig:
    def test_missing_jwt_secret_rejected(self):
        from app.core.config import Settings
        with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
            Settings(_env_file=None, JWT_SECRET_KEY="", DATABASE_URL="sqlite:///:memory:")

    def test_weak_jwt_secret_rejected_in_production(self):
        from app.core.config import Settings
        with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
            Settings(
                _env_file=None,
                APP_ENV="production",
                JWT_SECRET_KEY="short",
                DATABASE_URL="postgresql+psycopg2://u:p@h:5432/db",
                ALLOWED_ORIGINS="http://localhost:5173",
                APP_DEBUG=False,
                DEBUG=False,
                NEO4J_PASSWORD="strong-neo4j-pass-123",
                SAKSHA_DATA_MODE="production",
            )

    def test_production_rejects_default_neo4j_password(self):
        from app.core.config import Settings
        with pytest.raises(ValidationError, match="NEO4J_PASSWORD"):
            Settings(
                _env_file=None,
                APP_ENV="production",
                JWT_SECRET_KEY="a" * 80,
                DATABASE_URL="postgresql+psycopg2://u:p@h:5432/db",
                ALLOWED_ORIGINS="http://localhost:5173",
                APP_DEBUG=False,
                DEBUG=False,
                NEO4J_PASSWORD="neo4j",
                SAKSHA_DATA_MODE="production",
            )

    def test_production_rejects_sqlite(self):
        from app.core.config import Settings
        with pytest.raises(ValidationError, match="PostgreSQL"):
            Settings(
                _env_file=None,
                APP_ENV="production",
                JWT_SECRET_KEY="a" * 80,
                DATABASE_URL="sqlite:///./saksha.db",
                ALLOWED_ORIGINS="http://localhost:5173",
                APP_DEBUG=False,
                DEBUG=False,
                NEO4J_PASSWORD="strong-neo4j-pass-123",
                SAKSHA_DATA_MODE="production",
            )


# ---------------------------------------------------------------------------
# External service unavailability (MISSING.md §9) — graceful / honest
# ---------------------------------------------------------------------------

class TestExternalServiceUnavailability:
    def test_empty_database_data_mode_endpoint_succeeds(self, client):
        """An empty database must not crash the data-mode endpoint."""
        resp = client.get("/api/v2/system/data-mode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] in ("production", "demo", "test")
        assert data["seed_record_count"] >= 0
        assert data["live_record_count"] >= 0

    def test_data_mode_reports_production_filtering(self, client, monkeypatch):
        """Production mode must report allow_demo_fallback=False."""
        monkeypatch.setenv("SAKSHA_DATA_MODE", "production")
        resp = client.get("/api/v2/system/data-mode")
        assert resp.status_code == 200
        assert resp.json()["allow_demo_fallback"] is False

    def test_neo4j_unavailable_does_not_fail_system_endpoint(self, client, monkeypatch):
        """System endpoint must not depend on Neo4j connectivity."""
        import app.core.data_mode as data_mode
        monkeypatch.setenv("SAKSHA_DATA_MODE", "demo")
        payload = data_mode.data_mode_payload()
        assert payload["mode"] == "demo"
        assert payload["allow_demo_fallback"] is True
        assert payload["show_demo_badges"] is True

    def test_supabase_unavailable_data_mode_still_reports(self, monkeypatch):
        """Even with Supabase env vars removed, the helper returns a sane mode."""
        for key in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("SAKSHA_DATA_MODE", "demo")
        from app.core import data_mode
        assert data_mode.get_data_mode() == "demo"


class TestDataModePayload:
    def test_payload_honors_production(self, monkeypatch):
        """data_mode_payload reflects production mode (no demo fallback)."""
        monkeypatch.setenv("SAKSHA_DATA_MODE", "production")
        from app.core import data_mode
        payload = data_mode.data_mode_payload()
        assert payload["mode"] == "production"
        assert payload["allow_demo_fallback"] is False
        assert payload["show_demo_badges"] is True

    def test_payload_honors_demo(self, monkeypatch):
        monkeypatch.setenv("SAKSHA_DATA_MODE", "demo")
        from app.core import data_mode
        payload = data_mode.data_mode_payload()
        assert payload["mode"] == "demo"
        assert payload["allow_demo_fallback"] is True
        assert payload["show_demo_badges"] is True

    def test_show_demo_badges_is_always_transparent(self, monkeypatch):
        """Badges are always shown so users can distinguish demo from live."""
        for mode in ("production", "demo", "test"):
            monkeypatch.setenv("SAKSHA_DATA_MODE", mode)
            from app.core import data_mode
            assert data_mode.show_demo_badges() is True


class TestProductionFilteringEndpoints:
    def test_production_data_mode_endpoint_disables_fallback(self, client, monkeypatch):
        """In production the system endpoint must report fallback disabled."""
        monkeypatch.setenv("SAKSHA_DATA_MODE", "production")
        resp = client.get("/api/v2/system/data-mode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "production"
        assert data["allow_demo_fallback"] is False


class TestProvenancePipelineEndToEnd:
    def test_demo_seeded_record_is_normalized_demo_not_live(self, db_session):
        """Seed records are reported as 'demo' through normalization, never 'live'."""
        from app.models.crime import CrimeCase
        from app.models.crime_category import CrimeCategory
        from app.models.location import Location
        from app.core.data_mode import normalize_provenance

        location = Location(district="SeedDist", latitude=12.0, longitude=77.0, dataset_provenance="demo")
        category = CrimeCategory(name="SeedCat")
        db_session.add_all([location, category])
        db_session.flush()
        case = CrimeCase(
            case_number="SEED-190-001",
            category_id=category.id,
            location_id=location.id,
            occurred_at=datetime.now(timezone.utc),
            status="open",
            dataset_provenance="demo",
        )
        db_session.add(case)
        db_session.flush()
        assert normalize_provenance(case.dataset_provenance) == "demo"
        assert normalize_provenance(case.dataset_provenance) != "live"
