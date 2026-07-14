from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Iterable


@dataclass(frozen=True)
class DriftReport:
    feature_name: str
    baseline_mean: float
    current_mean: float
    absolute_shift: float
    drift_detected: bool


def compare_distributions(
    baseline: Iterable[dict[str, Any]],
    current: Iterable[dict[str, Any]],
    *,
    feature_name: str,
    threshold: float = 0.15,
) -> DriftReport:
    base_values = [float(row.get(feature_name, 0.0)) for row in baseline]
    current_values = [float(row.get(feature_name, 0.0)) for row in current]
    baseline_mean = mean(base_values) if base_values else 0.0
    current_mean = mean(current_values) if current_values else 0.0
    shift = abs(current_mean - baseline_mean)
    return DriftReport(
        feature_name=feature_name,
        baseline_mean=baseline_mean,
        current_mean=current_mean,
        absolute_shift=shift,
        drift_detected=shift >= threshold,
    )
