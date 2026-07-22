from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from app.ai.features.anomaly.feature_engineering import build_anomaly_features
from app.ai.models.anomaly.model import AnomalyDetectorModel


@dataclass(frozen=True)
class AnomalyAlert:
    event_id: str | None
    is_anomaly: bool
    score: float
    threshold: float
    explanation: dict[str, Any]


class AnomalyPipeline:
    def __init__(self, model: AnomalyDetectorModel):
        self.model = model

    def run(self, events: list[dict[str, Any]]) -> list[AnomalyAlert]:
        if not events:
            return []

        alerts: list[AnomalyAlert] = []
        for ev in events:
            fv = build_anomaly_features(ev)
            pred = self.model.predict(fv.values)
            alerts.append(
                AnomalyAlert(
                    event_id=ev.get("event_id") or ev.get("id"),
                    is_anomaly=pred.is_anomaly,
                    score=pred.score,
                    threshold=pred.threshold,
                    explanation={
                        "top_features": pred.explanation.top_features,
                        "score": pred.explanation.score,
                        "threshold": pred.explanation.threshold,
                        "is_anomaly": pred.explanation.is_anomaly,
                    },
                )
            )
        return alerts

    @staticmethod
    def train_from_events(model: AnomalyDetectorModel, events: list[dict[str, Any]], y_true: list[bool] | None = None) -> dict[str, float]:
        X = np.vstack([build_anomaly_features(ev).values for ev in events])
        if y_true is None:
            model.train(X)
            return model.evaluate(X, None)
        model.train(X)
        return model.evaluate(X, np.asarray(y_true, dtype=bool))

