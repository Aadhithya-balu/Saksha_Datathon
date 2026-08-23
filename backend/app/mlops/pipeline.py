from __future__ import annotations

import importlib.util
import inspect
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dataset_versioning import DatasetVersionStore
from .monitoring import ModelMonitor
from .registry import ModelRegistry


@dataclass(frozen=True)
class ModelRunResult:
    model_name: str
    dataset_version: str
    registry_version: str
    metrics: dict[str, Any]
    deployed_stage: str


def run_full_mlops_cycle(db_session=None, *, registry_root: str | Path = "mlflow") -> list[ModelRunResult]:
    registry = ModelRegistry(root=registry_root)
    dataset_store = DatasetVersionStore(root=Path(registry_root) / "datasets")
    monitor = ModelMonitor(root="monitoring")

    results: list[ModelRunResult] = []
    for model_name in ("criminal", "risk", "hotspot"):
        metrics = _run_trainer(model_name, db_session=db_session)
        dataset_version = dataset_store.version_records(model_name, [{"metrics": metrics}], metadata={"source": "training"}).version
        artifact_path = _artifact_path_for(model_name, registry_root)
        artifact = registry.register(model_name, artifact_path, dataset_version=dataset_version, metrics_path=_metrics_path_for(model_name, registry_root), stage="staging", metadata={"metrics": metrics})
        registry.promote(model_name, artifact.version, "production")
        snapshot = monitor.record(model_name, dataset_version, metrics, drift=[])
        results.append(ModelRunResult(model_name=model_name, dataset_version=snapshot.dataset_version, registry_version=artifact.version, metrics=metrics, deployed_stage="production"))
    return results


def run_scheduled_retraining(db_session=None, *, registry_root: str | Path = "mlflow") -> dict[str, Any]:
    runs = run_full_mlops_cycle(db_session=db_session, registry_root=registry_root)
    return {"status": "ok", "runs": [asdict(run) for run in runs], "generated_at": datetime.now(timezone.utc).isoformat()}


def _artifact_path_for(model_name: str, registry_root: str | Path) -> str:
    return str(Path(registry_root) / "artifacts" / model_name / "model.bin")


def _metrics_path_for(model_name: str, registry_root: str | Path) -> str:
    return str(Path(registry_root) / "artifacts" / model_name / "metrics.json")


def _run_trainer(model_name: str, db_session=None) -> dict[str, Any]:
    module_map = {
        "criminal": "app.ai.pipelines.criminal.train",
        "risk": "app.ai.pipelines.risk.train",
        "hotspot": "app.ai.pipelines.hotspot.train",
    }
    if model_name == "hotspot" and importlib.util.find_spec("lightgbm") is None:
        return {
            "status": "skipped",
            "model_name": model_name,
            "error": "lightgbm is not installed in this environment",
        }
    try:
        module = __import__(module_map[model_name], fromlist=["run_training"])
        trainer = getattr(module, "run_training")
        signature = inspect.signature(trainer)
        if "db_session" in signature.parameters:
            return trainer(db_session=db_session)
        return trainer()
    except ModuleNotFoundError as exc:
        missing = str(exc)
        if model_name == "hotspot" and "lightgbm" in missing.lower():
            return {
                "status": "skipped",
                "model_name": model_name,
                "error": "lightgbm is not installed in this environment",
            }
        return {
            "status": "degraded",
            "model_name": model_name,
            "error": f"optional dependency missing: {exc}",
        }
    except TypeError:
        try:
            return trainer()
        except Exception as exc:
            return {"status": "degraded", "model_name": model_name, "error": str(exc)}
    except Exception as exc:
        return {"status": "degraded", "model_name": model_name, "error": str(exc)}
