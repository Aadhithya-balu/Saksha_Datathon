from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelArtifact:
    model_name: str
    version: str
    artifact_path: str
    metrics_path: str | None
    dataset_version: str
    stage: str
    created_at: str
    metadata: dict[str, Any]


class ModelRegistry:
    """Filesystem-backed registry with MLflow-compatible metadata layout."""

    def __init__(self, root: str | Path = "mlflow") -> None:
        self.root = Path(root)
        self.registry_dir = self.root / "registry"
        self.manifest_path = self.registry_dir / "models.json"
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def register(
        self,
        model_name: str,
        artifact_path: str | Path,
        *,
        dataset_version: str,
        metrics_path: str | Path | None = None,
        stage: str = "staging",
        metadata: dict[str, Any] | None = None,
    ) -> ModelArtifact:
        artifact = ModelArtifact(
            model_name=model_name,
            version=self._next_version(model_name),
            artifact_path=str(Path(artifact_path)),
            metrics_path=str(Path(metrics_path)) if metrics_path else None,
            dataset_version=dataset_version,
            stage=stage,
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        manifest = self._load_manifest()
        manifest.setdefault(model_name, []).append(asdict(artifact))
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return artifact

    def promote(self, model_name: str, version: str, stage: str) -> ModelArtifact:
        manifest = self._load_manifest()
        records = manifest.get(model_name, [])
        for record in records:
            if record["version"] == version:
                record["stage"] = stage
                self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                return ModelArtifact(**record)
        raise KeyError(f"Model {model_name!r} version {version!r} not found")

    def latest(self, model_name: str) -> ModelArtifact | None:
        records = self._load_manifest().get(model_name, [])
        if not records:
            return None
        return ModelArtifact(**records[-1])

    def list_models(self) -> dict[str, list[ModelArtifact]]:
        manifest = self._load_manifest()
        return {name: [ModelArtifact(**record) for record in records] for name, records in manifest.items()}

    def _next_version(self, model_name: str) -> str:
        records = self._load_manifest().get(model_name, [])
        return f"v{len(records) + 1:04d}"

    def _load_manifest(self) -> dict[str, list[dict[str, Any]]]:
        if not self.manifest_path.exists():
            return {}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))
