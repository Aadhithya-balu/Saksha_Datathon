"""Scenarios 5, 7 acceptance: hotspot intelligence flow + failure honesty.

Also covers issue 8 §15 model-artifact behaviour at API level:
valid / missing / invalid artifacts and feature-schema mismatch.
"""
import joblib
import pytest

pytestmark = pytest.mark.acceptance

PREDICT = "/api/v2/ai/hotspot/predict"
MODEL_INFO = "/api/v2/ai/hotspot/model-info"
HEALTH = "/api/v2/ai/hotspot/health"


def _records():
    return [
        {
            "CaseMasterID": f"ACC-{i:04d}",
            "IncidentFromDate": "2026-06-10T22:30:00",
            "latitude": 12.96 + i * 0.001,
            "longitude": 77.72 + i * 0.001,
            "PoliceStationID": "PS-ACC-1",
            "GravityOffenceID": 1,
            "CrimeMajorHeadID": "THEFT",
        }
        for i in range(6)
    ]


@pytest.fixture
def isolated_hotspot_model_dir(monkeypatch, tmp_path):
    """Point the hotspot inference module at an empty temp artifact dir."""
    from app.ai.inference import hotspot as hotspot_module

    empty_dir = tmp_path / "hotspot-models"
    empty_dir.mkdir()
    monkeypatch.setattr(hotspot_module, "MODEL_DIR", empty_dir)
    hotspot_module.invalidate_caches()
    yield empty_dir
    hotspot_module.invalidate_caches()


@pytest.fixture
def tolerant_client(db_session):
    """TestClient that surfaces server-side error HANDLERS instead of raising.

    Used where an intentionally corrupt artifact must exercise the app's
    real exception-handling path.
    """
    from fastapi.testclient import TestClient

    from app.database.postgres import get_db
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_hotspot_flow_returns_predictions_with_honest_mode(client, analyst_headers):
    r = client.post(PREDICT, json={"records": _records()}, headers=analyst_headers)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["total"] == len(body["predictions"]) >= 1
    for pred in body["predictions"]:
        assert {"h3_cell", "year_month", "predicted_crime_count", "risk_level", "confidence_score"} <= set(pred)
        assert pred["risk_level"] in ("Low", "Medium", "High", "Critical")
        assert 0.0 <= pred["confidence_score"] <= 1.0

    # Scenario 5/§32: mode must be declared AND consistent with model reality.
    info = client.get(MODEL_INFO, headers=analyst_headers).json()
    expected_mode = "ML" if info.get("model_loaded") else "FALLBACK"
    assert body["prediction_mode"] == expected_mode
    if expected_mode == "FALLBACK":
        assert body["model_version"] in (None, "untrained")


def test_hotspot_predict_requires_authentication(client):
    assert client.post(PREDICT, json={"records": _records()}).status_code == 401


def test_hotspot_invalid_payload_controlled_error(client, analyst_headers):
    missing_fields = [{"CaseMasterID": "X-1"}]
    r = client.post(PREDICT, json={"records": missing_fields}, headers=analyst_headers)
    assert r.status_code == 422
    detail = str(r.json())
    assert "Traceback" not in detail
    assert not r.json().get("predictions")  # no fabricated hotspot data


def test_hotspot_empty_records_rejected(client, analyst_headers):
    r = client.post(PREDICT, json={"records": []}, headers=analyst_headers)
    assert r.status_code == 422


def test_missing_model_artifact_reports_unavailable_never_claims_ml(
    client, analyst_headers, isolated_hotspot_model_dir
):
    """Scenario 7: no artifact -> FALLBACK/UNAVAILABLE status, no false ML claim."""
    info_r = client.get(MODEL_INFO, headers=analyst_headers)
    assert info_r.status_code == 200
    info = info_r.json()
    assert info["model_loaded"] is False
    assert info["version"] == "untrained"

    health = client.get(HEALTH, headers=analyst_headers).json()
    assert health["status"] == "ok"  # service alive...
    assert health["model"] == "SAKSHA Hotspot Predictor"  # ...but metadata honest

    predict = client.post(PREDICT, json={"records": _records()}, headers=analyst_headers)
    assert predict.status_code == 200
    body = predict.json()
    assert body["prediction_mode"] == "FALLBACK", (
        "system must not claim ML inference without a trained artifact"
    )


def test_invalid_model_artifact_does_not_silently_continue_as_ml(
    tolerant_client, db_session, isolated_hotspot_model_dir
):
    """A corrupt artifact must never be presented as validated ML inference."""
    from tests.acceptance.conftest import auth_headers

    (isolated_hotspot_model_dir / "hotspot_model.pkl").write_bytes(b"not-a-real-pickle")
    headers = auth_headers(tolerant_client, db_session, "acc-hotspot-invalid", "crime_analyst")

    info_r = tolerant_client.get(MODEL_INFO, headers=headers)
    # Controlled error (500 JSON via the app's exception handler), never a
    # fabricated 'loaded' claim.
    assert info_r.status_code >= 400
    assert "Traceback" not in info_r.text

    predict = tolerant_client.post(PREDICT, json={"records": _records()}, headers=headers)
    assert predict.status_code in (422, 503)


def test_feature_schema_mismatch_rejects_prediction(
    client, analyst_headers, isolated_hotspot_model_dir
):
    """Artifact whose feature columns don't match engineered features must be
    rejected, not silently scored or silently treated as fallback success."""
    from sklearn.linear_model import LinearRegression

    model = LinearRegression().fit([[0.0], [1.0]], [0.0, 1.0])
    joblib.dump(model, isolated_hotspot_model_dir / "hotspot_model.pkl")
    (isolated_hotspot_model_dir / "feature_columns.json").write_text(
        '["NotARealFeatureColumn"]', encoding="utf-8"
    )

    predict = client.post(PREDICT, json={"records": _records()}, headers=analyst_headers)
    assert predict.status_code == 422
