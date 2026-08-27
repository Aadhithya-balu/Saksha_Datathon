"""Authoritative runtime data-mode provider (Issue #190 §3, §5).

This module is the single extension point for data-mode enforcement.  It wraps
the validated :class:`app.core.config.Settings` and exposes helpers so that
services can gate demo/seed fallback behavior consistently.

Principles enforced here (MISSING.md §3):
  - ``production``  -> NO silent fallback to demo/seed data; honest behaviour.
  - ``demo``        -> fallback permitted; state visible via DEMO badges.
  - ``test``        -> no fallback, mock responses only.
  - Invalid/missing configuration fails safely at configuration load time
    (see the ``SAKSHA_DATA_MODE`` validator in ``config.py``), so this module
    can assume a valid value at runtime.

Unknown provenance never becomes ``live`` by default (see
:func:`normalize_provenance` and the provenance pipeline used by services).
"""
from __future__ import annotations

import os
from enum import Enum
from typing import Any

from app.core.config import settings

MODE_PRODUCTION = "production"
MODE_DEMO = "demo"
MODE_TEST = "test"

VALID_MODES = (MODE_PRODUCTION, MODE_DEMO, MODE_TEST)

# Provenance values supported by the pipeline (MISSING.md §7).
PROVENANCE_LIVE = "live"
PROVENANCE_MIGRATED = "migrated"
PROVENANCE_DEMO = "demo"
PROVENANCE_UNKNOWN = "unknown"
PROVENANCE_MIXED = "mixed"

VALID_PROVENANCE = (PROVENANCE_LIVE, PROVENANCE_MIGRATED, PROVENANCE_DEMO, PROVENANCE_UNKNOWN)


class DataMode(str, Enum):
    PRODUCTION = MODE_PRODUCTION
    DEMO = MODE_DEMO
    TEST = MODE_TEST


def get_data_mode() -> str:
    """Return the validated runtime data mode: 'production' | 'demo' | 'test'.

    Resolution order (Issue #190 §3):
      1. Runtime ``SAKSHA_DATA_MODE`` env var (allows operator override without
         a restart, and keeps the live/request-time semantics used by the
         data-mode endpoint and tests).
      2. The validated :data:`settings.SAKSHA_DATA_MODE` startup default.

    Any invalid/missing value fails safely to ``demo`` (the least permissive
    mode that does not silently present seed data as live in an unlabelled
    way); it never degrades to a hidden 'production' interpretation.
    """
    raw = os.environ.get("SAKSHA_DATA_MODE")
    if raw is None or str(raw).strip() == "":
        raw = getattr(settings, "SAKSHA_DATA_MODE", MODE_DEMO) or MODE_DEMO
    mode = str(raw).strip().lower()
    if mode not in VALID_MODES:
        # Defensive: config validator already guarantees a valid startup value,
        # but a runtime env override could be invalid. Never let an unexpected
        # value produce permissive/ambiguous behaviour.
        return MODE_DEMO
    return mode


def is_production() -> bool:
    """True when running in production mode (no silent demo fallback)."""
    return get_data_mode() == MODE_PRODUCTION


def is_demo_mode() -> bool:
    return get_data_mode() == MODE_DEMO


def is_test_mode() -> bool:
    return get_data_mode() == MODE_TEST


def allows_demo_fallback() -> bool:
    """Whether demo/seed data may be used as a fallback in the current mode.

    Only ``demo`` mode permits silent fallback.  In ``production`` and
    ``test`` modes fallback is NOT permitted, so endpoints must return an
    honest error/unavailable state instead of synthetic intelligence.
    """
    return get_data_mode() == MODE_DEMO


def show_demo_badges() -> bool:
    """Whether DEMO badges should be rendered for transparency.

    They are always shown so users can always distinguish demo from live data.
    """
    return True


def normalize_provenance(value: Any) -> str:
    """Normalize a raw provenance value to a canonical tag.

    None / empty / unrecognized values map to ``unknown`` (never ``live``),
    honouring MISSING.md §7: "Unknown must never become LIVE by default."
    """
    if value is None:
        return PROVENANCE_UNKNOWN
    normalized = str(value).strip().lower() if not isinstance(value, str) else value.strip().lower()
    if normalized in VALID_PROVENANCE:
        return normalized
    return PROVENANCE_UNKNOWN


def data_mode_payload() -> dict[str, Any]:
    """Return the data-mode payload shared by admin/analytics endpoints."""
    return {
        "mode": get_data_mode(),
        "allow_demo_fallback": allows_demo_fallback(),
        "show_demo_badges": show_demo_badges(),
    }
