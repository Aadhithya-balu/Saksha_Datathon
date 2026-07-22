import pytest

pytest.importorskip("lightgbm", reason="lightgbm not installed")

from app.ai.inference.hotspot import predict


def test_predict_accepts_single_record_payload():
    payload = [
        {
            "CaseMasterID": 1,
            "IncidentFromDate": "2025-05-15 21:30:00",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "PoliceStationID": 10,
            "GravityOffenceID": 2,
            "CrimeMajorHeadID": 5,
        }
    ]

    results = predict(payload)

    assert len(results) >= 1
    assert results[0]["h3_cell"]
    assert results[0]["predicted_crime_count"] >= 0
    assert results[0]["risk_level"] in {"Low", "Medium", "High", "Critical"}
