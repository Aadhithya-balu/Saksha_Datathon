"""Criminal intelligence inference layer.

Loads trained models once per process and exposes typed functions used by
the API route.  Falls back to on-the-fly training when no saved model exists,
or when a saved artifact predates the current FEATURE_NAMES set (e.g. the
MO-feature extension added in issue #144 gap 132.3).
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any


from app.ai.features.criminal.extractor import FEATURE_NAMES, extract_for_criminal
from app.ai.models.criminal.clustering import CriminalClusteringModel
from app.ai.models.criminal.repeat_offender import RepeatOffenderPredictor
from app.ai.models.criminal.risk_scorer import CriminalRiskScorer
from app.ai.models.criminal.similarity import SimilarOffenderModel

logger = logging.getLogger(__name__)

_MODEL_DIR = Path(__file__).parent.parent / "models" / "criminal"


# ── model loaders (cached per process) ───────────────────────────────────────

def _ensure_trained(db_session=None) -> None:
    """Train and save all models if artifacts are missing."""
    if not (_MODEL_DIR / "risk_scorer.json").exists():
        from app.ai.pipelines.criminal.train import run_training
        run_training(db_session=db_session)


@lru_cache(maxsize=1)
def _risk_model() -> CriminalRiskScorer:
    path = _MODEL_DIR / "risk_scorer.json"
    if not path.exists():
        _ensure_trained()
    return CriminalRiskScorer.load_model(path)


@lru_cache(maxsize=1)
def _repeat_model() -> RepeatOffenderPredictor:
    path = _MODEL_DIR / "repeat_offender.json"
    if not path.exists():
        _ensure_trained()
    return RepeatOffenderPredictor.load_model(path)


@lru_cache(maxsize=1)
def _sim_model() -> SimilarOffenderModel:
    path = _MODEL_DIR / "similarity.json"
    if not path.exists():
        _ensure_trained()
    return SimilarOffenderModel.load_model(path)


@lru_cache(maxsize=1)
def _cluster_model() -> CriminalClusteringModel:
    path = _MODEL_DIR / "clustering.json"
    if not path.exists():
        _ensure_trained()
    return CriminalClusteringModel.load_model(path)


def _load_model(path: Path, loader, db_session=None):
    """Load a model from path, training first if the artifact is missing —
    or stale relative to the current FEATURE_NAMES (auto-migrates artifacts
    saved before the MO-feature extension, gap 132.3)."""
    if not path.exists():
        _ensure_trained(db_session=db_session)
    model = loader(path)
    stored = list(getattr(model, "feature_names", None) or [])
    if stored and stored != list(FEATURE_NAMES):
        logger.info(
            "Artifact %s has %d features, current FEATURE_NAMES has %d — retraining.",
            path.name, len(stored), len(FEATURE_NAMES),
        )
        from app.ai.pipelines.criminal.train import run_training
        run_training(db_session=db_session)
        _invalidate_cache()
        model = loader(path)
    return model


def _invalidate_cache() -> None:
    """Clear lru_cache after retraining so fresh models are loaded."""
    _risk_model.cache_clear()
    _repeat_model.cache_clear()
    _sim_model.cache_clear()
    _cluster_model.cache_clear()


# ── public inference functions ────────────────────────────────────────────────

def _to_uuid(value: str):
    """Convert a string to uuid.UUID; return None on failure."""
    import uuid as _uuid
    try:
        return _uuid.UUID(str(value))
    except (ValueError, AttributeError):
        return None


def score_criminal_risk(db, criminal_id: str) -> dict[str, Any]:
    """Return risk score for a single criminal by UUID string."""
    from app.models.criminal import Criminal
    from sqlalchemy.orm import joinedload
    from app.models.fir import FIRCriminalLink, FIR
    from app.models.crime import CrimeCase

    uid = _to_uuid(criminal_id)
    if uid is None:
        return {"error": "criminal not found"}

    # Ensure models are trained (pass db so test sessions work)
    risk = _load_model(_MODEL_DIR / "risk_scorer.json", CriminalRiskScorer.load_model, db_session=db)

    criminal = (
        db.query(Criminal)
        .options(
            joinedload(Criminal.fir_links)
            .joinedload(FIRCriminalLink.fir)
            .joinedload(FIR.crime_case)
            .joinedload(CrimeCase.category),
            joinedload(Criminal.fir_links)
            .joinedload(FIRCriminalLink.fir)
            .joinedload(FIR.crime_case)
            .joinedload(CrimeCase.location),
        )
        .filter(Criminal.id == uid)
        .first()
    )
    if criminal is None:
        return {"error": "criminal not found"}

    fv = extract_for_criminal(db, criminal)
    pred = risk.predict(fv.values, criminal_id=criminal_id)
    return {
        "criminal_id": pred.criminal_id,
        "risk_score": pred.risk_score,
        "risk_band": pred.risk_band,
        "top_factors": pred.top_factors,
        "confidence": pred.confidence,
        "name": fv.raw.get("name"),
    }


def predict_repeat_offender(db, criminal_id: str) -> dict[str, Any]:
    from app.models.criminal import Criminal
    from sqlalchemy.orm import joinedload
    from app.models.fir import FIRCriminalLink, FIR
    from app.models.crime import CrimeCase

    uid = _to_uuid(criminal_id)
    if uid is None:
        return {"error": "criminal not found"}

    repeat = _load_model(_MODEL_DIR / "repeat_offender.json", RepeatOffenderPredictor.load_model, db_session=db)

    criminal = (
        db.query(Criminal)
        .options(
            joinedload(Criminal.fir_links)
            .joinedload(FIRCriminalLink.fir)
            .joinedload(FIR.crime_case)
            .joinedload(CrimeCase.category),
            joinedload(Criminal.fir_links)
            .joinedload(FIRCriminalLink.fir)
            .joinedload(FIR.crime_case)
            .joinedload(CrimeCase.location),
        )
        .filter(Criminal.id == uid)
        .first()
    )
    if criminal is None:
        return {"error": "criminal not found"}

    fv = extract_for_criminal(db, criminal)
    pred = repeat.predict(fv.values, criminal_id=criminal_id)
    return {
        "criminal_id": pred.criminal_id,
        "will_reoffend": pred.will_reoffend,
        "probability": pred.probability,
        "risk_factors": pred.risk_factors,
        "name": fv.raw.get("name"),
    }


def find_similar_offenders(db, criminal_id: str, top_k: int = 5) -> dict[str, Any]:
    from app.models.criminal import Criminal

    uid = _to_uuid(criminal_id)
    if uid is None:
        return {"error": "criminal not found"}

    sim = _load_model(_MODEL_DIR / "similarity.json", SimilarOffenderModel.load_model, db_session=db)
    criminal = db.query(Criminal).filter(Criminal.id == uid).first()
    if criminal is None:
        return {"error": "criminal not found"}

    fv = extract_for_criminal(db, criminal)
    pred = sim.predict(fv.values, query_id=criminal_id, top_k=top_k)

    # Enrich with names + shared canonical MO tags (gap 132.3)
    from app.services.mo_pattern_service import shared_mo_tags

    similar_enriched = []
    for s in pred.similar:
        sid = _to_uuid(s.criminal_id)
        c = db.query(Criminal).filter(Criminal.id == sid).first() if sid else None
        similar_enriched.append({
            "criminal_id": s.criminal_id,
            "name": c.full_name if c else "Unknown",
            "similarity": s.similarity,
            "rank": s.rank,
            "shared_mo_tags": shared_mo_tags(db, uid, sid) if sid else [],
        })

    return {
        "query_id": pred.query_id,
        "query_name": criminal.full_name,
        "similar": similar_enriched,
    }


def cluster_criminal(db, criminal_id: str) -> dict[str, Any]:
    from app.models.criminal import Criminal

    uid = _to_uuid(criminal_id)
    if uid is None:
        return {"error": "criminal not found"}

    cluster = _load_model(_MODEL_DIR / "clustering.json", CriminalClusteringModel.load_model, db_session=db)
    criminal = db.query(Criminal).filter(Criminal.id == uid).first()
    if criminal is None:
        return {"error": "criminal not found"}

    fv = extract_for_criminal(db, criminal)
    pred = cluster.predict(fv.values, criminal_id=criminal_id)
    return {
        "criminal_id": pred.criminal_id,
        "cluster_id": pred.cluster_id,
        "cluster_label": pred.cluster_label,
        "distance_to_centroid": pred.distance_to_centroid,
        "cluster_profile": pred.cluster_profile,
        "name": fv.raw.get("name"),
    }


def get_investigation_recommendations(db, criminal_id: str) -> dict[str, Any]:
    """Combine all model outputs into actionable investigation recommendations."""
    risk = score_criminal_risk(db, criminal_id)
    repeat = predict_repeat_offender(db, criminal_id)
    cluster = cluster_criminal(db, criminal_id)
    similar = find_similar_offenders(db, criminal_id, top_k=3)

    if "error" in risk:
        return risk

    recommendations: list[str] = []
    risk_band = risk.get("risk_band", "LOW")
    if risk_band in ("CRITICAL", "HIGH"):
        recommendations.append("Immediate surveillance recommended — risk score exceeds threshold.")
    if repeat.get("will_reoffend"):
        prob = repeat.get("probability", 0)
        recommendations.append(f"Re-offence probability {prob:.0%} — flag for proactive monitoring.")
    cluster_label = cluster.get("cluster_label", "")
    if cluster_label == "ORGANISED_NETWORK":
        recommendations.append("Linked to organised network cluster — investigate co-offender associations.")
    elif cluster_label == "ACTIVE_FUGITIVE":
        recommendations.append("Active fugitive profile — coordinate with district units for location trace.")
    if similar.get("similar"):
        names = [s["name"] for s in similar["similar"][:2]]
        recommendations.append(f"Similar offender profiles: {', '.join(names)} — cross-reference FIRs.")
    if not recommendations:
        recommendations.append("No immediate escalation required — continue routine monitoring.")

    return {
        "criminal_id": criminal_id,
        "name": risk.get("name"),
        "risk_score": risk.get("risk_score"),
        "risk_band": risk_band,
        "repeat_offender_probability": repeat.get("probability"),
        "cluster_label": cluster_label,
        "recommendations": recommendations,
        "similar_offenders": similar.get("similar", []),
    }


def retrain_models(db) -> dict[str, Any]:
    """Retrain all models from current DB state and reload caches."""
    from app.ai.pipelines.criminal.train import run_training
    metrics = run_training(db_session=db)
    _invalidate_cache()
    return metrics
