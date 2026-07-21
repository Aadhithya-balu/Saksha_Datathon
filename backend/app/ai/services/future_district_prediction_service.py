from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any
import warnings

import joblib
import pandas as pd

from app.core.logging_config import logger
from app.schemas.future_district_prediction import FutureDistrictRiskRequest


MODEL_NAME = "Random Forest Regressor"
MODEL_METRICS = {
    "r2": 0.9534,
    "mae": 1608.07,
    "rmse": 4928.44,
}
FEATURE_COLUMNS = [
    "DISTRICT",
    "YEAR",
    "VIOLENT_CRIME",
    "PROPERTY_CRIME",
    "WOMEN_CRIME",
    "PREVIOUS_YEAR_CRIME",
    "CRIME_GROWTH",
    "ROLLING_AVG",
]
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "futuredistrict" / "risk_model_adv.joblib"


class FutureDistrictModelMissingError(Exception):
    pass


class FutureDistrictPredictionError(Exception):
    pass


_model: Any | None = None
_model_lock = Lock()


def _install_sklearn_compatibility_shim() -> None:
    try:
        import sklearn.compose._column_transformer as column_transformer
    except Exception:
        return

    if not hasattr(column_transformer, "_RemainderColsList"):
        class _RemainderColsList(list):
            pass

        column_transformer._RemainderColsList = _RemainderColsList


def get_model() -> Any:
    global _model

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        if not MODEL_PATH.exists():
            logger.error(f"Future district risk model missing at {MODEL_PATH}")
            raise FutureDistrictModelMissingError("Future district risk model is not available")

        try:
            _install_sklearn_compatibility_shim()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                _model = joblib.load(MODEL_PATH)
            logger.info(f"Future district risk model loaded from {MODEL_PATH}")
            return _model
        except Exception as exc:
            logger.exception(f"Failed to load future district risk model: {exc}")
            raise FutureDistrictPredictionError("Unable to load future district risk model") from exc


def _risk_level(predicted_count: float) -> str:
    if predicted_count < 1000:
        return "LOW"
    if predicted_count <= 5000:
        return "MEDIUM"
    if predicted_count <= 10000:
        return "HIGH"
    return "VERY_HIGH"


def _to_feature_frame(payload: FutureDistrictRiskRequest) -> pd.DataFrame:
    row = payload.model_dump(by_alias=True)
    return pd.DataFrame([{column: row[column] for column in FEATURE_COLUMNS}], columns=FEATURE_COLUMNS)


def get_trained_districts() -> list[str]:
    try:
        model = get_model()
        preprocessor = model.named_steps["preprocessor"]

        for name, transformer, columns in preprocessor.transformers_:
            if "DISTRICT" not in columns:
                continue
            for _, step in getattr(transformer, "steps", []):
                if type(step).__name__ == "OneHotEncoder":
                    return [str(category) for category in step.categories_[0]]
    except FutureDistrictModelMissingError:
        logger.exception("Future district risk districts lookup failure: missing model")
        raise
    except Exception as exc:
        logger.exception(f"Future district risk districts lookup failure: {exc}")
        raise FutureDistrictPredictionError("Unable to read trained district names") from exc

    raise FutureDistrictPredictionError("Trained district names are not available")


def predict_future_district_risk(payload: FutureDistrictRiskRequest) -> dict[str, Any]:
    logger.info(f"Future district risk prediction request for district={payload.district}, year={payload.year}")

    try:
        model = get_model()
        features = _to_feature_frame(payload)
        prediction = model.predict(features)
        predicted_count = max(float(prediction[0]), 0.0)
        rounded_prediction = round(predicted_count)

        response = {
            "predicted_crime_count": rounded_prediction,
            "risk_level": _risk_level(predicted_count),
            "model": MODEL_NAME,
            "metrics": MODEL_METRICS,
        }
        logger.info(
            "Future district risk prediction completed "
            f"district={payload.district}, year={payload.year}, predicted={rounded_prediction}"
        )
        return response
    except FutureDistrictModelMissingError:
        logger.exception("Future district risk prediction failure: missing model")
        raise
    except FutureDistrictPredictionError:
        logger.exception("Future district risk prediction failure")
        raise
    except Exception as exc:
        logger.exception(f"Future district risk prediction failure: {exc}")
        raise FutureDistrictPredictionError("Future district risk prediction failed") from exc
