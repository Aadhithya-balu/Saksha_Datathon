"""Optional Zoho Catalyst/Zia face-analytics adapter (Issue #228).

The issue documented a set of Zia SDK symbols (``ZCFaceAnalyticsOptions``,
``ZCFaces``, ``ZCFaceAnalysisData``, ``ZCAge``, ``ZCGender``,
``ZCFaceEmotion``, ``ZCFacePoints``, ``ZCFaceLandmark``). Those names are NOT
present in the actual installed Zoho Catalyst SDK (``zcatalyst-sdk``). Rather
than invent unsupported methods, this adapter inspects the installed SDK at
runtime and only exercises the methods that are verified to exist there:

  * ``Zia.analyse_face(image, options)``      -> POST /ml/faceanalytics
  * ``Zia.compare_face(source, query)``       -> POST /ml/facecomparison

with response shapes ``ICatalystZiaFace`` (``faces: [FaceParams]``) and
``ICatalystZiaFaceComparison`` (``{confidence, matched}``).

The Zoho Zia endpoints are only reachable from inside the Catalyst cloud: the
SDK's ``catalyst.initialize()`` validates that the Catalyst runtime headers
(``X-Catalyst-Environment`` etc.) are present and raises otherwise. Running this
adapter on a plain local machine therefore reports ``available=False`` and the
face-recognition service transparently uses the bundled local engine instead —
the application keeps working regardless. This exactly matches Issue #228's
"optional enhancement ... keep working even if face recognition is unavailable".

The adapter is deliberately defensive: every access is guarded so that a partial
or incompatible Zoho installation can never crash the API.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.config import settings
from app.core.logging_config import logger

# The verified Catalyst SDK import name (the issue's "zcatalyst"/"zcml"/"zarro"
# aliases are checked too, but only `zcatalyst_sdk` is known to exist).
_SDK_MODULES = (
    "zcatalyst_sdk",
    "zcatalyst",
    "zcml",
    "zarro",
)

# Genuine Zia `analyse_face` option keys (ICatalystFaceAnalysisOptions).
_ANALYSE_OPTION_KEYS = ("mode", "emotion", "age", "gender")


@dataclass
class ZohoFaceAnalysis:
    """Normalized face-analysis payload derived from supported Zoho SDK data."""

    faces_detected: int = 0
    ages: list = field(default_factory=list)
    genders: list = field(default_factory=list)
    emotions: list = field(default_factory=list)
    landmarks: list = field(default_factory=list)
    points: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)
    used: bool = False


@dataclass
class ZohoFaceComparison:
    """Normalized result of Zoho Zia ``compare_face``."""

    confidence: Optional[float] = None
    matched: bool = False
    used: bool = False
    error: Optional[str] = None


class ZohoFaceAdapter:
    """Thin, reflective wrapper over the installed Zoho Catalyst/Zia SDK.

    ``available`` is True only when the SDK module imports cleanly AND the
    Catalyst runtime can be initialized (i.e. we are running inside the Catalyst
    cloud where the required headers are injected). All calls are guarded so a
    missing/partial SDK can never raise out of the face-recognition flow.
    """

    def __init__(self) -> None:
        self._zoho = None
        self._methods: dict[str, bool] = {}
        self.available: bool = False
        self._error: Optional[str] = None
        self._discover()

    # -- discovery ---------------------------------------------------------
    def _discover(self) -> None:
        if not settings.FACE_RECOGNITION_ENABLED:
            self._error = "FACE_RECOGNITION_ENABLED=false"
            return
        self._zoho = _try_import_sdk()
        if self._zoho is None:
            self._error = "Zoho Catalyst SDK not installed"
            return
        self._methods = _inspect_sdk_methods(self._zoho)
        if not self._methods:
            self._error = "Zoho SDK imported but no supported Zia face methods found"
            return
        # The SDK only runs inside the Catalyst cloud. Attempting initialize()
        # here is cheap and tells us whether the runtime is usable at all.
        if not _catalyst_runtime_usable(self._zoho):
            self._error = "Catalyst runtime not usable outside the Zoho cloud (missing headers)"
            return
        self.available = True

    # -- introspection -----------------------------------------------------
    def describe(self) -> dict:
        """Non-sensitive capability summary (no images, no face data)."""
        return {
            "provider": "zoho",
            "available": self.available,
            "methods_available": sorted(self._methods.keys()),
            "error": self._error,
            "project_id_configured": bool(settings.ZOHO_PROJECT_ID),
            "credentials_configured": bool(settings.ZOHO_CLIENT_ID and settings.ZOHO_CLIENT_SECRET),
        }

    def analyze(self, image_bytes: bytes) -> ZohoFaceAnalysis:
        """Run Zia face analysis on raw image bytes via the installed SDK.

        Returns an empty ``ZohoFaceAnalysis(used=False)`` when the SDK/runtime is
        unavailable or the call cannot be completed safely — never raises.
        """
        result = ZohoFaceAnalysis()
        if not self.available or not self._methods.get("analyse_face"):
            return result
        try:
            return self._run_analysis(image_bytes, result)
        except Exception as exc:  # pragma: no cover - SDK-dependent
            logger.warning("Zoho face analysis failed (falling back): %s", exc)
            self._error = f"analysis_error: {exc}"
            return ZohoFaceAnalysis()

    def compare(self, source_bytes: bytes, query_bytes: bytes) -> ZohoFaceComparison:
        """Verify two faces match by delegating to Zoho Zia ``compare_face``.

        ``source_bytes`` is the reference face, ``query_bytes`` the candidate.
        Falls back to ``ZohoFaceComparison(used=False)`` on any failure.
        """
        result = ZohoFaceComparison()
        if not self.available or not self._methods.get("compare_face"):
            return result
        try:
            return self._run_compare(source_bytes, query_bytes, result)
        except Exception as exc:  # pragma: no cover - SDK-dependent
            logger.warning("Zoho face comparison failed (falling back): %s", exc)
            self._error = f"compare_error: {exc}"
            return ZohoFaceComparison(error=str(exc))

    # -- execution ---------------------------------------------------------
    def _run_analysis(self, image_bytes: bytes, result: ZohoFaceAnalysis) -> ZohoFaceAnalysis:
        from zcatalyst_sdk import catalyst, initialize  # type: ignore
        from io import BufferedReader

        app = catalyst.initialize()
        options = {k: True for k in _ANALYSE_OPTION_KEYS if k in _ANALYSE_OPTION_KEYS and k != "mode"}
        resp = app.zia().analyse_face(file=BufferedReader(_BytesReader(image_bytes)), options=options)
        return _normalize_face_response(resp, result)

    def _run_compare(self, source_bytes: bytes, query_bytes: bytes, result: ZohoFaceComparison) -> ZohoFaceComparison:
        from zcatalyst_sdk import catalyst  # type: ignore
        from io import BufferedReader

        app = catalyst.initialize()
        resp = app.zia().compare_face(
            source_img=BufferedReader(_BytesReader(source_bytes)),
            query_img=BufferedReader(_BytesReader(query_bytes)),
        )
        result.used = True
        result.matched = bool(resp.get("matched"))
        conf = resp.get("confidence")
        result.confidence = float(conf) if conf is not None else None
        return result

    @property
    def is_used(self) -> bool:
        return self.available


class _BytesReader:
    """Minimal bytes-backed reader shim accepted in place of BufferedReader."""

    def __init__(self, data: bytes) -> None:
        self._buffer = data
        self._pos = 0

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = len(self._buffer) - self._pos
        chunk = self._buffer[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk


def _try_import_sdk():
    for name in _SDK_MODULES:
        try:
            return importlib.import_module(name)
        except Exception:
            continue
    return None


def _inspect_sdk_methods(zoho) -> dict[str, bool]:
    """Return which supported Zia face methods exist on the SDK.

    Only methods that are genuinely exposed by the installed SDK are returned;
    nothing is assumed from the issue's prose.
    """
    methods: dict[str, bool] = {}
    try:
        from zcatalyst_sdk.types.zia import ICatalystZiaFace, ICatalystZiaFaceComparison  # type: ignore
        methods["ICatalystZiaFace"] = True
        methods["ICatalystZiaFaceComparison"] = True
    except Exception:
        pass
    try:
        from zcatalyst_sdk import catalyst_app  # type: ignore
        zia_type = getattr(getattr(catalyst_app, "CatalystApp", None), "zia", None)
        if zia_type is not None:
            methods["app.zia"] = True
    except Exception:
        pass
    try:
        import zcatalyst_sdk.zia as zia_mod  # type: ignore
        ana = getattr(zia_mod.Zia, "analyse_face", None)
        cmp = getattr(zia_mod.Zia, "compare_face", None)
        if ana is not None:
            methods["analyse_face"] = True
        if cmp is not None:
            methods["compare_face"] = True
    except Exception:
        pass
    return methods


def _catalyst_runtime_usable(zoho) -> bool:
    """Probe whether Catalyst runtime can be initialized (true only in-cloud)."""
    try:
        from zcatalyst_sdk import catalyst, initialize  # type: ignore
        opts = {
            "client_id": settings.ZOHO_CLIENT_ID,
            "client_secret": settings.ZOHO_CLIENT_SECRET,
            "project_id": settings.ZOHO_PROJECT_ID,
        }
        app = initialize(opts)
        _ = app.zia()
        return True
    except Exception:
        return False


def _normalize_face_response(resp, result: ZohoFaceAnalysis) -> ZohoFaceAnalysis:
    """Map an ``ICatalystZiaFace``-shaped response onto our normalized model."""
    result.used = True
    faces = _dig(resp, "faces") if isinstance(resp, dict) else getattr(resp, "faces", None)
    if isinstance(faces, dict):
        faces = [faces]
    if not isinstance(faces, (list, tuple)):
        faces = []
    result.faces_detected = len(faces)
    for face in faces:
        result.ages.append(_label(_com_value(face, "age")))
        result.genders.append(_label(_com_value(face, "gender")))
        result.emotions.append(_label(_com_value(face, "emotion")))
        result.landmarks.append(_dig(face, "landmarks"))
        result.points.append(_dig(face, "co_ordinates") or _dig(face, "coordinates"))
    result.raw = {"response_type": type(resp).__name__, "face_keys": sorted(face.keys()) if isinstance(faces and faces[0], dict) else []}
    return result


def _com_value(face, key: str) -> Any:
    """Extract the prediction from a face's ``{prediction, confidence}`` sub-object."""
    val = _dig(face, key)
    if isinstance(val, dict):
        return val.get("prediction") or val
    return val


def _label(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (str, int, float)):
        return str(value)
    if isinstance(value, dict):
        for k in ("prediction", "value", "label", "type", "name", "range"):
            if value.get(k) is not None:
                return str(value[k])
        return str(value)
    for attr in ("prediction", "value", "label", "type", "name", "range"):
        v = _dig(value, attr)
        if v is not None:
            return str(v)
    return str(value)


def _dig(obj, key: str):
    if isinstance(obj, dict) and key in obj:
        return obj[key]
    if hasattr(obj, key):
        return getattr(obj, key)
    return None


_instance_cache: dict = {}


def get_zoho_adapter() -> ZohoFaceAdapter:
    if "adapter" not in _instance_cache:
        _instance_cache["adapter"] = ZohoFaceAdapter()
    return _instance_cache["adapter"]
