from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .registry import ModelArtifact, ModelRegistry


@dataclass(frozen=True)
class DeploymentPlan:
    model_name: str
    source_version: str
    target_stage: str
    artifact_path: str
    rollback_version: str | None


def build_deployment_plan(registry: ModelRegistry, model_name: str, target_stage: str = "production") -> DeploymentPlan:
    latest = registry.latest(model_name)
    if latest is None:
        raise FileNotFoundError(f"No registry artifact found for {model_name}")
    previous = _previous_version(registry, model_name, latest.version)
    return DeploymentPlan(
        model_name=model_name,
        source_version=latest.version,
        target_stage=target_stage,
        artifact_path=latest.artifact_path,
        rollback_version=previous.version if previous else None,
    )


def rollback_release(registry: ModelRegistry, model_name: str, version: str) -> ModelArtifact:
    return registry.promote(model_name, version, "production")


def _previous_version(registry: ModelRegistry, model_name: str, current_version: str) -> ModelArtifact | None:
    records = registry.list_models().get(model_name, [])
    previous = None
    for record in records:
        if record.version == current_version:
            return previous
        previous = record
    return previous
