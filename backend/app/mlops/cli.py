from __future__ import annotations

import json
from pathlib import Path
import sys

from .pipeline import run_scheduled_retraining


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv or argv[0] == "retrain":
        print(json.dumps(run_scheduled_retraining(), indent=2))
        return 0
    raise SystemExit(f"Unknown mlops command: {argv[0]}")


if __name__ == "__main__":
    raise SystemExit(main())
