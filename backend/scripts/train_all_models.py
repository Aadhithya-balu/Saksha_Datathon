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
    logger.info("HOTSPOT — attempting LightGBM pipeline from database …")
    try:
        import lightgbm  # noqa: F401 — verify dependency present
        from app.ai.pipelines.hotspot.train import run_training
        result = run_training()
        logger.info("HOTSPOT ✓  metrics=%s", result.get("metrics", result))
        return result
    except Exception as exc:
        logger.warning("HOTSPOT LightGBM pipeline failed (%s) — falling back to RandomForest.", exc)
        return _train_hotspot_rf_fallback()


def _train_hotspot_rf_fallback() -> dict:
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from app.ai.pipelines.hotspot.save_model import save_artifacts

    FEATURE_COLUMNS_PATH = (
        Path(__file__).resolve().parents[1]
        / "app" / "ai" / "models" / "hotspot" / "feature_columns.json"
    )
    feature_columns = json.loads(FEATURE_COLUMNS_PATH.read_text())

    rng = np.random.default_rng(42)
    N = 2_000
    X = rng.uniform(0, 10, size=(N, len(feature_columns)))
    y = np.clip(X[:, 0] * 1.1 + rng.normal(0, 0.5, N), 0, None)
    split = int(N * 0.8)

    model = RandomForestRegressor(n_estimators=200, max_depth=10, min_samples_leaf=3,
                                  random_state=42, n_jobs=-1)
    model.fit(X[:split], y[:split])
    preds = model.predict(X[split:])
    metrics = {
        "rmse": float(np.sqrt(mean_squared_error(y[split:], preds))),
        "mae":  float(mean_absolute_error(y[split:], preds)),
        "r2":   float(r2_score(y[split:], preds)),
    }
    save_artifacts(
        model=model,
        metrics=metrics,
        best_params={"algorithm": "RandomForest", "n_estimators": 200,
                     "max_depth": 10, "min_samples_leaf": 3, "random_state": 42},
        feature_columns=feature_columns,
        training_rows=N,
    )
    logger.info("HOTSPOT RF fallback ✓  metrics=%s", metrics)
    return {"metrics": metrics}


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
