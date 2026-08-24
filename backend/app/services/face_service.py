"""Issue #118 — Server-side face verification service.

Pipeline
--------
1. Decode the base64 JPEG frame sent from the browser.
2. Detect faces using a Haar cascade (OpenCV, already available via opencv-python-headless).
3. Crop + resize the detected face region to a fixed 64×64 patch.
4. Flatten the grayscale patch into a compact feature vector (4096-dim float32).
5. L2-normalise the vector.
6. Compare against enrolled officer embeddings stored in the database using
   cosine similarity (numpy dot product of two unit vectors).
7. Return the best-matching officer if similarity ≥ FACE_MATCH_THRESHOLD.

Security notes
--------------
* Embeddings are NEVER returned to the frontend.
* The raw frame is discarded immediately after processing.
* Only officers with face_enabled=True and a non-null face_embedding are eligible.
* Inactive officers (status != 'active') are rejected even on a valid match.

Limitations / anti-spoofing
----------------------------
This implementation uses a simple pixel-histogram embedding, not a deep neural
network descriptor.  It is sufficient for a prototype but does NOT provide
liveness detection.  The FACE_MATCH_THRESHOLD is intentionally conservative
(0.92) to reduce false positives.  A production deployment should replace the
embedding step with a proper face-recognition model (e.g. dlib / InsightFace)
and add liveness checks.
"""
from __future__ import annotations

import base64
import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.officer import Officer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FACE_MATCH_THRESHOLD: float = 0.92   # cosine similarity; tune as needed
EMBEDDING_VERSION: str = "v1-pixel64"
_PATCH_SIZE: int = 64                # face crop size before flattening

# ---------------------------------------------------------------------------
# Haar cascade — loaded lazily so the import doesn't fail if cv2 is absent
# ---------------------------------------------------------------------------
_cascade = None


def _get_cascade():
    global _cascade
    if _cascade is not None:
        return _cascade
    try:
        import cv2  # noqa: PLC0415
        _cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        return _cascade
    except Exception as exc:
        logger.warning("OpenCV not available; face detection disabled: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _embed_face_patch(patch_gray: "np.ndarray") -> np.ndarray:
    """Resize patch to _PATCH_SIZE×_PATCH_SIZE, flatten, L2-normalise."""
    from PIL import Image as _Image  # noqa: PLC0415
    img = _Image.fromarray(patch_gray).resize((_PATCH_SIZE, _PATCH_SIZE), _Image.LANCZOS)
    vec = np.array(img, dtype=np.float32).flatten()
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def embedding_to_json(vec: np.ndarray) -> str:
    return json.dumps(vec.tolist())


def embedding_from_json(s: str) -> np.ndarray:
    return np.array(json.loads(s), dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))  # both are already L2-normalised


# ---------------------------------------------------------------------------
# Face detection from a raw image (PIL or numpy)
# ---------------------------------------------------------------------------

@dataclass
class DetectionResult:
    face_count: int
    patch_gray: "np.ndarray | None" = None   # single detected face patch
    error: str | None = None


def detect_face(image: Image.Image) -> DetectionResult:
    """Detect faces in *image*.

    Returns DetectionResult with:
    - face_count == 0  → no face found
    - face_count == 1  → exactly one face; patch_gray is the cropped region
    - face_count > 1   → multiple faces; patch_gray is None
    """
    cascade = _get_cascade()
    if cascade is None:
        # OpenCV unavailable — fall back to a simple centre-crop heuristic
        # so the rest of the pipeline still works in minimal environments.
        gray = np.array(image.convert("L"), dtype=np.uint8)
        h, w = gray.shape
        margin_y, margin_x = h // 4, w // 4
        patch = gray[margin_y: h - margin_y, margin_x: w - margin_x]
        return DetectionResult(face_count=1, patch_gray=patch)

    import cv2  # noqa: PLC0415
    gray = np.array(image.convert("L"), dtype=np.uint8)
    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60),
    )
    if len(faces) == 0:
        return DetectionResult(face_count=0)
    if len(faces) > 1:
        return DetectionResult(face_count=len(faces))

    x, y, w, h = faces[0]
    patch = gray[y: y + h, x: x + w]
    return DetectionResult(face_count=1, patch_gray=patch)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class VerifyResult:
    success: bool
    officer_id: str | None = None
    badge_number: str | None = None
    name: str | None = None
    rank: str | None = None
    role: str | None = None
    error_code: str | None = None   # NO_FACE | MULTI_FACE | NO_MATCH | INACTIVE | NO_ENROLLMENT | BAD_IMAGE


def verify_face_from_b64(db: "Session", image_b64: str) -> VerifyResult:
    """Full face-verification pipeline.

    1. Decode base64 frame.
    2. Detect face.
    3. Generate embedding.
    4. Compare against enrolled officers.
    5. Return VerifyResult.
    """
    # --- decode frame ---
    try:
        # Strip data-URI prefix if present
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]
        raw = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        logger.warning("Face verify: could not decode image: %s", exc)
        return VerifyResult(success=False, error_code="BAD_IMAGE")

    # --- detect face ---
    det = detect_face(image)
    if det.face_count == 0:
        return VerifyResult(success=False, error_code="NO_FACE")
    if det.face_count > 1:
        return VerifyResult(success=False, error_code="MULTI_FACE")

    # --- generate embedding ---
    probe_vec = _embed_face_patch(det.patch_gray)

    # --- load enrolled officers ---
    from app.models.officer import Officer  # noqa: PLC0415
    candidates: list[Officer] = (
        db.query(Officer)
        .filter(
            Officer.face_enabled.is_(True),
            Officer.face_embedding.isnot(None),
            Officer.status == "active",
        )
        .all()
    )

    if not candidates:
        return VerifyResult(success=False, error_code="NO_ENROLLMENT")

    best_officer: Officer | None = None
    best_score: float = -1.0

    for officer in candidates:
        try:
            gallery_vec = embedding_from_json(officer.face_embedding)
            score = cosine_similarity(probe_vec, gallery_vec)
            if score > best_score:
                best_score = score
                best_officer = officer
        except Exception as exc:
            logger.warning("Face verify: bad embedding for officer %s: %s", officer.id, exc)

    if best_officer is None or best_score < FACE_MATCH_THRESHOLD:
        return VerifyResult(success=False, error_code="NO_MATCH")

    # --- update last verified timestamp ---
    try:
        best_officer.face_verified_at = datetime.now(timezone.utc)
        db.add(best_officer)
        db.commit()
    except Exception:
        db.rollback()

    role = best_officer.user.role.name if best_officer.user and best_officer.user.role else "officer"
    return VerifyResult(
        success=True,
        officer_id=str(best_officer.id),
        badge_number=best_officer.badge_number,
        name=best_officer.name,
        rank=best_officer.rank,
        role=role,
    )


def enroll_face_from_b64(db: "Session", officer_id: str, image_b64: str) -> dict:
    """Enroll (or re-enroll) a face for an officer.

    Called only from the admin-protected enroll endpoint.
    Returns a dict with 'success' and optional 'error'.
    """
    from app.models.officer import Officer  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415

    try:
        oid = _uuid.UUID(officer_id)
    except ValueError:
        return {"success": False, "error": "Invalid officer_id"}

    officer = db.query(Officer).filter(Officer.id == oid).first()
    if not officer:
        return {"success": False, "error": "Officer not found"}

    try:
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]
        raw = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        return {"success": False, "error": f"Could not decode image: {exc}"}

    det = detect_face(image)
    if det.face_count == 0:
        return {"success": False, "error": "No face detected in enrollment image"}
    if det.face_count > 1:
        return {"success": False, "error": "Multiple faces detected; use a single-person image"}

    vec = _embed_face_patch(det.patch_gray)
    officer.face_embedding = embedding_to_json(vec)
    officer.face_embedding_version = EMBEDDING_VERSION
    officer.face_enabled = True
    officer.face_enrolled_at = datetime.now(timezone.utc)
    db.add(officer)
    db.commit()
    return {"success": True, "officer_id": str(officer.id), "badge_number": officer.badge_number}
