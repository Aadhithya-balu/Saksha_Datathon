from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class DatasetVersion:
    dataset_name: str
    version: str
    content_hash: str
    row_count: int
    created_at: str
    metadata: dict[str, Any]


class DatasetVersionStore:
    def __init__(self, root: str | Path = "mlflow/datasets") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def version_records(self, dataset_name: str, records: Iterable[dict[str, Any]], *, metadata: dict[str, Any] | None = None) -> DatasetVersion:
        payload = json.dumps(list(records), sort_keys=True, default=str).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        version = DatasetVersion(
            dataset_name=dataset_name,
            version=digest[:12],
            content_hash=digest,
            row_count=len(json.loads(payload.decode("utf-8"))),
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        out = self.root / f"{dataset_name}-{version.version}.json"
        out.write_text(json.dumps(asdict(version), indent=2), encoding="utf-8")
        return version

    def latest(self, dataset_name: str) -> DatasetVersion | None:
        matches = sorted(self.root.glob(f"{dataset_name}-*.json"))
        if not matches:
            return None
        return DatasetVersion(**json.loads(matches[-1].read_text(encoding="utf-8")))
