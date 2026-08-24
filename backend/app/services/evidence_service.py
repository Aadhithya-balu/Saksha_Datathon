import os
import uuid
import json
from typing import Any
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
from PIL import Image
from PyPDF2 import PdfReader
from pymediainfo import MediaInfo

from app.models.evidence import Evidence
from app.models.evidence_metadata import EvidenceMetadata
from app.models.evidence_timeline import EvidenceTimeline
from app.models.evidence_assignment import EvidenceAssignment
from app.models.chain_of_custody import ChainOfCustody
from app.models.user import User
from app.core.config import BACKEND_DIR, settings

# ---------------------------------------------------------------------------
# Upload directory — used only when Supabase Storage is not configured.
# Defaults to <backend_dir>/uploads so the path is correct both locally
# (backend/uploads/) and inside the Docker container (/app/uploads/).
# ---------------------------------------------------------------------------
_custom_upload_dir = settings.UPLOAD_DIR.strip() if settings.UPLOAD_DIR else ""
UPLOAD_DIR = Path(_custom_upload_dir) if _custom_upload_dir else Path(BACKEND_DIR) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "video/mp4", "video/x-matroska", "video/quicktime",
    "audio/mpeg", "audio/wav", "audio/ogg",
    "application/pdf", "text/plain"
}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mkv", ".mov", ".mp3", ".wav", ".ogg", ".pdf", ".txt"}
MAX_FILE_SIZE_MB = 50

def validate_upload_file(file: UploadFile):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext}")
    
    # We validate size after reading/saving, or by checking content-length header (but header is spoofable)
    # So size validation will happen during save_upload_file


def extract_metadata(file_path: str, mime_type: str) -> dict[str, Any]:
    metadata = {}
    try:
        if mime_type.startswith("image/"):
            with Image.open(file_path) as img:
                metadata = {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode
                }
                # Try getting basic exif if exists
                if hasattr(img, "_getexif") and img._getexif():
                    metadata["has_exif"] = True
        elif mime_type.startswith("video/") or mime_type.startswith("audio/"):
            media_info = MediaInfo.parse(file_path)
            for track in media_info.tracks:
                if track.track_type == "Video":
                    metadata.update({
                        "duration_seconds": track.duration / 1000 if track.duration else None,
                        "fps": track.frame_rate,
                        "width": track.width,
                        "height": track.height,
                        "codec": track.codec_id
                    })
                elif track.track_type == "Audio" and not mime_type.startswith("video/"):
                    metadata.update({
                        "duration_seconds": track.duration / 1000 if track.duration else None,
                        "bitrate": track.bit_rate,
                        "codec": track.codec_id
                    })
        elif mime_type == "application/pdf":
            reader = PdfReader(file_path)
            metadata = {
                "pages": len(reader.pages)
            }
            if reader.metadata:
                metadata.update({
                    "author": reader.metadata.author,
                    "creator": reader.metadata.creator,
                    "subject": reader.metadata.subject,
                    "title": reader.metadata.title
                })
    except Exception as e:
        metadata["extraction_error"] = str(e)
    
    return metadata

def _upload_to_supabase_storage(file_path: str, storage_key: str, mime_type: str) -> str | None:
    """Upload a local file to Supabase Storage and return the public/signed URL.

    Returns None when Supabase Storage is not configured or the upload fails,
    so the caller can fall back to serving from the local path.
    """
    bucket = (settings.SUPABASE_STORAGE_BUCKET or "").strip()
    url = (settings.SUPABASE_URL or "").strip()
    key = (settings.SUPABASE_ANON_KEY or "").strip()
    if not (bucket and url and key):
        return None
    try:
        import httpx
        with open(file_path, "rb") as fh:
            data = fh.read()
        upload_url = f"{url}/storage/v1/object/{bucket}/{storage_key}"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": mime_type,
            "x-upsert": "true",
        }
        resp = httpx.post(upload_url, content=data, headers=headers, timeout=60)
        if resp.status_code in (200, 201):
            return f"{url}/storage/v1/object/public/{bucket}/{storage_key}"
    except Exception:  # noqa: BLE001 — storage failure must not break the upload flow
        pass
    return None


def save_upload_file(upload_file: UploadFile, evidence_id: uuid.UUID) -> tuple[str, str | None]:
    """Save an uploaded file locally (for metadata extraction) and optionally
    push it to Supabase Storage for persistent cloud access.

    Returns ``(local_file_path, storage_url)`` where *storage_url* is the
    Supabase Storage URL when the upload succeeded, or ``None`` when running
    in local-only mode.
    """
    validate_upload_file(upload_file)

    file_ext = os.path.splitext(upload_file.filename)[1].lower()
    unique_filename = f"{evidence_id}_{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename

    file_size = 0
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024

    try:
        with open(file_path, "wb") as buffer:
            while chunk := upload_file.file.read(1024 * 1024):
                file_size += len(chunk)
                if file_size > max_bytes:
                    buffer.close()
                    os.remove(file_path)
                    raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB.")
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    mime_type = upload_file.content_type or "application/octet-stream"
    storage_key = f"evidence/{evidence_id}/{unique_filename}"
    storage_url = _upload_to_supabase_storage(str(file_path), storage_key, mime_type)

    # When the file is safely in Supabase Storage, remove the local copy to
    # avoid accumulating files on ephemeral server storage.
    if storage_url:
        try:
            os.remove(file_path)
        except OSError:
            pass

    return str(file_path), storage_url

def add_timeline_event(db: Session, evidence_id: uuid.UUID, action: str, current_user: User, description: str = None):
    event = EvidenceTimeline(
        evidence_id=evidence_id,
        action=action,
        performed_by=current_user.full_name or current_user.username,
        role=current_user.role.name,
        description=description
    )
    db.add(event)
    db.commit()

def generate_ai_summary(evidence: Evidence, metadata: EvidenceMetadata, timeline: list[EvidenceTimeline], assignments: list[EvidenceAssignment] = None, custody: list[ChainOfCustody] = None) -> str:
    summary = f"**Digital Evidence Dossier:** {evidence.title}\n"
    summary += f"**Type:** {evidence.evidence_type} | **Status:** {evidence.status}\n"
    summary += f"**Description:** {evidence.description or 'No description provided.'}\n\n"
    
    if metadata:
        summary += "### Extracted Metadata\n"
        summary += f"- **File:** {metadata.filename} ({metadata.mime_type})\n"
        summary += f"- **Size:** {round(metadata.filesize / 1024 / 1024, 2)} MB\n"
        if metadata.extracted_data:
            summary += "- **Attributes:** " + json.dumps(metadata.extracted_data) + "\n"
        summary += "\n"
        
    if assignments and len(assignments) > 0:
        summary += "### Assignment History\n"
        for a in assignments:
            status_text = a.status
            if a.completed_at:
                status_text = 'Completed'
            elif a.accepted_at:
                status_text = 'In Progress'
            summary += f"- Assigned to UUID {a.assigned_to} (Status: {status_text})\n"
        summary += "\n"
        
    if custody and len(custody) > 0:
        summary += "### Chain of Custody\n"
        summary += f"Documented transfers: {len(custody)}\n"
        for c in custody[:3]:
            summary += f"- {c.action} on {c.timestamp.strftime('%Y-%m-%d %H:%M')} (To UUID {c.to_user})\n"
        if len(custody) > 3:
            summary += f"- ...and {len(custody) - 3} more records.\n"
        summary += "\n"
        
    summary += "### Timeline Overview\n"
    summary += f"Total registered events: {len(timeline)}.\n"
    if timeline:
        first_event = timeline[-1] # Assuming timeline is ordered desc, last is first chronologically
        last_event = timeline[0]
        summary += f"First recorded activity: {first_event.action} by {first_event.performed_by}\n"
        summary += f"Most recent activity: {last_event.action} by {last_event.performed_by}\n"

    summary += "\n*Note: This dossier was automatically assembled by the AI Evidence System.*"
    return summary
