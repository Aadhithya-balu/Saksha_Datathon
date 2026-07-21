from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .drift import DriftReport, compare_distributions


@dataclass(frozen=True)
class MonitoringSnapshot:
    model_name: str
    dataset_version: str
    timestamp: str
    metrics: dict[str, Any]
    drift: list[DriftReport]


class ModelMonitor:
    def __init__(self, root: str | Path = "monitoring") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def record(self, model_name: str, dataset_version: str, metrics: dict[str, Any], drift: list[DriftReport]) -> MonitoringSnapshot:
        snapshot = MonitoringSnapshot(
            model_name=model_name,
            dataset_version=dataset_version,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metrics=metrics,
            drift=drift,
        )
        out = self.root / f"{model_name}-latest.json"
        out.write_text(json.dumps({
            **asdict(snapshot),
            "drift": [asdict(item) for item in drift],
        }, indent=2), encoding="utf-8")
        return snapshot

    def needs_retraining(self, snapshot: MonitoringSnapshot) -> bool:
        return any(item.drift_detected for item in snapshot.drift)
