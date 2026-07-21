"""Criminal intelligence training pipeline.

Loads all criminals from the database, extracts features, trains all four
criminal models, saves artifacts, and returns evaluation metrics.

Usage (from backend/):
    python -m app.ai.pipelines.criminal.train
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from app.ai.features.criminal.extractor import FEATURE_NAMES, extract_all
from app.ai.models.criminal.clustering import CriminalClusteringModel
from app.ai.models.criminal.repeat_offender import RepeatOffenderPredictor
from app.ai.models.criminal.risk_scorer import CriminalRiskScorer
from app.ai.models.criminal.similarity import SimilarOffenderModel

MODEL_DIR = Path(__file__).parent.parent.parent / "models" / "criminal"


def _fallback_matrix(n_features: int) -> tuple[np.ndarray, list[str]]:
    """Return a minimal synthetic matrix when the DB has < 2 criminals."""
    rng = np.random.default_rng(0)
    X = rng.uniform(0, 5, size=(8, n_features))
    ids = [f"synthetic-{i}" for i in range(8)]
    return X, ids


def run_training(db_session=None) -> dict[str, Any]:
    """Train all criminal models.  Accepts an optional SQLAlchemy session for
    testing; if None, opens its own session from the shared factory."""
    from app.database.postgres import SessionLocal

    own_session = db_session is None
    db = SessionLocal() if own_session else db_session
    try:
        vectors = extract_all(db)
    finally:
        if own_session:
            db.close()

    n_features = len(FEATURE_NAMES)

    if len(vectors) >= 2:
        X = np.vstack([v.values for v in vectors])
        ids = [v.criminal_id for v in vectors]
    else:
        X, ids = _fallback_matrix(n_features)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Risk scorer ────────────────────────────────────────────────────────
    risk_model = CriminalRiskScorer(feature_names=FEATURE_NAMES)
    risk_model.train(X)
    risk_metrics = risk_model.evaluate(X)
    risk_model.save_model(MODEL_DIR / "risk_scorer.json")

    # ── 2. Repeat offender predictor ─────────────────────────────────────────
    repeat_model = RepeatOffenderPredictor(feature_names=FEATURE_NAMES)
    repeat_model.train(X)
    repeat_metrics = repeat_model.evaluate(X)
    repeat_model.save_model(MODEL_DIR / "repeat_offender.json")

    # ── 3. Similarity index ───────────────────────────────────────────────────
    sim_model = SimilarOffenderModel(feature_names=FEATURE_NAMES)
    sim_model.train(X, ids=ids)
    sim_metrics = sim_model.evaluate(X)
    sim_model.save_model(MODEL_DIR / "similarity.json")

    # ── 4. Clustering ─────────────────────────────────────────────────────────
    cluster_model = CriminalClusteringModel(feature_names=FEATURE_NAMES, n_clusters=min(4, len(X)))
    cluster_model.train(X)
    cluster_metrics = cluster_model.evaluate(X)
    cluster_model.save_model(MODEL_DIR / "clustering.json")

    # ── Save combined metrics ─────────────────────────────────────────────────
    metrics: dict[str, Any] = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_criminals": len(vectors),
        "n_features": n_features,
        "feature_names": FEATURE_NAMES,
        "risk_scorer": risk_metrics,
        "repeat_offender": repeat_metrics,
        "similarity": sim_metrics,
        "clustering": cluster_metrics,
    }
    (MODEL_DIR / "training_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    return metrics


if __name__ == "__main__":
    result = run_training()
    print(json.dumps(result, indent=2))
