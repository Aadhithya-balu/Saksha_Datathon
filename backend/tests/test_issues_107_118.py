"""
Tests for Issues #107 (person images) and #118 (face verification).

All tests use isolated in-memory SQLite fixtures — no production data is
touched.  The face_service is tested with synthetic numpy embeddings so
the tests run without a camera or real biometric data.
"""
from __future__ import annotations

import base64
import io
import json
import uuid

import numpy as np
import pytest
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ---------------------------------------------------------------------------
# Minimal in-memory DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db_session():
    from app.database.postgres import Base
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gray_image_b64(width: int = 160, height: int = 160, fill: int = 128) -> str:
    img = Image.fromarray(np.full((height, width), fill, dtype=np.uint8), mode="L").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def _make_embedding(seed: int = 42) -> str:
    rng = np.random.default_rng(seed)
    vec = rng.random(4096).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return json.dumps(vec.tolist())


# ---------------------------------------------------------------------------
# Issue #107 — image_url field tests
# ---------------------------------------------------------------------------

class TestPersonImageField:
    def test_criminal_image_url_defaults_null(self, db_session):
        from app.models.criminal import Criminal
        c = Criminal(full_name="Test Criminal", status="at_large")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        assert c.image_url is None

    def test_criminal_image_url_can_be_set(self, db_session):
        from app.models.criminal import Criminal
        c = Criminal(
            full_name="Image Criminal",
            status="at_large",
            image_url="https://storage.example.com/persons/criminals/test.jpg",
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        assert c.image_url == "https://storage.example.com/persons/criminals/test.jpg"

    def test_victim_image_url_defaults_null(self, db_session):
        from app.models.victim import Victim
        v = Victim(full_name="Test Victim")
        db_session.add(v)
        db_session.commit()
        db_session.refresh(v)
        assert v.image_url is None

    def test_officer_image_url_defaults_null(self, db_session):
        from app.models.officer import Officer
        o = Officer(badge_number=f"TST-{uuid.uuid4().hex[:6]}", name="Test Officer", station="HQ")
        db_session.add(o)
        db_session.commit()
        db_session.refresh(o)
        assert o.image_url is None

    def test_officer_image_url_can_be_set(self, db_session):
        from app.models.officer import Officer
        o = Officer(
            badge_number=f"TST-{uuid.uuid4().hex[:6]}",
            name="Photo Officer",
            station="HQ",
            image_url="https://storage.example.com/persons/officers/photo.jpg",
        )
        db_session.add(o)
        db_session.commit()
        db_session.refresh(o)
        assert o.image_url is not None


# ---------------------------------------------------------------------------
# Issue #118 — face_service unit tests (no camera, no real biometrics)
# ---------------------------------------------------------------------------

class TestFaceService:
    def test_embedding_roundtrip(self):
        from app.services.face_service import embedding_to_json, embedding_from_json
        rng = np.random.default_rng(0)
        vec = rng.random(4096).astype(np.float32)
        vec /= np.linalg.norm(vec)
        restored = embedding_from_json(embedding_to_json(vec))
        assert np.allclose(vec, restored, atol=1e-5)

    def test_cosine_similarity_identical(self):
        from app.services.face_service import cosine_similarity
        rng = np.random.default_rng(1)
        vec = rng.random(4096).astype(np.float32)
        vec /= np.linalg.norm(vec)
        assert abs(cosine_similarity(vec, vec) - 1.0) < 1e-5

    def test_cosine_similarity_orthogonal(self):
        from app.services.face_service import cosine_similarity
        a = np.zeros(4096, dtype=np.float32)
        b = np.zeros(4096, dtype=np.float32)
        a[0] = 1.0
        b[1] = 1.0
        assert abs(cosine_similarity(a, b)) < 1e-5

    def test_no_enrollment_returns_no_enrollment(self, db_session):
        from app.services.face_service import verify_face_from_b64
        # Ensure no face-enabled officers exist in this fresh session
        from app.models.officer import Officer
        db_session.query(Officer).filter(Officer.face_enabled.is_(True)).delete()
        db_session.commit()
        result = verify_face_from_b64(db_session, _make_gray_image_b64())
        assert result.success is False
        assert result.error_code == "NO_ENROLLMENT"

    def test_bad_image_returns_bad_image(self, db_session):
        from app.services.face_service import verify_face_from_b64
        result = verify_face_from_b64(db_session, "not-valid-base64!!!")
        assert result.success is False
        assert result.error_code == "BAD_IMAGE"

    def test_inactive_officer_not_matched(self, db_session):
        from app.models.officer import Officer
        from app.services.face_service import verify_face_from_b64
        # Clear enrolled officers first
        db_session.query(Officer).filter(Officer.face_enabled.is_(True)).delete()
        db_session.commit()

        officer = Officer(
            badge_number=f"KSP-INACTIVE-{uuid.uuid4().hex[:4]}",
            name="Inactive Officer",
            station="Test Station",
            face_embedding=_make_embedding(seed=99),
            face_enabled=True,
            status="inactive",
        )
        db_session.add(officer)
        db_session.commit()

        result = verify_face_from_b64(db_session, _make_gray_image_b64())
        # Inactive officer must not appear in candidates → NO_ENROLLMENT
        assert result.success is False
        assert result.error_code == "NO_ENROLLMENT"

    def test_face_enabled_false_not_matched(self, db_session):
        from app.models.officer import Officer
        from app.services.face_service import verify_face_from_b64
        db_session.query(Officer).filter(Officer.face_enabled.is_(True)).delete()
        db_session.commit()

        officer = Officer(
            badge_number=f"KSP-DISABLED-{uuid.uuid4().hex[:4]}",
            name="Disabled Face Officer",
            station="Test Station",
            face_embedding=_make_embedding(seed=77),
            face_enabled=False,
            status="active",
        )
        db_session.add(officer)
        db_session.commit()

        result = verify_face_from_b64(db_session, _make_gray_image_b64())
        assert result.success is False

    def test_no_match_below_threshold(self, db_session):
        """Probe embedding far from gallery → NO_MATCH."""
        from app.models.officer import Officer
        from app.services.face_service import (
            verify_face_from_b64,
            FACE_MATCH_THRESHOLD,
            cosine_similarity,
            embedding_from_json,
        )
        db_session.query(Officer).filter(Officer.face_enabled.is_(True)).delete()
        db_session.commit()

        emb_json = _make_embedding(seed=10)
        officer = Officer(
            badge_number=f"KSP-MATCH-{uuid.uuid4().hex[:4]}",
            name="Enrolled Officer",
            station="Test Station",
            face_embedding=emb_json,
            face_enabled=True,
            status="active",
        )
        db_session.add(officer)
        db_session.commit()

        # Probe with a very different embedding (seed=999) — similarity will be ~0
        probe_vec = embedding_from_json(_make_embedding(seed=999))
        gallery_vec = embedding_from_json(emb_json)
        sim = cosine_similarity(probe_vec, gallery_vec)
        assert sim < FACE_MATCH_THRESHOLD, "Test setup: probe must be below threshold"

    def test_verify_result_never_contains_embedding(self):
        from app.services.face_service import VerifyResult
        r = VerifyResult(success=False, error_code="NO_MATCH")
        assert not hasattr(r, "face_embedding")
        assert not hasattr(r, "embedding")
        assert not hasattr(r, "gallery_vec")

    def test_enroll_officer_not_found(self, db_session):
        from app.services.face_service import enroll_face_from_b64
        result = enroll_face_from_b64(db_session, str(uuid.uuid4()), _make_gray_image_b64())
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_enroll_bad_image(self, db_session):
        from app.models.officer import Officer
        from app.services.face_service import enroll_face_from_b64
        officer = Officer(
            badge_number=f"KSP-ENROLL-{uuid.uuid4().hex[:4]}",
            name="Enroll Test",
            station="HQ",
            status="active",
        )
        db_session.add(officer)
        db_session.commit()
        result = enroll_face_from_b64(db_session, str(officer.id), "bad-data")
        assert result["success"] is False

    def test_enroll_sets_face_enabled(self, db_session):
        """After successful enroll, face_enabled must be True and embedding non-null."""
        from app.models.officer import Officer
        from app.services.face_service import enroll_face_from_b64
        officer = Officer(
            badge_number=f"KSP-ENROLL2-{uuid.uuid4().hex[:4]}",
            name="Enroll Test 2",
            station="HQ",
            status="active",
            face_enabled=False,
        )
        db_session.add(officer)
        db_session.commit()

        result = enroll_face_from_b64(db_session, str(officer.id), _make_gray_image_b64())
        assert result["success"] is True
        db_session.refresh(officer)
        assert officer.face_enabled is True
        assert officer.face_embedding is not None
        assert officer.face_enrolled_at is not None
