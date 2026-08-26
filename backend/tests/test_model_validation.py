"""Tests for Issue #165: ML Model Artifact/Schema/Training Validation."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestModelValidationService:
    """Tests for app.services.model_validation_service."""

    def test_check_artifact_exists_valid(self, tmp_path):
        from app.services.model_validation_service import _check_artifact_exists
        p = tmp_path / "model.pkl"
        p.write_bytes(b"fake-model-data")
        result = _check_artifact_exists(p, "test_model")
        assert result["valid"] is True
        assert result["size_bytes"] == len(b"fake-model-data")

    def test_check_artifact_missing(self, tmp_path):
        from app.services.model_validation_service import _check_artifact_exists
        p = tmp_path / "nonexistent.pkl"
        result = _check_artifact_exists(p, "test_model")
        assert result["valid"] is False
        assert "not found" in result["error"]

    def test_check_artifact_empty(self, tmp_path):
        from app.services.model_validation_service import _check_artifact_exists
        p = tmp_path / "empty.pkl"
        p.write_bytes(b"")
        result = _check_artifact_exists(p, "test_model")
        assert result["valid"] is False
        assert "empty" in result["error"]

    def test_validate_json_artifact_valid(self, tmp_path):
        from app.services.model_validation_service import _validate_json_artifact
        p = tmp_path / "meta.json"
        p.write_text(json.dumps({"model_name": "test"}), encoding="utf-8")
        result = _validate_json_artifact(p, "metadata")
        assert result["valid"] is True
        assert result["data"]["model_name"] == "test"

    def test_validate_json_artifact_invalid_json(self, tmp_path):
        from app.services.model_validation_service import _validate_json_artifact
        p = tmp_path / "bad.json"
        p.write_text("not-json", encoding="utf-8")
        result = _validate_json_artifact(p, "metadata")
        assert result["valid"] is False
        assert "not valid JSON" in result["error"]

    def test_validate_hotspot_model_no_artifacts(self, tmp_path):
        from app.services.model_validation_service import validate_hotspot_model
        result = validate_hotspot_model(tmp_path)
        assert result["model"] == "hotspot"
        assert result["overall_status"] == "INVALID"
        assert result["model_loaded"] is False

    def test_validate_hotspot_model_all_artifacts(self, tmp_path):
        from app.services.model_validation_service import validate_hotspot_model
        # Create all required artifacts
        (tmp_path / "hotspot_model.pkl").write_bytes(b"fake-model")
        (tmp_path / "model_metadata.json").write_text(
            json.dumps({
                "model_name": "Test Hotspot",
                "algorithm": "LightGBM",
                "h3_resolution": 7,
                "trained_on": "2026-01-01",
            }),
            encoding="utf-8",
        )
        (tmp_path / "feature_columns.json").write_text(
            json.dumps(["feature1", "feature2", "feature3"]),
            encoding="utf-8",
        )
        (tmp_path / "training_metrics.json").write_text(
            json.dumps({"rmse": 0.5, "mae": 0.3, "r2": 0.8}),
            encoding="utf-8",
        )
        result = validate_hotspot_model(tmp_path)
        assert result["overall_status"] == "VALID"
        assert result["model_loaded"] is True

    def test_validate_risk_model_no_artifacts(self, tmp_path):
        from app.services.model_validation_service import validate_risk_model
        result = validate_risk_model(tmp_path)
        assert result["model"] == "risk"
        assert result["overall_status"] == "INVALID"
        assert result["risk_model_loaded"] is False
        assert result["forecast_model_loaded"] is False

    def test_validate_risk_model_partial(self, tmp_path):
        from app.services.model_validation_service import validate_risk_model
        # Only risk model present
        (tmp_path / "risk_model.pkl").write_bytes(b"fake-risk")
        (tmp_path / "model_metadata.json").write_text(
            json.dumps({
                "model_name": "Test Risk",
                "risk_algorithm": "RandomForest",
                "forecast_algorithm": "XGBoost",
                "trained_on": "2026-01-01",
            }),
            encoding="utf-8",
        )
        (tmp_path / "training_metrics.json").write_text(
            json.dumps({"risk": {"mae": 1.2}, "forecast": {"mae": 0.9}}),
            encoding="utf-8",
        )
        result = validate_risk_model(tmp_path)
        assert result["risk_model_loaded"] is True
        assert result["forecast_model_loaded"] is False

    def test_validate_risk_model_metadata_missing_keys(self, tmp_path):
        from app.services.model_validation_service import validate_risk_model
        (tmp_path / "model_metadata.json").write_text(
            json.dumps({"model_name": "Incomplete"}),
            encoding="utf-8",
        )
        result = validate_risk_model(tmp_path)
        meta_check = [c for c in result["checks"] if c.get("artifact") == "metadata_completeness"]
        assert len(meta_check) == 1
        assert meta_check[0]["valid"] is False

    def test_feature_schema_empty_list(self, tmp_path):
        from app.services.model_validation_service import validate_hotspot_model
        (tmp_path / "feature_columns.json").write_text(json.dumps([]), encoding="utf-8")
        result = validate_hotspot_model(tmp_path)
        schema_check = [c for c in result["checks"] if c.get("artifact") == "feature_schema"]
        assert len(schema_check) == 1
        assert schema_check[0]["valid"] is False


class TestGetAllModelHealth:
    def test_returns_structure(self):
        from app.services.model_validation_service import get_all_model_health
        result = get_all_model_health()
        assert "hotspot" in result
        assert "risk" in result
        assert "overall_status" in result
        assert result["overall_status"] in ("VALID", "DEGRADED")
