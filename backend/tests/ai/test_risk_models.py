"""
Unit tests for the District Risk & Forecast ML pipeline.

Tests cover:
- Feature engineering (risk + forecast)
- DistrictRiskModel  (train / evaluate / predict / save / load)
- DistrictForecastModel (train / evaluate / predict / save / load)
- Inference layer (predict_risk / predict_forecast with fallback)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_records(n: int = 60) -> list[dict]:
    """Generate synthetic crime records spanning multiple districts and months."""
    rng = np.random.default_rng(0)
    districts = ["Bengaluru Urban", "Mysuru", "Belagavi"]
    categories = ["Cybercrime", "Robbery", "Fraud"]
    records = []
    for i in range(n):
        month = (i % 12) + 1
        year = 2024 + i // 12
        records.append({
            "occurred_at": f"{year}-{month:02d}-{rng.integers(1, 28):02d}T{rng.integers(0, 23):02d}:00:00",
            "district": districts[i % len(districts)],
            "category": categories[i % len(categories)],
        })
    return records


@pytest.fixture
def sample_records():
    return _make_records(90)


@pytest.fixture
def risk_feature_df(sample_records):
    from app.ai.features.risk.feature_engineering import build_risk_features
    return build_risk_features(pd.DataFrame(sample_records), include_target=True)


@pytest.fixture
def forecast_feature_df(sample_records):
    from app.ai.features.risk.feature_engineering import build_forecast_features
    return build_forecast_features(pd.DataFrame(sample_records), include_target=True)


# ---------------------------------------------------------------------------
# Feature engineering tests
# ---------------------------------------------------------------------------

class TestFeatureEngineering:
    def test_risk_features_shape(self, risk_feature_df):
        from app.ai.features.risk.feature_engineering import RISK_FEATURE_COLUMNS
        assert not risk_feature_df.empty
        for col in RISK_FEATURE_COLUMNS:
            assert col in risk_feature_df.columns, f"Missing column: {col}"

    def test_forecast_features_shape(self, forecast_feature_df):
        from app.ai.features.risk.feature_engineering import FORECAST_FEATURE_COLUMNS
        assert not forecast_feature_df.empty
        for col in FORECAST_FEATURE_COLUMNS:
            assert col in forecast_feature_df.columns, f"Missing column: {col}"

    def test_no_nulls_in_features(self, risk_feature_df):
        from app.ai.features.risk.feature_engineering import RISK_FEATURE_COLUMNS
        assert risk_feature_df[RISK_FEATURE_COLUMNS].isnull().sum().sum() == 0

    def test_missing_required_column_raises(self):
        from app.ai.features.risk.feature_engineering import build_risk_features
        bad_df = pd.DataFrame({"occurred_at": ["2024-01-01"], "district": ["X"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            build_risk_features(bad_df)

    def test_empty_dataframe_raises(self):
        from app.ai.features.risk.feature_engineering import build_risk_features
        with pytest.raises(ValueError):
            build_risk_features(pd.DataFrame())


# ---------------------------------------------------------------------------
# DistrictRiskModel tests
# ---------------------------------------------------------------------------

class TestDistrictRiskModel:
    def test_train_evaluate_predict(self, risk_feature_df):
        _sklearn = pytest.importorskip("sklearn", reason="scikit-learn not installed")  # noqa: F841 ensures skip when missing
        from app.ai.features.risk.feature_engineering import RISK_FEATURE_COLUMNS
        from app.ai.models.risk.risk_model import DistrictRiskModel

        X = risk_feature_df[RISK_FEATURE_COLUMNS].values
        y = risk_feature_df["TargetRiskScore"].values

        model = DistrictRiskModel(feature_names=RISK_FEATURE_COLUMNS)
        model.train(X, y)

        metrics = model.evaluate(X, y)
        assert "rmse" in metrics and "mae" in metrics and "r2" in metrics
        assert metrics["rmse"] >= 0

        pred = model.predict(X[0], district="Bengaluru Urban", year_month="2024-01")
        assert 0.0 <= pred.risk_score <= 100.0
        assert pred.risk_band in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert 0.0 <= pred.confidence <= 1.0

    def test_predict_before_train_raises(self):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        from app.ai.features.risk.feature_engineering import RISK_FEATURE_COLUMNS
        from app.ai.models.risk.risk_model import DistrictRiskModel

        model = DistrictRiskModel(feature_names=RISK_FEATURE_COLUMNS)
        with pytest.raises(RuntimeError):
            model.predict(np.zeros(len(RISK_FEATURE_COLUMNS)))

    def test_save_load_roundtrip(self, risk_feature_df):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        from app.ai.features.risk.feature_engineering import RISK_FEATURE_COLUMNS
        from app.ai.models.risk.risk_model import DistrictRiskModel

        X = risk_feature_df[RISK_FEATURE_COLUMNS].values
        y = risk_feature_df["TargetRiskScore"].values

        model = DistrictRiskModel(feature_names=RISK_FEATURE_COLUMNS)
        model.train(X, y)
        original_pred = model.predict(X[0]).risk_score

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "risk_model.pkl"
            model.save_model(path)
            loaded = DistrictRiskModel.load_model(path)

        loaded_pred = loaded.predict(X[0]).risk_score
        assert abs(original_pred - loaded_pred) < 1e-4


# ---------------------------------------------------------------------------
# DistrictForecastModel tests
# ---------------------------------------------------------------------------

class TestDistrictForecastModel:
    @staticmethod
    def _skip_if_no_boosting_lib():
        import importlib
        has_xgb = importlib.util.find_spec("xgboost") is not None
        has_lgb = importlib.util.find_spec("lightgbm") is not None
        if not has_xgb and not has_lgb:
            pytest.skip("Neither xgboost nor lightgbm is installed")

    def test_train_evaluate_predict(self, forecast_feature_df):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        self._skip_if_no_boosting_lib()
        from app.ai.features.risk.feature_engineering import FORECAST_FEATURE_COLUMNS
        from app.ai.models.risk.forecast_model import DistrictForecastModel

        X = forecast_feature_df[FORECAST_FEATURE_COLUMNS].values
        y = forecast_feature_df["TargetCrimeCount"].values

        model = DistrictForecastModel(feature_names=FORECAST_FEATURE_COLUMNS)
        model.train(X, y)

        metrics = model.evaluate(X, y)
        assert "rmse" in metrics and "r2" in metrics
        assert metrics["rmse"] >= 0

        point = model.predict(X[0], district="Mysuru", year_month="2024-06", lag1=5.0)
        assert point.predicted_crime_count >= 0
        assert point.lower_bound <= point.predicted_crime_count <= point.upper_bound
        assert point.trend in {"up", "stable", "down"}

    def test_save_load_roundtrip(self, forecast_feature_df):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        self._skip_if_no_boosting_lib()
        from app.ai.features.risk.feature_engineering import FORECAST_FEATURE_COLUMNS
        from app.ai.models.risk.forecast_model import DistrictForecastModel

        X = forecast_feature_df[FORECAST_FEATURE_COLUMNS].values
        y = forecast_feature_df["TargetCrimeCount"].values

        model = DistrictForecastModel(feature_names=FORECAST_FEATURE_COLUMNS)
        model.train(X, y)
        original = model.predict(X[0]).predicted_crime_count

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "forecast_model.pkl"
            model.save_model(path)
            loaded = DistrictForecastModel.load_model(path)

        loaded_pred = loaded.predict(X[0]).predicted_crime_count
        assert abs(original - loaded_pred) < 1e-4


# ---------------------------------------------------------------------------
# Inference layer tests (fallback path — no trained model on disk)
# ---------------------------------------------------------------------------

class TestInferenceFallback:
    def test_predict_risk_fallback(self, sample_records):
        """predict_risk must work without a trained model via rule-based fallback."""
        from app.ai.inference.risk import predict_risk

        results = predict_risk(sample_records)
        assert len(results) > 0
        for r in results:
            assert "district" in r
            assert 0.0 <= r["risk_score"] <= 100.0
            assert r["risk_band"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
            assert "resource_recommendation" in r

    def test_predict_forecast_fallback(self, sample_records):
        """predict_forecast must work without a trained model."""
        from app.ai.inference.risk import predict_forecast

        results = predict_forecast(sample_records)
        assert len(results) > 0
        for r in results:
            assert "district" in r
            assert r["predicted_crime_count"] >= 0
            assert r["lower_bound"] <= r["predicted_crime_count"] <= r["upper_bound"]

    def test_predict_risk_empty_raises(self):
        from app.ai.inference.risk import predict_risk
        with pytest.raises(ValueError):
            predict_risk([])

    def test_predict_forecast_empty_raises(self):
        from app.ai.inference.risk import predict_forecast
        with pytest.raises(ValueError):
            predict_forecast([])

    def test_get_model_info_returns_dict(self):
        from app.ai.inference.risk import get_model_info
        info = get_model_info()
        assert isinstance(info, dict)
        assert "model_name" in info
        assert "risk_model_loaded" in info

