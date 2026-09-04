"""
Train all SAKSHA ML model artifacts in one shot.

Trains:
  1. Hotspot model  — LightGBM from real DB (falls back to RandomForest on synthetic data)
  2. Risk model     — RandomForest from real DB
  3. Forecast model — XGBoost from real DB

After training, invalidates lru_caches in the inference modules so a running
server picks up the new artifacts without a restart.

Run from backend/:
    py -3.12 scripts/train_all_models.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train_all")

SEPARATOR = "-" * 60


# ---------------------------------------------------------------------------
# Hotspot
# ---------------------------------------------------------------------------

def train_hotspot() -> dict:
    logger.info("HOTSPOT — training hotspot model from database …")
    from app.ai.pipelines.hotspot.train import run_training
    result = run_training()
    logger.info("HOTSPOT ✓  metrics=%s", result.get("metrics", result))
    return result


# ---------------------------------------------------------------------------
# Risk + Forecast
# ---------------------------------------------------------------------------

def train_risk() -> dict:
    logger.info("RISK + FORECAST — training from database …")
    try:
        import numpy as np  # noqa: F401 — needed inside run_training
        from app.ai.pipelines.risk.train import run_training
        result = run_training()
        logger.info("RISK ✓  metrics=%s", result.get("risk", {}))
        logger.info("FORECAST ✓  metrics=%s", result.get("forecast", {}))
        return result
    except Exception as exc:
        logger.error("RISK pipeline failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------

def invalidate_caches() -> None:
    try:
        from app.ai.inference.hotspot import invalidate_caches as hc
        hc()
        logger.info("Hotspot inference cache cleared.")
    except Exception as exc:
        logger.warning("Could not clear hotspot cache: %s", exc)

    try:
        from app.ai.inference.risk import invalidate_caches as rc
        rc()
        logger.info("Risk inference cache cleared.")
    except Exception as exc:
        logger.warning("Could not clear risk cache: %s", exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    results: dict[str, object] = {}
    errors: list[str] = []

    print(SEPARATOR)
    print("  SAKSHA — Training All ML Models")
    print(SEPARATOR)

    # 1. Hotspot
    print()
    try:
        results["hotspot"] = train_hotspot()
    except Exception as exc:
        logger.error("HOTSPOT FAILED: %s", exc)
        errors.append(f"hotspot: {exc}")

    # 2. Risk + Forecast
    print()
    try:
        results["risk"] = train_risk()
    except Exception as exc:
        logger.error("RISK/FORECAST FAILED: %s", exc)
        errors.append(f"risk/forecast: {exc}")

    # 3. Invalidate caches
    print()
    invalidate_caches()

    # 4. Summary
    print()
    print(SEPARATOR)
    print("  TRAINING SUMMARY")
    print(SEPARATOR)

    if "hotspot" in results:
        m = results["hotspot"].get("metrics", results["hotspot"])
        print(f"  Hotspot   OK  RMSE={m.get('rmse', '?'):.4f}  R2={m.get('r2', '?'):.4f}")
    else:
        print("  Hotspot   FAILED")

    if "risk" in results:
        rm = results["risk"].get("risk", {})
        fm = results["risk"].get("forecast", {})
        print(f"  Risk      OK  RMSE={rm.get('rmse', '?'):.4f}  R2={rm.get('r2', '?'):.4f}")
        print(f"  Forecast  OK  RMSE={fm.get('rmse', '?'):.4f}  R2={fm.get('r2', '?'):.4f}")
    else:
        print("  Risk      FAILED")
        print("  Forecast  FAILED")

    if errors:
        print()
        print("  Errors:")
        for e in errors:
            print(f"    • {e}")
        sys.exit(1)

    print()
    print("  All models trained. Artifacts written to backend/app/ai/models/")
    print("  Restart the server (or wait for prewarm) to activate ML mode.")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
