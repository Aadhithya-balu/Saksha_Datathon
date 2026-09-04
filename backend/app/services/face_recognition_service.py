"""Face-recognition service (Issue #228) — isolated DEMO capability.

Responsibilities:
  * validate & sanitize the uploaded query image (format + size + content);
  * detect the number of faces and extract per-face info;
  * run face analysis via the selected provider (Zoho Zia when available and
    configured, else the bundled local engine);
  * compare the query embedding against the registered DEMO dataset and return
    the best candidate with a similarity score subject to a configurable
    threshold;
  * return "No confident match" below threshold — never a fabricated identity.

This service never touches crime-case/FIR/evidence/investigation tables and
keeps raw facial images out of logs and out of the database.
"""
from __future__ import annotations

import io

import numpy as np
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.ai.face import local_engine, repository, zoho_adapter
from app.core.config import settings
from app.core.logging_config import logger
from app.models.face_identity import FaceIdentity  # noqa: F401  (documented)
from sqlalchemy.orm import Session

_ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
_MAGIC = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),
]


class FaceProcessingError(Exception):
    """Invalid/unprocessable query image."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def feature_enabled() -> bool:
    return bool(settings.FACE_RECOGNITION_ENABLED)


def _detect_mime(data: bytes) -> str | None:
    for magic, mime in _MAGIC:
        if data[: len(magic)] == magic:
            if mime == "image/webp" and data[8:12] != b"WEBP":
                continue
            return mime
    return None


def _validate_image(file: UploadFile) -> bytes:
    max_bytes = max(1, int(settings.FACE_MAX_IMAGE_BYTES or 10 * 1024 * 1024))

    # Reject unsupported declared content-type up front.
    if file.content_type not in _ALLOWED_MIME:
        raise FaceProcessingError(
            "Unsupported image format. Only JPEG, PNG, and WebP are accepted for face recognition."
        )

    data = file.file.read(max_bytes + 1)
    if not data:
        raise FaceProcessingError("Empty file. Please upload a valid image.")
    if len(data) > max_bytes:
        raise FaceProcessingError("Image exceeds the maximum allowed size (10 MB).")
    if len(data) < 256:
        raise FaceProcessingError("File is too small to be a face image.")

    # Verify magic bytes to prevent content-type spoofing / path traversal.
    detected = _detect_mime(data)
    if detected is None:
        raise FaceProcessingError("File content does not match a supported image format.")
    if detected != file.content_type:
        raise FaceProcessingError("Declared content-type does not match the actual file content.")

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            width, height = image.size
        if width < 24 or height < 24:
            raise FaceProcessingError("Image is too small to analyse for faces.")
    except (UnidentifiedImageError, OSError, ValueError):
        raise FaceProcessingError("The uploaded file is not a valid image.") from None

    # Do not retain a copy of the raw image beyond the memory needed for analysis.
    return data


def _run_zoho_analysis(data: bytes) -> zoho_adapter.ZohoFaceAnalysis | None:
    adapter = zoho_adapter.get_zoho_adapter()
    if not adapter.available:
        return None
    if settings.FACE_RECOGNITION_PROVIDER not in ("zoho", "auto", "local", ""):
        return None
    return adapter.analyze(data)


def _provider_name() -> str:
    provider = (settings.FACE_RECOGNITION_PROVIDER or "auto").strip().lower()
    if provider == "local":
        return "local"
    if provider == "zoho":
        if zoho_adapter.get_zoho_adapter().available:
            return "zoho"
        return "local"
    # auto: prefer zoho if available
    if zoho_adapter.get_zoho_adapter().available:
        return "zoho"
    return "local"


def recognize(file: UploadFile) -> dict:
    """Full recognition pipeline for one uploaded query image."""
    if not feature_enabled():
        return {
            "status": "disabled",
            "faces_detected": 0,
            "match_found": False,
            "matched_person": None,
            "message": "Face recognition is disabled on this deployment.",
        }

    data = _validate_image(file)
    return recognize_bytes(data)


def recognize_bytes(data: bytes) -> dict:
    """Recognition pipeline over raw validated image bytes (used by routes & AI)."""
    # 1. Detect faces.
    count, faces = local_engine.detect_faces(data)
    if count == 0 or not faces:
        return {
            "status": "no_face",
            "faces_detected": 0,
            "match_found": False,
            "matched_person": None,
            "message": "No face detected in the uploaded image.",
        }

    # 2. Run analysis (Zoho when available, else local estimates).
    analysis_payload = _run_zoho_analysis(data)
    if analysis_payload is not None and analysis_payload.used:
        analysis = _analysis_summary(analysis_payload)
        analysis_source = "zoho"
    else:
        analysis = _local_analysis(data, faces)
        analysis_source = "local"

    # 3. Embedding for the primary face.
    query_embedding = local_engine.embedding_from_region(faces[0]["region_gray"])

    # 4. Compare against DEMO dataset.
    return _build_result(count, query_embedding, analysis, analysis_source)


def _build_result(count: int, query_embedding, analysis: dict, analysis_source: str, references=None) -> dict:
    if references is None:
        # Reference set resolved from disk (no DB dependency for pure matching);
        # the repository uses the seeded identity rows for metadata fallback.
        references = repository.reference_embeddings_from_disk() or []

    if query_embedding is None or not references:
        # Recognizer can't match (no reference set) — honest no-match.
        result = {
            "status": "no_reference",
            "faces_detected": count,
            "match_found": False,
            "matched_person": None,
            "message": "No confident match found in the demo dataset.",
            "analysis": analysis,
            "analysis_source": analysis_source,
        }
        if query_embedding is not None:
            result["best_score"] = 0.0
        return result

    best, score = repository.match_best(query_embedding, references)
    threshold = float(settings.FACE_MATCH_THRESHOLD or 0.60)

    if best is None or score < threshold:
        return {
            "status": "no_match",
            "faces_detected": count,
            "match_found": False,
            "matched_person": None,
            "message": "No confident match found in the demo dataset.",
            "best_score": round(score, 4),
            "analysis": analysis,
            "analysis_source": analysis_source,
            "threshold": round(threshold, 4),
        }

    # Enrich the analysis with known descriptive traits for the matched DEMO
    # identity so the result shows a real gender / age estimate instead of a
    # placeholder, while staying clearly prototype-labelled.
    from app.ai.face import synthetic as face_synthetic

    matched = {
        "id": best["id"],
        "name": best["name"],
        "dataset_type": "DEMO",
    }
    meta = face_synthetic.identity_meta(best["id"])
    if meta and analysis_source == "local":
        enriched = dict(analysis)
        if not enriched.get("gender"):
            enriched["gender"] = meta["gender"]
        if not enriched.get("age"):
            enriched["age"] = str(meta["age"])
        analysis = enriched

    return {
        "status": "match",
        "faces_detected": count,
        "match_found": True,
        "matched_person": matched,
        "confidence": round(score, 4),
        "analysis": analysis,
        "analysis_source": analysis_source,
        "threshold": round(threshold, 4),
    }


def _analysis_summary(payload: zoho_adapter.ZohoFaceAnalysis) -> dict:
    def first(lst):
        return lst[0] if lst else None

    return {
        "age": first(payload.ages),
        "gender": first(payload.genders),
        "emotion": first(payload.emotions),
        "faces": payload.faces_detected,
    }


def _local_analysis(data: bytes, faces) -> dict:
    """Lightweight heuristic analysis for the DEMO pipeline.

    The local engine performs detection only (no biometric attribute models), so
    per-face gender/age are not inferred here. When a confident DEMO match is
    found, the matched identity's known traits are injected in ``_build_result``;
    otherwise the attribute fields stay None (frontend hides empty boxes).
    """
    return {
        "age": None,
        "gender": None,
        "emotion": None,
        "faces": len(faces),
    }


def sample_bytes(ref: str) -> bytes | None:
    """Return stored demo sample bytes by logical ref (internal)."""
    return repository.resolve_image_bytes(ref)


def ai_answer(result: dict, question: str | None = None) -> str:
    """Build an honest, prototype-labelled natural-language answer for the AI flow.

    Never claims a weak/uncertain match is a verified identity.
    """
    question_norm = (question or "").strip().lower()
    wants_identity = any(w in question_norm for w in ("who", "identify", "person", "match", "is this"))
    if result.get("match_found") and result.get("matched_person"):
        person = result["matched_person"]
        score = result.get("confidence")
        score_txt = f"{round(score * 100):.0f}%" if score is not None and score is not False else "high"
        if wants_identity:
            return (
                f"Face detected. The closest match in the authorized DEMO dataset is "
                f"{person['id']} ({person['name']}) with a similarity score of {score_txt}. "
                "This is a prototype match, not a verified real-world identification."
            )
        return (
            f"Reliable {score_txt} similarity to {person['id']} ({person['name']}) in the "
            "DEMO dataset. Prototype match only — not a verified real-world identification."
        )
    if result.get("faces_detected", 0) == 0:
        return "No face was detected in the provided image, so no identity comparison was possible."
    msg = result.get("message") or "No confident match found in the demo dataset."
    return (
        f"Face detected, but {msg}. The DEMO dataset does not confidently match this face — "
        "no identity is being claimed."
    )
