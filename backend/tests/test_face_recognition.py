"""Face-recognition tests (Issue #228) — isolated DEMO enhancement.

Each test uses the shared in-memory SQLite fixtures and authenticates via
``/api/v2/auth/login`` (the same pattern as test_auth.py). The demo dataset is
pre-generated on disk under ``backend/uploads/face_demo_dataset``; tests read
those reference images, so the suite stays self-contained and never requires
external Zoho services (the Zoho adapter must degrade gracefully when absent).

Authentication helper:
    * seed an admin login
    * POST /api/v2/auth/login -> access_token
    * use Authorization: Bearer <token>
"""
import io
from pathlib import Path

import pytest
from PIL import Image

from app.ai.face import synthetic, zoho_adapter
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User


def _dataset_root() -> Path:
    return Path(synthetic.default_dataset_root())


def _demo_image_bytes(demo_id: str, variation: str = "frontal") -> bytes:
    root = _dataset_root()
    # Variations actual filenames may vary; pick the requested one or any png.
    target = root / demo_id / f"{variation}.png"
    if target.exists():
        return target.read_bytes()
    candidates = sorted((root / demo_id).glob("*.png")) if (root / demo_id).exists() else []
    if not candidates:
        pytest.skip(f"no demo images for {demo_id}")
    return candidates[0].read_bytes()


def _solid_color_bytes(rgb=(70, 90, 120), size=(200, 200)) -> bytes:
    img = Image.new("RGB", size, rgb)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _seed_and_login(client, db_session) -> str:
    role = Role(name="admin", description="Administrator")
    db_session.add(role)
    db_session.flush()
    user = User(
        username="faceadmin",
        email="faceadmin@example.com",
        full_name="Face Admin",
        hashed_password=hash_password("Password123!"),
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    r = client.post(
        "/api/v2/auth/login", json={"username": "faceadmin", "password": "Password123!"}
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------- #
# Auth gating
# --------------------------------------------------------------------------- #
def test_recognize_requires_auth(client):
    r = client.post(
        "/api/v2/face-recognition/recognize",
        files={"file": ("f.png", _solid_color_bytes(), "image/png")},
    )
    assert r.status_code == 401


def test_identities_requires_auth(client):
    assert client.get("/api/v2/face-recognition/identities").status_code == 401


# --------------------------------------------------------------------------- #
# Happy paths
# --------------------------------------------------------------------------- #
def test_recognize_matches_demo_person(client, db_session):
    token = _seed_and_login(client, db_session)
    data = _demo_image_bytes("DEMO-001")
    r = client.post(
        "/api/v2/face-recognition/recognize",
        files={"file": ("f.png", data, "image/png")},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "match"
    assert body["match_found"] is True
    assert body["matched_person"]["id"] == "DEMO-001"
    assert body["confidence"] is not None


def test_ai_identify_returns_rule_based_answer(client, db_session):
    token = _seed_and_login(client, db_session)
    data = _demo_image_bytes("DEMO-001")
    r = client.post(
        "/api/v2/face-recognition/ai/identify",
        files={"file": ("f.png", data, "image/png")},
        data={"question": "Who is this person?"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["engine"] == "rule-based"
    assert body["answer"]
    assert "DEMO-001" in body["answer"]
    assert body["recognition"]["status"] == "match"


def test_identities_and_samples(client, db_session):
    token = _seed_and_login(client, db_session)
    ids = client.get(
        "/api/v2/face-recognition/identities", headers=_auth(token)
    )
    samples = client.get(
        "/api/v2/face-recognition/samples", headers=_auth(token)
    )
    assert ids.status_code == 200
    assert samples.status_code == 200
    assert ids.json()  # non-empty demo set
    assert samples.json()  # non-empty gallery


# --------------------------------------------------------------------------- #
# Negative / robustness
# --------------------------------------------------------------------------- #
def test_recognize_solid_color_no_match(client, db_session):
    token = _seed_and_login(client, db_session)
    data = _solid_color_bytes()
    r = client.post(
        "/api/v2/face-recognition/recognize",
        files={"file": ("f.png", data, "image/png")},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["match_found"] is False


def test_recognize_rejects_invalid_content(client, db_session):
    token = _seed_and_login(client, db_session)
    r = client.post(
        "/api/v2/face-recognition/recognize",
        files={"file": ("f.txt", b"definitely not an image" * 40, "image/png")},
        headers=_auth(token),
    )
    # Content-type says PNG but bytes are not PNG -> 400 from the service.
    assert r.status_code == 400


def test_recognize_rejects_unsupported_mime(client, db_session):
    token = _seed_and_login(client, db_session)
    r = client.post(
        "/api/v2/face-recognition/recognize",
        files={"file": ("f.bmp", _solid_color_bytes(), "image/bmp")},
        headers=_auth(token),
    )
    assert r.status_code == 400


def test_recognize_rejects_empty_file(client, db_session):
    token = _seed_and_login(client, db_session)
    r = client.post(
        "/api/v2/face-recognition/recognize",
        files={"file": ("f.png", b"", "image/png")},
        headers=_auth(token),
    )
    assert r.status_code == 400


# --------------------------------------------------------------------------- #
# Zoho adapter — graceful degradation (unit)
# --------------------------------------------------------------------------- #
def test_zoho_adapter_degrades_without_sdk():
    adapter = zoho_adapter.ZohoFaceAdapter()
    # In a non-Catalyst runtime the adapter must report unavailable and return
    # used=False (never raising), so the service falls back to the local engine.
    assert adapter.available is False
    res = adapter.analyze(b"not-an-image")
    assert res.used is False
    assert res.faces_detected == 0
    cmp = adapter.compare(b"a", b"b")
    assert cmp.used is False
    assert cmp.matched is False
