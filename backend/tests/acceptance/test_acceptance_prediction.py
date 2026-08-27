"""Scenario 6 + 7 acceptance: predictive intelligence honesty.

Verifies the risk/forecast endpoints authenticate, validate, and — critically —
declare whether results came from a trained ML model or rule-based fallback.
"""
import pytest

pytestmark = pytest.mark.acceptance

RISK_GET = "/api/v2/ai/predictions/risk-scores"
RISK_POST = "/api/v2/ai/predictions/risk-scores"
FORECAST = "/api/v2/ai/predictions/forecast"
MODEL_INFO = "/api/v2/ai/predictions/model-info"
HEALTH = "/api/v2/ai/predictions/health"


def _records():
    return [
        {"occurred_at": "2026-06-10T22:30:00", "district": "Bengaluru Urban", "category": "Theft & Burglaries"},
        {"occurred_at": "2026-06-11T23:30:00", "district": "Bengaluru Urban", "category": "Assault"},
        {"occurred_at": "2026-06-12T21:00:00", "district": "Mysuru", "category": "Theft & Burglaries"},
    ]


def test_risk_scores_from_seeded_db(client, crime_dataset, analyst_headers):
    """GET /risk-scores must use real DB records (3 seeded cases)."""
    r = client.get(RISK_GET, headers=analyst_headers)
    assert r.status_code == 200, r.text
    body = r.json()

    # Response contract.
    for key in ("window", "model_version", "grid_predictions", "prediction_mode", "data_provenance"):
        assert key in body
    # §33 DB-backed: provenance must honestly reflect live operational records.
    # The fixture deliberately includes one demo-provenance case, so LIVE_DB must
    # be present (it may legitimately combine to "LIVE_DB + DEMO").
    assert "LIVE_DB" in body["data_provenance"]

    # DB-backed: districts from the fixture appear among predictions.
    districts = {p["district"] for p in body["grid_predictions"]}
    assert {"Bengaluru Urban", "Mysuru"} <= districts
    for pred in body["grid_predictions"]:
        assert {"district", "year_month", "risk_score", "risk_band", "confidence"} <= set(pred)
        assert 0.0 <= pred["risk_score"] <= 100.0

    # §14/§32: mode must be an honest declared value.
    assert body["prediction_mode"] in ("ML", "FALLBACK")


def test_prediction_mode_matches_model_info(client, crime_dataset, analyst_headers):
    info = client.get(MODEL_INFO, headers=analyst_headers)
    assert info.status_code == 200
    scores = client.get(RISK_GET, headers=analyst_headers)
    if scores.status_code == 503:
        pytest.skip("risk service unavailable in this environment")
    body = scores.json()
    if not body["grid_predictions"]:
        assert body["prediction_mode"] == "UNAVAILABLE"
        return
    loaded = bool(info.json().get("risk_model_loaded"))
    expected = "ML" if loaded else "FALLBACK"
    assert body["prediction_mode"] == expected, (
        f"prediction_mode={body['prediction_mode']} but risk_model_loaded={loaded}"
    )


def test_post_risk_scores_validates_and_declares_mode(client, analyst_headers):
    r = client.post(RISK_POST, json={"records": _records()}, headers=analyst_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["grid_predictions"]
    assert body["prediction_mode"] in ("ML", "FALLBACK")
    districts = {p["district"] for p in body["grid_predictions"]}
    assert "Bengaluru Urban" in districts


def test_forecast_returns_bounded_predictions(client, analyst_headers):
    r = client.post(FORECAST, json={"records": _records()}, headers=analyst_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == len(body["forecasts"]) >= 1
    for item in body["forecasts"]:
        assert {"district", "year_month", "predicted_crime_count", "lower_bound", "upper_bound", "trend"} <= set(item)
        assert item["lower_bound"] <= item["predicted_crime_count"] <= item["upper_bound"]


def test_forecast_invalid_records_controlled_422(client, analyst_headers):
    r = client.post(FORECAST, json={"records": [{"nonsense": True}]}, headers=analyst_headers)
    assert r.status_code == 422
    assert "Traceback" not in r.text


def test_prediction_endpoints_require_authentication(client):
    assert client.get(RISK_GET).status_code == 401
    assert client.post(RISK_POST, json={"records": _records()}).status_code == 401
    assert client.post(FORECAST, json={"records": _records()}).status_code == 401


def test_model_training_is_admin_only(client, db_session, analyst_headers):
    r = client.post("/api/v2/ai/predictions/train", headers=analyst_headers)
    assert r.status_code == 403


def test_health_reports_model_load_honestly(client, analyst_headers):
    r = client.get(HEALTH, headers=analyst_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "unavailable")
    if body["status"] == "ok":
        assert isinstance(body["risk_model"], bool)
