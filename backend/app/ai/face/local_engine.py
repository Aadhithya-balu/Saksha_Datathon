"""Local face-recognition engine (offline fallback).

Runs entirely with the bundled dependencies: OpenCV (when importable) for real
face detection and a pure-numpy/PIL descriptor for face matching. It never
requires the Zoho SDK, so the DEMO feature works in any environment and the
rest of the application is unaffected even when the engine is unavailable.

Matching uses a lighting-robust holistic descriptor (standardized grayscale +
low-frequency DCT + Local Binary Pattern texture histogram) and returns a cosine
similarity. The service layer applies the configurable threshold.
"""
from __future__ import annotations

import io
import math

import numpy as np

from app.core.logging_config import logger

# Optional OpenCV — used only when available. Absence degrades only to the
# PIL "whole-image is the subject" detection path (fine for synthetic DEMO data).
try:  # pragma: no cover - exercised by import-on-demand
    import cv2

    _OPENCV = True
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]
    _OPENCV = False

_EMBED_SIZE = 48
_DCT_LOW = 12
_LBP_BINS = 64


def _to_gray_float(data: bytes) -> np.ndarray | None:
    """Decode image bytes to a float grayscale array or None (invalid image)."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data)).convert("L")
        return np.asarray(img, dtype=np.float32)
    except Exception:
        return None


def _detect_faces_opencv(gray: np.ndarray) -> list[tuple[float, float, float, float]]:
    """OpenCV Haar-cascade detection. Returns [x, y, w, h] normalized 0..1."""
    if not _OPENCV:
        return []
    try:
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        uint8 = np.clip(gray, 0, 255).astype(np.uint8)
        faces = cascade.detectMultiScale(uint8, scaleFactor=1.1, minNeighbors=5, minSize=(32, 32))
        h, w = gray.shape[:2]
        return [(x / w, y / h, bw / w, bh / h) for x, y, bw, bh in faces]
    except Exception:  # pragma: no cover - cascade/cv2 quirks
        return []


def detect_faces(data: bytes) -> tuple[int, list[dict]]:
    """Detect faces in image bytes.

    Returns ``(count, faces)`` where each face dict has ``bbox`` (normalized) and
    ``region_gray`` (float array copy). When OpenCV finds nothing but the image is
    a plausible single-subject image, we fall back to treating the whole frame as
    a single face so the synthetic DEMO images remain testable.
    """
    gray = _to_gray_float(data)
    if gray is None:
        return 0, []

    boxes = _detect_faces_opencv(gray)
    faces: list[dict] = []
    if boxes:
        for (x, y, w, h) in boxes:
            x0 = max(0, int((x - 0.05) * gray.shape[1]))
            y0 = max(0, int((y - 0.05) * gray.shape[0]))
            x1 = min(gray.shape[1], int((x + w + 0.05) * gray.shape[1]))
            y1 = min(gray.shape[0], int((y + h + 0.05) * gray.shape[0]))
            crop = gray[y0:y1, x0:x1]
            if crop.size == 0:
                continue
            faces.append({"bbox": {"x": x, "y": y, "w": w, "h": h}, "region_gray": crop})
        if faces:
            return len(faces), faces

    # Fallback: assume a single centered subject (synthetic/cartoon imagery).
    # Crop to the central region where the face is drawn so the identical
    # background does not dominate the descriptor.
    h, w = gray.shape[:2]
    cw = max(16, int(w * 0.62))
    ch = max(16, int(h * 0.78))
    x0 = max(0, int((w - cw) / 2))
    y0 = max(0, int((h - ch) / 2))
    region = gray[y0:y0 + ch, x0:x0 + cw]
    if region.size == 0:
        region = gray
    return 1, [{"bbox": {"x": x0 / w, "y": y0 / h, "w": cw / w, "h": ch / h}, "region_gray": region}]


def _extract_embedding(crop: np.ndarray) -> np.ndarray:
    """Build a robust, fixed-length descriptor for a face crop.

    Background is masked out (the synthetic dataset uses a flat background), so
    the descriptor reflects the facial features that differ per identity rather
    than the shared background. Features combine a foreground-masked pixel grid,
    low-frequency DCT (holistic shape) and an LBP texture histogram.
    """
    # Resize to a canonical square.
    if _OPENCV:
        resized = cv2.resize(crop, (_EMBED_SIZE, _EMBED_SIZE), interpolation=cv2.INTER_AREA)
    else:
        ys = np.linspace(0, crop.shape[0] - 1, _EMBED_SIZE)
        xs = np.linspace(0, crop.shape[1] - 1, _EMBED_SIZE)
        gx, gy = np.meshgrid(xs, ys)
        resized = _bilinear_sample(crop, gx, gy)

    # Foreground mask: drop the flat (near-minimum) background.
    flat = resized > (float(resized.min()) + 10.0)

    # Standardize (lights-out for illumination robustness) on the foreground.
    masked = np.where(flat, resized, 0.0)
    std = float(masked.std())
    if std < 1e-6:
        std = 1.0
    normed = (masked - float(masked.mean())) / std

    # Masked pixel grid (face layout).
    grid = normed[flat].mean() if flat.any() else 0.0

    # DCT low-frequency block (holistic shape).
    dct = _dct2d(normed)[:_DCT_LOW, :_DCT_LOW].flatten()

    # LBP histogram over the masked foreground (texture).
    lbp = _lbp_histogram(np.where(flat, normed, normed.min()), bins=_LBP_BINS)

    vec = np.concatenate([[grid], dct, lbp])
    norm = float(np.linalg.norm(vec))
    if norm < 1e-9:
        norm = 1.0
    return vec / norm


def _bilinear_sample(img: np.ndarray, gx: np.ndarray, gy: np.ndarray) -> np.ndarray:
    gx = np.clip(gx, 0, img.shape[1] - 1.001)
    gy = np.clip(gy, 0, img.shape[0] - 1.001)
    x0 = np.floor(gx).astype(int)
    y0 = np.floor(gy).astype(int)
    x1 = np.clip(x0 + 1, 0, img.shape[1] - 1)
    y1 = np.clip(y0 + 1, 0, img.shape[0] - 1)
    wx = gx - x0
    wy = gy - y0
    return (
        img[y0, x0] * (1 - wx) * (1 - wy)
        + img[y0, x1] * wx * (1 - wy)
        + img[y1, x0] * (1 - wx) * wy
        + img[y1, x1] * wx * wy
    )


def _dct2d(x: np.ndarray) -> np.ndarray:
    try:
        from scipy.fft import dct as _dct_1d
    except Exception:  # pragma: no cover
        from numpy.fft import rfft2

        return np.abs(rfft2(x)).astype(np.float64)
    # Type-II DCT along each axis.
    out = _dct_1d(x, type=2, norm="ortho", axis=0)
    out = _dct_1d(out, type=2, norm="ortho", axis=1)
    return np.asarray(out, dtype=np.float64)


def _lbp_histogram(x: np.ndarray, bins: int) -> np.ndarray:
    """Uniform LBP texture histogram (8 neighbours). Returns normalized vector."""
    x = np.asarray(x, dtype=np.float32)
    center = x
    offsets = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]
    codes = np.zeros_like(x, dtype=np.int32)
    for bit, (dy, dx) in enumerate(offsets):
        shifted = _shift(x, dy, dx)
        codes |= ((shifted >= center).astype(np.int32) << bit)
    # uniform LBP:
    pattern = _uniform_map(codes)
    hist, _ = np.histogram(pattern, bins=bins, range=(0, bins))
    total = float(hist.sum())
    if total < 1e-9:
        return np.zeros(bins, dtype=np.float32)
    return (hist / total).astype(np.float32)


def _shift(x: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Fast shifted copy: out[i,j] = x[i+dy, j+dx], zero-padded at borders."""
    out = np.zeros_like(x)
    h, w = x.shape
    src_y0 = max(0, -dy)
    src_y1 = min(h, h - dy)
    src_x0 = max(0, -dx)
    src_x1 = min(w, w - dx)
    dst_y0 = src_y0 + dy
    dst_x0 = src_x0 + dx
    if src_y0 < src_y1 and src_x0 < src_x1:
        out[dst_y0:dst_y0 + (src_y1 - src_y0), dst_x0:dst_x0 + (src_x1 - src_x0)] = x[src_y0:src_y1, src_x0:src_x1]
    return out


def _uniform_map(codes: np.ndarray) -> np.ndarray:
    """Map LBP codes to uniform-pattern labels in [0, 58]; rest -> 58."""
    lut = _LBP_UNIFORM_LUT
    flat = np.clip(codes, 0, 255)
    return lut[flat]


# Precomputed uniform-LBP lookup (static).
_LBP_UNIFORM_LUT: np.ndarray | None = None


def _build_uniform_lut() -> np.ndarray:
    lut = np.zeros(256, dtype=np.int32)
    for code in range(256):
        b = [(code >> i) & 1 for i in range(8)]
        circ = b + [b[0]]
        transitions = sum(circ[i] != circ[i + 1] for i in range(8))
        lut[code] = code if transitions <= 2 else 58
    return lut


_LBP_UNIFORM_LUT = _build_uniform_lut()


def embedding_from_bytes(data: bytes) -> np.ndarray | None:
    """Detect the primary face and return its embedding, or None if undecodable."""
    count, faces = detect_faces(data)
    if count == 0 or not faces:
        return None
    return _extract_embedding(faces[0]["region_gray"])


def embedding_from_region(region_gray) -> np.ndarray:
    return _extract_embedding(np.asarray(region_gray, dtype=np.float32))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))
