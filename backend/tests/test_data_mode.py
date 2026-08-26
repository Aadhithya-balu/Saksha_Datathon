"""Tests for Issue #162 — Data Mode & Provenance Endpoint.

Validates:
  1. /api/v2/system/data-mode returns correct structure
  2. Production mode disables fallback
  3. Demo mode allows fallback
  4. Provenance counts are returned for each table
  5. Seed record count is non-negative
  6. Live record count is non-negative
  7. Data mode is one of: production, demo, test
  8. show_demo_badges is always True
"""
import os
import pytest


@pytest.fixture(autouse=True)
def _set_data_mode():
    """Ensure data mode is set for tests."""
    os.environ.setdefault("SAKSHA_DATA_MODE", "demo")
    yield
    os.environ.pop("SAKSHA_DATA_MODE", None)


class TestDataModeEndpoint:
    """Tests for GET /api/v2/system/data-mode."""

    def test_data_mode_returns_valid_structure(self, client):
        """Endpoint returns all required fields."""
        resp = client.get("/api/v2/system/data-mode")
        assert resp.status_code == 200
        data = resp.json()
        assert "mode" in data
        assert "allow_demo_fallback" in data
        assert "show_demo_badges" in data
        assert "provenance" in data
        assert "seed_record_count" in data
        assert "live_record_count" in data

    def test_data_mode_is_valid_value(self, client):
        """Mode must be one of: production, demo, test."""
        resp = client.get("/api/v2/system/data-mode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] in ("production", "demo", "test")

    def test_demo_mode_allows_fallback(self, client):
        """In demo mode, allow_demo_fallback is True."""
        resp = client.get("/api/v2/system/data-mode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["allow_demo_fallback"] is True

    def test_production_mode_disables_fallback(self, client, monkeypatch):
        """In production mode, allow_demo_fallback is False."""
        monkeypatch.setenv("SAKSHA_DATA_MODE", "production")
        resp = client.get("/api/v2/system/data-mode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["allow_demo_fallback"] is False

    def test_provenance_has_all_tables(self, client):
        """Provenance includes all monitored tables."""
        resp = client.get("/api/v2/system/data-mode")
        assert resp.status_code == 200
        data = resp.json()
        expected_tables = ["crime_cases", "criminals", "firs", "locations", "officers", "victims"]
        for table in expected_tables:
            assert table in data["provenance"], f"Missing provenance for {table}"

    def test_counts_are_non_negative(self, client):
        """Seed and live record counts are non-negative integers."""
        resp = client.get("/api/v2/system/data-mode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["seed_record_count"] >= 0
        assert data["live_record_count"] >= 0

    def test_show_demo_badges_always_true(self, client):
        """Demo badges are always shown for transparency."""
        resp = client.get("/api/v2/system/data-mode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["show_demo_badges"] is True

    def test_test_mode_disables_fallback(self, client, monkeypatch):
        """In test mode, allow_demo_fallback is False."""
        monkeypatch.setenv("SAKSHA_DATA_MODE", "test")
        resp = client.get("/api/v2/system/data-mode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["allow_demo_fallback"] is False
