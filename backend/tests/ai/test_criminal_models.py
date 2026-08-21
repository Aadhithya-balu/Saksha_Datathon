"""Tests for the criminal intelligence AI module.

Covers:
- Feature extractor (unit)
- Risk scorer model (unit)
- Repeat offender model (unit)
- Similarity model (unit)
- Clustering model (unit)
- Training pipeline (integration with in-memory DB)
- API endpoints (integration via TestClient)
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pytest

# ── ensure test env uses SQLite before any app import ────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("APP_DEBUG", "false")

from app.ai.features.criminal.extractor import (
    FEATURE_NAMES,
    CriminalFeatureVector,
    extract_for_criminal,
)
from app.ai.models.criminal.clustering import CriminalClusteringModel
from app.ai.models.criminal.repeat_offender import RepeatOffenderPredictor
from app.ai.models.criminal.risk_scorer import CriminalRiskScorer
from app.ai.models.criminal.similarity import SimilarOffenderModel


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _make_X(n: int = 10) -> np.ndarray:
    rng = np.random.default_rng(7)
    return rng.uniform(0, 5, size=(n, len(FEATURE_NAMES)))


def _make_ids(n: int = 10) -> list[str]:
    return [str(uuid.uuid4()) for _ in range(n)]


# ═══════════════════════════════════════════════════════════════════════════════
# Feature extractor
# ═══════════════════════════════════════════════════════════════════════════════

class TestFeatureExtractor:
    def test_feature_names_stable(self):
        assert len(FEATURE_NAMES) == 10
        assert "fir_count" in FEATURE_NAMES
        assert "risk_score" not in FEATURE_NAMES  # not a raw feature

    def test_extract_for_criminal_no_firs(self, db_session):
        """Criminal with no FIR links should produce a zero-heavy vector."""
        from app.models.criminal import Criminal
        from app.models.role import Role
        from app.models.user import User

        criminal = Criminal(
            full_name="Test Subject",
            date_of_birth=date(1990, 1, 1),
            gender="Male",
            status="at_large",
        )
        db_session.add(criminal)
        db_session.flush()

        fv = extract_for_criminal(db_session, criminal)

        assert isinstance(fv, CriminalFeatureVector)
        assert fv.values.shape == (len(FEATURE_NAMES),)
        assert fv.values[FEATURE_NAMES.index("fir_count")] == 0.0
        assert fv.values[FEATURE_NAMES.index("status_encoded")] == 2.0  # at_large


# ═══════════════════════════════════════════════════════════════════════════════
# Risk scorer
# ═══════════════════════════════════════════════════════════════════════════════

class TestCriminalRiskScorer:
    def test_train_and_predict(self):
        X = _make_X()
        model = CriminalRiskScorer(feature_names=FEATURE_NAMES)
        model.train(X)
        pred = model.predict(X[0], criminal_id="test-id")

        assert 0.0 <= pred.risk_score <= 100.0
        assert pred.risk_band in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert len(pred.top_factors) <= 5
        assert 0.0 <= pred.confidence <= 1.0

    def test_evaluate_returns_metrics(self):
        X = _make_X()
        model = CriminalRiskScorer(feature_names=FEATURE_NAMES)
        model.train(X)
        metrics = model.evaluate(X)

        assert "mean_risk_score" in metrics
        assert "high_risk_fraction" in metrics

    def test_save_load_roundtrip(self, tmp_path):
        X = _make_X()
        model = CriminalRiskScorer(feature_names=FEATURE_NAMES)
        model.train(X)
        path = tmp_path / "risk.json"
        model.save_model(path)

        loaded = CriminalRiskScorer.load_model(path)
        pred_orig = model.predict(X[0], "a")
        pred_loaded = loaded.predict(X[0], "a")
        assert pred_orig.risk_score == pred_loaded.risk_score

    def test_untrained_raises(self):
        model = CriminalRiskScorer(feature_names=FEATURE_NAMES)
        with pytest.raises(RuntimeError, match="trained"):
            model.predict(np.zeros(len(FEATURE_NAMES)))

    def test_wrong_feature_count_raises(self):
        X = _make_X()
        model = CriminalRiskScorer(feature_names=FEATURE_NAMES)
        model.train(X)
        with pytest.raises(ValueError):
            model.predict(np.zeros(3))


# ═══════════════════════════════════════════════════════════════════════════════
# Repeat offender predictor
# ═══════════════════════════════════════════════════════════════════════════════

class TestRepeatOffenderPredictor:
    def test_train_predict_no_labels(self):
        X = _make_X()
        model = RepeatOffenderPredictor(feature_names=FEATURE_NAMES)
        model.train(X)
        pred = model.predict(X[0], criminal_id="x")

        assert isinstance(pred.will_reoffend, bool)
        assert 0.0 <= pred.probability <= 1.0
        assert len(pred.risk_factors) <= 5

    def test_train_predict_with_labels(self):
        X = _make_X(20)
        y = np.array([i % 2 for i in range(20)], dtype=float)
        model = RepeatOffenderPredictor(feature_names=FEATURE_NAMES)
        model.train(X, y=y)
        metrics = model.evaluate(X, y_true=y)

        assert "f1" in metrics
        assert "auc" in metrics

    def test_save_load_roundtrip(self, tmp_path):
        X = _make_X()
        model = RepeatOffenderPredictor(feature_names=FEATURE_NAMES)
        model.train(X)
        path = tmp_path / "repeat.json"
        model.save_model(path)

        loaded = RepeatOffenderPredictor.load_model(path)
        assert loaded.predict(X[0]).probability == model.predict(X[0]).probability


# ═══════════════════════════════════════════════════════════════════════════════
# Similarity model
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimilarOffenderModel:
    def test_train_predict_returns_ranked_results(self):
        X = _make_X(10)
        ids = _make_ids(10)
        model = SimilarOffenderModel(feature_names=FEATURE_NAMES)
        model.train(X, ids=ids)
        pred = model.predict(X[0], query_id=ids[0], top_k=3)

        assert pred.query_id == ids[0]
        assert len(pred.similar) <= 3
        # query itself should be excluded
        assert all(s.criminal_id != ids[0] for s in pred.similar)
        # similarities should be descending
        sims = [s.similarity for s in pred.similar]
        assert sims == sorted(sims, reverse=True)

    def test_evaluate_returns_index_size(self):
        X = _make_X(8)
        model = SimilarOffenderModel(feature_names=FEATURE_NAMES)
        model.train(X)
        metrics = model.evaluate(X)
        assert metrics["index_size"] == 8.0

    def test_save_load_roundtrip(self, tmp_path):
        X = _make_X(6)
        ids = _make_ids(6)
        model = SimilarOffenderModel(feature_names=FEATURE_NAMES)
        model.train(X, ids=ids)
        path = tmp_path / "sim.json"
        model.save_model(path)

        loaded = SimilarOffenderModel.load_model(path)
        pred = loaded.predict(X[0], query_id=ids[0], top_k=2)
        assert len(pred.similar) <= 2


# ═══════════════════════════════════════════════════════════════════════════════
# Clustering model
# ═══════════════════════════════════════════════════════════════════════════════

class TestCriminalClusteringModel:
    def test_train_predict_valid_cluster(self):
        X = _make_X(12)
        model = CriminalClusteringModel(feature_names=FEATURE_NAMES, n_clusters=3)
        model.train(X)
        pred = model.predict(X[0], criminal_id="c1")

        assert 0 <= pred.cluster_id < 3
        assert pred.cluster_label in ("ORGANISED_NETWORK", "HIGH_SEVERITY_REPEAT", "ACTIVE_FUGITIVE", "LOW_ACTIVITY")
        assert pred.distance_to_centroid >= 0.0
        assert set(pred.cluster_profile.keys()) == set(FEATURE_NAMES)

    def test_evaluate_returns_inertia(self):
        X = _make_X(12)
        model = CriminalClusteringModel(feature_names=FEATURE_NAMES, n_clusters=3)
        model.train(X)
        metrics = model.evaluate(X)
        assert "inertia" in metrics
        assert metrics["inertia"] >= 0.0

    def test_n_clusters_capped_at_n_samples(self):
        X = _make_X(2)
        model = CriminalClusteringModel(feature_names=FEATURE_NAMES, n_clusters=10)
        model.train(X)
        assert model._centroids.shape[0] <= 2

    def test_save_load_roundtrip(self, tmp_path):
        X = _make_X(8)
        model = CriminalClusteringModel(feature_names=FEATURE_NAMES, n_clusters=2)
        model.train(X)
        path = tmp_path / "cluster.json"
        model.save_model(path)

        loaded = CriminalClusteringModel.load_model(path)
        assert loaded.predict(X[0]).cluster_id == model.predict(X[0]).cluster_id


# ═══════════════════════════════════════════════════════════════════════════════
# Training pipeline (integration)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrainingPipeline:
    def test_run_training_with_empty_db(self, db_session, tmp_path, monkeypatch):
        """Pipeline should succeed even with no criminals (uses synthetic fallback)."""
        from app.ai.pipelines.criminal import train as train_module

        monkeypatch.setattr(train_module, "MODEL_DIR", tmp_path / "criminal")

        metrics = train_module.run_training(db_session=db_session)

        assert "trained_at" in metrics
        assert "risk_scorer" in metrics
        assert "repeat_offender" in metrics
        assert "similarity" in metrics
        assert "clustering" in metrics
        assert (tmp_path / "criminal" / "risk_scorer.json").exists()
        assert (tmp_path / "criminal" / "training_metrics.json").exists()

    def test_run_training_with_seeded_db(self, db_session, tmp_path, monkeypatch):
        """Pipeline should use real DB records when available."""
        from app.ai.pipelines.criminal import train as train_module
        from app.models.criminal import Criminal

        monkeypatch.setattr(train_module, "MODEL_DIR", tmp_path / "criminal")

        for i in range(3):
            db_session.add(Criminal(
                full_name=f"Criminal {i}",
                date_of_birth=date(1985 + i, 1, 1),
                status="at_large",
            ))
        db_session.flush()

        metrics = train_module.run_training(db_session=db_session)
        assert metrics["n_criminals"] == 3


# ═══════════════════════════════════════════════════════════════════════════════
# API endpoints (integration)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCriminalAPIEndpoints:
    """End-to-end tests via TestClient with an in-memory SQLite DB."""

    def _seed_db(self, db_session):
        """Seed minimal data: role, user, criminal."""
        from app.core.security import hash_password
        from app.models.criminal import Criminal
        from app.models.role import Role
        from app.models.user import User

        role = Role(name="admin", description="admin")
        db_session.add(role)
        db_session.flush()

        user = User(
            username="testadmin",
            email="testadmin@saksha.local",
            full_name="Test Admin",
            hashed_password=hash_password("TestPass1!"),
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)

        criminal = Criminal(
            full_name="Test Criminal",
            date_of_birth=date(1985, 6, 15),
            status="at_large",
        )
        db_session.add(criminal)
        db_session.flush()
        return user, criminal

    def _get_token(self, client, username: str, password: str) -> str:
        resp = client.post(
            "/api/v2/auth/login",
            json={"username": username, "password": password},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    def test_risk_endpoint_returns_score(self, client, db_session, tmp_path, monkeypatch):
        from app.ai import inference as inf_pkg
        import app.ai.inference.criminal as inf_mod
        from app.ai.pipelines.criminal import train as train_module

        monkeypatch.setattr(train_module, "MODEL_DIR", tmp_path / "criminal")
        monkeypatch.setattr(inf_mod, "_MODEL_DIR", tmp_path / "criminal")
        inf_mod._invalidate_cache()

        user, criminal = self._seed_db(db_session)
        token = self._get_token(client, "testadmin", "TestPass1!")

        resp = client.get(
            f"/api/v2/ai/criminal/{criminal.id}/risk",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "risk_score" in data
        assert 0.0 <= data["risk_score"] <= 100.0
        assert data["risk_band"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_repeat_offender_endpoint(self, client, db_session, tmp_path, monkeypatch):
        import app.ai.inference.criminal as inf_mod
        from app.ai.pipelines.criminal import train as train_module

        monkeypatch.setattr(train_module, "MODEL_DIR", tmp_path / "criminal")
        monkeypatch.setattr(inf_mod, "_MODEL_DIR", tmp_path / "criminal")
        inf_mod._invalidate_cache()

        user, criminal = self._seed_db(db_session)
        token = self._get_token(client, "testadmin", "TestPass1!")

        resp = client.get(
            f"/api/v2/ai/criminal/{criminal.id}/repeat-offender",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "will_reoffend" in data
        assert "probability" in data

    def test_similar_endpoint(self, client, db_session, tmp_path, monkeypatch):
        import app.ai.inference.criminal as inf_mod
        from app.ai.pipelines.criminal import train as train_module

        monkeypatch.setattr(train_module, "MODEL_DIR", tmp_path / "criminal")
        monkeypatch.setattr(inf_mod, "_MODEL_DIR", tmp_path / "criminal")
        inf_mod._invalidate_cache()

        user, criminal = self._seed_db(db_session)
        token = self._get_token(client, "testadmin", "TestPass1!")

        resp = client.get(
            f"/api/v2/ai/criminal/{criminal.id}/similar?top_k=3",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "similar" in data
        assert isinstance(data["similar"], list)

    def test_cluster_endpoint(self, client, db_session, tmp_path, monkeypatch):
        import app.ai.inference.criminal as inf_mod
        from app.ai.pipelines.criminal import train as train_module

        monkeypatch.setattr(train_module, "MODEL_DIR", tmp_path / "criminal")
        monkeypatch.setattr(inf_mod, "_MODEL_DIR", tmp_path / "criminal")
        inf_mod._invalidate_cache()

        user, criminal = self._seed_db(db_session)
        token = self._get_token(client, "testadmin", "TestPass1!")

        resp = client.get(
            f"/api/v2/ai/criminal/{criminal.id}/cluster",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "cluster_label" in data
        assert "cluster_id" in data

    def test_recommendations_endpoint(self, client, db_session, tmp_path, monkeypatch):
        import app.ai.inference.criminal as inf_mod
        from app.ai.pipelines.criminal import train as train_module

        monkeypatch.setattr(train_module, "MODEL_DIR", tmp_path / "criminal")
        monkeypatch.setattr(inf_mod, "_MODEL_DIR", tmp_path / "criminal")
        inf_mod._invalidate_cache()

        user, criminal = self._seed_db(db_session)
        token = self._get_token(client, "testadmin", "TestPass1!")

        resp = client.get(
            f"/api/v2/ai/criminal/{criminal.id}/recommendations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) >= 1

    def test_unknown_criminal_returns_404(self, client, db_session, tmp_path, monkeypatch):
        import app.ai.inference.criminal as inf_mod
        from app.ai.pipelines.criminal import train as train_module

        monkeypatch.setattr(train_module, "MODEL_DIR", tmp_path / "criminal")
        monkeypatch.setattr(inf_mod, "_MODEL_DIR", tmp_path / "criminal")
        inf_mod._invalidate_cache()

        # seed just a user so login works
        from app.core.security import hash_password
        from app.models.role import Role
        from app.models.user import User

        role = Role(name="admin", description="admin")
        db_session.add(role)
        db_session.flush()
        user = User(
            username="testadmin2",
            email="testadmin2@saksha.local",
            full_name="Test Admin 2",
            hashed_password=hash_password("TestPass1!"),
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()

        token = self._get_token(client, "testadmin2", "TestPass1!")
        fake_id = str(uuid.uuid4())

        resp = client.get(
            f"/api/v2/ai/criminal/{fake_id}/risk",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_retrain_requires_admin(self, client, db_session, tmp_path, monkeypatch):
        import app.ai.inference.criminal as inf_mod
        from app.ai.pipelines.criminal import train as train_module
        from app.core.security import hash_password
        from app.models.role import Role
        from app.models.user import User

        monkeypatch.setattr(train_module, "MODEL_DIR", tmp_path / "criminal")
        monkeypatch.setattr(inf_mod, "_MODEL_DIR", tmp_path / "criminal")
        inf_mod._invalidate_cache()

        role = Role(name="investigator", description="investigator")
        db_session.add(role)
        db_session.flush()
        user = User(
            username="inv_user",
            email="inv@saksha.local",
            full_name="Investigator",
            hashed_password=hash_password("TestPass1!"),
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()

        token = self._get_token(client, "inv_user", "TestPass1!")
        resp = client.post(
            "/api/v2/ai/criminal/retrain",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
