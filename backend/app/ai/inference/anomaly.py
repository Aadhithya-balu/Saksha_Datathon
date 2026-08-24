from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from app.ai.models.anomaly.model import AnomalyDetectorModel
from app.ai.pipelines.anomaly.pipeline import AnomalyPipeline


DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "anomaly" / "anomaly_model.json"


def _resolve_model_path(model_path: str | None) -> Path:
    if model_path:
        return Path(model_path)
    return DEFAULT_MODEL_PATH


@lru_cache(maxsize=1)
def _load_default_model(model_path: str | None = None) -> AnomalyDetectorModel:
    path = _resolve_model_path(model_path)
    if not path.exists():
        # Create a tiny “safe default” model so endpoint works even without training.
        # Trained mean/std = zeros/ones so score roughly equals L2 norm of input vector.
        feature_names = [
            "day_seconds",
            "lat_norm",
            "lon_norm",
            "district_bucket",
            "crime_bucket",
            "officer_bucket",
            "offender_bucket",
        ]
        model = AnomalyDetectorModel(feature_names=feature_names)
        import numpy as np

        model._mean = np.zeros(len(feature_names), dtype=np.float64)
        model._std = np.ones(len(feature_names), dtype=np.float64)
        model.threshold = 1.8
        return model

    return AnomalyDetectorModel.load_model(path)


def invalidate_caches() -> None:
    """Drop cached artifacts so retrained/promoted models are reloaded (issue #145)."""
    _load_default_model.cache_clear()


def run_anomaly_inference(events: list[dict[str, Any]], *, model_path: str | None = None) -> list[dict[str, Any]]:
    model = _load_default_model(model_path)
    pipeline = AnomalyPipeline(model)
    alerts = pipeline.run(events)
    return [
        {
            "event_id": a.event_id,
            "is_anomaly": a.is_anomaly,
            "score": a.score,
            "threshold": a.threshold,
            "explanation": a.explanation,
        }
        for a in alerts
    ]

