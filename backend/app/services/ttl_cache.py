"""Small thread-safe time-to-live (TTL) result cache.

Used to short-circuit expensive read-only analytics/AI computations (e.g.
hotspot statistics, district risk scoring) that are repeatedly requested by
the dashboard without the underlying data changing every request.

The cache is a plain module-level dict keyed by the decorated function plus a
caller-supplied key. Entries expire after ``ttl_seconds``. Because expired
entries are simply skipped and overwritten, the implementation is safe under
FastAPI's default threadpool concurrency (worst case: redundant recompute).
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

_ENTRIES: dict[str, tuple[float, Any]] = {}
_LOCK = threading.Lock()


def _make_key(func_key: str, key_args: tuple[Any, ...]) -> str:
    try:
        return f"{func_key}:{repr(key_args)}"
    except Exception:
        return f"{func_key}:{id(key_args)}"


def ttl_cached(
    func_key: str,
    key_args: tuple[Any, ...],
    ttl_seconds: float,
    compute: Callable[[], Any],
    scope: Any = None,
) -> Any:
    """Return a cached value for ``(func_key, key_args)`` or compute fresh.

    If a non-expired cached value exists it is returned without invoking
    ``compute``. Otherwise ``compute()`` is called, stored, and returned.

    ``scope`` is an optional cache partition (e.g. the database engine) used to
    isolate cached results when the underlying data source changes identity —
    this avoids stale values leaking across database instances/tests.
    """
    if scope is not None:
        try:
            key_args = (id(scope),) + key_args
        except Exception:
            pass
    cache_key = _make_key(func_key, key_args)
    now = time.monotonic()

    with _LOCK:
        hit = _ENTRIES.get(cache_key)
        if hit is not None and hit[0] > now:
            return hit[1]

    value = compute()

    with _LOCK:
        _ENTRIES[cache_key] = (now + ttl_seconds, value)
    return value


def invalidate_ttl_caches() -> None:
    """Drop every cached entry (call after bulk imports/updates)."""
    with _LOCK:
        _ENTRIES.clear()
