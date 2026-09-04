"""Synthetic DEMO face dataset generator.

Produces clearly synthetic, fictional, consented demo subjects — never real
criminal photographs or scraped mugshots. Each of the 5 DEMO identities gets
4-5 image variations (frontal, side/angle, pose, lighting, expression) drawn
with PIL so the demo runs fully offline and is obviously non-real.

The parameter set for each identity controls the drawn face. Variations perturb
presentation (skew/rotate, brightness, expression) while preserving the
underlying identity so the recognition engine can be demonstrated end-to-end.
"""
from __future__ import annotations

import math
import os
import uuid
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageEnhance

# Image canvas size (square). Kept modest for speed and small dataset footprint.
SIZE = 160

# Canonical demo image variations (in generation order).
VARIATIONS: list[str] = ["frontal", "left-angle", "right-angle", "pose", "expression"]


@dataclass
class FaceSpec:
    """Parameters that define one synthetic identity's face."""

    demo_id: str
    display_name: str
    gender: str  # descriptive traits for the DEMO pipeline
    age: int
    skin: tuple[int, int, int]
    hair_color: tuple[int, int, int]
    hair_style: str  # "short" | "long" | "bald" | "bun"
    eye_color: tuple[int, int, int]
    eye_gap: float  # fraction of face width between eyes
    eye_size: float
    brow: float  # brow height offset
    nose: float  # nose length
    mouth: float  # mouth width


IDENTITIES: list[FaceSpec] = [
    # 5 clearly distinctive synthetic subjects — distinct haircuts, hair colours
    # and facial proportions, so the demo recognizer separates them cleanly.
    FaceSpec("DEMO-001", "Demo Person 1", "Male", 34, (226, 184, 148), (28, 24, 20), "short", (60, 60, 110), 0.46, 1.0, 0.72, 0.32, 0.5),
    FaceSpec("DEMO-002", "Demo Person 2", "Male", 58, (150, 108, 84), (16, 16, 20), "bald", (80, 110, 150), 0.30, 1.2, 0.82, 0.44, 0.56),
    FaceSpec("DEMO-003", "Demo Person 3", "Female", 27, (240, 210, 170), (158, 128, 64), "long", (110, 80, 70), 0.50, 0.9, 0.76, 0.30, 0.46),
    FaceSpec("DEMO-004", "Demo Person 4", "Female", 41, (140, 96, 76), (24, 40, 28), "bun", (60, 90, 130), 0.38, 1.08, 0.68, 0.38, 0.52),
    FaceSpec("DEMO-005", "Demo Person 5", "Male", 45, (208, 168, 148), (120, 46, 60), "short", (90, 70, 70), 0.42, 1.15, 0.78, 0.40, 0.62),
]


def _draw_face(spec: FaceSpec, *, variation: str, seed: int) -> Image.Image:
    """Draw one synthetic face. ``variation`` keys:
    frontal, left-angle, right-angle, pose, dim, bright, smile, sad, cls (closed eyes).
    Unknown keys default to 'frontal'.
    """
    w = h = SIZE
    img = Image.new("RGB", (w, h), (30, 34, 44))
    d = ImageDraw.Draw(img)

    cx, cy = w / 2, h / 2
    face_w = w * 0.62
    face_h = h * 0.72

    smile = "smile" == variation
    closed = variation == "cls"

    # === Face region (ellipse) ===
    # Deterministic pseudo-random via the seed; small per-variation jitter keeps
    # the same identity close together while differing across runs for angle.
    fx = cx
    fy = cy + h * 0.02
    face_bbox = [fx - face_w / 2, fy - face_h / 2, fx + face_w / 2, fy + face_h / 2]
    d.ellipse(face_bbox, fill=spec.skin)
    # Slight face outline for structure
    d.ellipse(face_bbox, outline=tuple(int(c * 0.7) for c in spec.skin), width=2)

    # === Hair ===
    hair_w = face_w * 1.05
    hair_h = face_h * 0.62
    top = fy - face_h / 2
    if spec.hair_style == "short":
        d.ellipse([cx - hair_w / 2, top - hair_h * 0.25, cx + hair_w / 2, top + hair_h * 0.75], fill=spec.hair_color)
    elif spec.hair_style == "long":
        d.rectangle([cx - hair_w / 2, top - hair_h * 0.3, cx + hair_w / 2, top + face_h * 0.9], fill=spec.hair_color)
        d.rounded_rectangle([cx - hair_w / 2, top - hair_h * 0.2, cx + hair_w / 2, top + face_h * 1.1], radius=20, fill=spec.hair_color)
    elif spec.hair_style == "bald":
        d.arc([cx - hair_w / 2, top - hair_h * 0.3, cx + hair_w / 2, top + hair_h * 0.5], start=180, end=360, fill=spec.hair_color, width=6)
    elif spec.hair_style == "bun":
        d.ellipse([cx - hair_w / 2, top - hair_h * 0.3, cx + hair_w / 2, top + hair_h * 0.6], fill=spec.hair_color)
        d.ellipse([cx - 14, top - 34, cx + 14, top - 6], fill=spec.hair_color)

    # === Eyes ===
    eye_y = cy - h * 0.05
    eye_dy = spec.eye_size * 4
    gap = spec.eye_gap * face_w
    eye_lx, eye_rx = cx - gap, cx + gap
    eye_w = spec.eye_size * 9
    eye_h = spec.eye_size * 5
    for ex in (eye_lx, eye_rx):
        offset = 1.5 if smile else 0.0
        d.ellipse([ex - eye_w / 2 + offset, eye_y - eye_h / 2, ex + eye_w / 2 + offset, eye_y + eye_h / 2], outline=(20, 20, 20), width=2)
        if closed:
            d.line([ex - eye_w / 2 + 2, eye_y, ex + eye_w / 2 - 2, eye_y], fill=(30, 30, 30), width=2)
        else:
            pup = spec.eye_color
            d.ellipse([ex - eye_w / 6, eye_y - eye_h / 6, ex + eye_w / 6, eye_y + eye_h / 3], fill=pup)

    # === Eyebrows ===
    brow_y = eye_y - eye_h
    for ex in (eye_lx, eye_rx):
        d.arc([ex - eye_w / 2 - 2, brow_y - 6, ex + eye_w / 2 + 2, brow_y + 4],
              start=180, end=360, fill=spec.hair_color, width=3)

    # === Nose ===
    nose_len = spec.nose * face_h
    d.line([cx, cy - h * 0.03, cx - 2, cy + nose_len * 0.5], fill=(140, 110, 90), width=3)

    # === Mouth ===
    mw = spec.mouth * face_w
    mouth_y = cy + h * 0.14
    if smile:
        d.arc([cx - mw / 2, mouth_y - 6, cx + mw / 2, mouth_y + 12], start=20, end=160, fill=(120, 60, 60), width=3)
    elif variation == "sad":
        d.arc([cx - mw / 2, mouth_y - 4, cx + mw / 2, mouth_y + 10], start=200, end=340, fill=(120, 60, 60), width=3)
    else:
        d.line([cx - mw / 2, mouth_y, cx + mw / 2, mouth_y], fill=(120, 60, 60), width=3)

    return img


def _apply_variation(img: Image.Image, variation: str) -> Image.Image:
    """Apply presentation-level perturbation: angle, pose, lighting, expression."""
    if variation.startswith("left"):
        # Gentle left lean (positive vertical shear); face stays framed.
        img = img.transform(img.size, Image.AFFINE, (1, 0.14, 0, 0, 1, 0))
    elif variation.startswith("right"):
        # Gentle right lean (negative vertical shear) — mirror of left.
        img = img.transform(img.size, Image.AFFINE, (1, -0.14, 0, 0, 1, 0))
    elif variation == "pose":
        img = img.rotate(-9, resample=Image.BICUBIC, expand=False)
    elif variation == "dim":
        img = ImageEnhance.Brightness(img).enhance(0.65)
    elif variation == "bright":
        img = ImageEnhance.Brightness(img).enhance(1.35)
    # expression variations (smile/sad/cls) are drawn into the face itself
    return img


def generate_variation(spec: FaceSpec, variation: str, seed: int) -> Image.Image:
    """Return one synthetic image for the given identity & variation."""
    img = _draw_face(spec, variation=variation, seed=seed)
    return _apply_variation(img, variation)


def generate_dataset(root_dir: str) -> dict[str, int]:
    """Generate and save the full DEMO dataset under ``root_dir``.

    Layout: ``<root>/DEMO-001/frontal.png``, ``DEMO-001/left-angle.png`` ...
    Returns a mapping of demo_id -> number of images written.
    """
    os.makedirs(root_dir, exist_ok=True)
    variations = VARIATIONS
    counts: dict[str, int] = {}
    for spec in IDENTITIES:
        person_dir = os.path.join(root_dir, spec.demo_id)
        os.makedirs(person_dir, exist_ok=True)
        n = 0
        for i, var in enumerate(variations):
            img = generate_variation(spec, var, seed=i)
            img.save(os.path.join(person_dir, f"{var}.png"), format="PNG")
            n += 1
        counts[spec.demo_id] = n
    return counts


def identity_meta(demo_id: str) -> dict | None:
    """Return descriptive metadata (gender/age) for a DEMO identity, if known."""
    for spec in IDENTITIES:
        if spec.demo_id == demo_id:
            return {"gender": spec.gender, "age": spec.age, "name": spec.display_name}
    return None


def default_dataset_root() -> str:
    """Computed dataset root. Not user-configurable path leaks; hidden under backend/uploads."""
    from app.core.config import settings
    base = (settings.UPLOAD_DIR or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads"))
    return os.path.join(base, "face_demo_dataset")


def ensure_demo_dataset() -> str:
    """Idempotently materialize the DEMO dataset to disk and return its root."""
    root = default_dataset_root()
    # Skip regeneration if already present with the expected identity folders.
    if all(os.path.isdir(os.path.join(root, s.demo_id)) for s in IDENTITIES):
        return root
    generate_dataset(root)
    return root
