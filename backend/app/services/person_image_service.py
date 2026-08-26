"""Persistent, validated profile-image storage for person records.

Profile images are stored in the configured Supabase bucket; database records
contain the returned storage URL.  There is deliberately no local-file fallback
in this service: a successful response always means the image survived outside
the application container.
"""
from __future__ import annotations

import io
import uuid

import httpx
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

MAX_PERSON_IMAGE_BYTES = 10 * 1024 * 1024
_ALLOWED = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

# Magic bytes for each allowed type — prevents content-type spoofing
_MAGIC: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),  # RIFF....WEBP
]


def _detect_mime(data: bytes) -> str | None:
    for magic, mime in _MAGIC:
        if data[:len(magic)] == magic:
            if mime == "image/webp" and data[8:12] != b"WEBP":
                continue
            return mime
    return None


def store_person_image(file: UploadFile, *, person_type: str, person_id: uuid.UUID) -> str:
    """Validate and persist one profile image, returning its Supabase URL."""
    if file.content_type not in _ALLOWED:
        raise HTTPException(400, "Only JPEG, PNG, and WebP images are accepted.")

    data = file.file.read(MAX_PERSON_IMAGE_BYTES + 1)
    if not data or len(data) > MAX_PERSON_IMAGE_BYTES:
        raise HTTPException(400, "Image must be between 1 byte and 10 MB.")

    # Verify actual file content matches declared content-type (path traversal / spoofing guard)
    detected = _detect_mime(data)
    if detected is None:
        raise HTTPException(400, "File content does not match a supported image format.")
    if detected != file.content_type:
        raise HTTPException(400, "Declared content-type does not match actual file content.")

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, "The uploaded file is not a valid image.") from exc

    base_url = (settings.SUPABASE_URL or "").rstrip("/")
    bucket = (settings.SUPABASE_STORAGE_BUCKET or "").strip()
    # The server-only service-role key is preferred.  An anon key is supported
    # only for deployments with an explicit insert policy for this bucket.
    token = (settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "").strip()
    if not (base_url and bucket and token):
        raise HTTPException(503, "Persistent image storage is not configured.")

    object_key = f"persons/{person_type}/{person_id}/{uuid.uuid4()}{_ALLOWED[file.content_type]}"
    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{base_url}/storage/v1/object/{bucket}/{object_key}",
                content=data,
                headers={"Authorization": f"Bearer {token}", "Content-Type": file.content_type, "x-upsert": "false"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Persistent image storage is unavailable.") from exc
    if response.status_code not in (200, 201):
        raise HTTPException(502, "Persistent image storage rejected the upload.")
    return f"{base_url}/storage/v1/object/public/{bucket}/{object_key}"
