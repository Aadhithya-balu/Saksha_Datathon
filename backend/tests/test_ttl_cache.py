"""Tests for the TTL result cache used to cut dashboard/AI latency (issue #212)."""
import time

from app.services.ttl_cache import invalidate_ttl_caches, ttl_cached


def test_ttl_cached_returns_cached_value_without_recompute():
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"value": calls["n"]}

    invalidate_ttl_caches()
    first = ttl_cached("test_key", (1,), ttl_seconds=10, compute=compute)
    second = ttl_cached("test_key", (1,), ttl_seconds=10, compute=compute)

    assert calls["n"] == 1
    assert first == second == {"value": 1}
    invalidate_ttl_caches()


def test_ttl_cached_distinct_keys_recompute():
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"value": calls["n"]}

    invalidate_ttl_caches()
    a = ttl_cached("test_key", (1,), ttl_seconds=10, compute=compute)
    b = ttl_cached("test_key", (2,), ttl_seconds=10, compute=compute)

    assert a != b
    assert calls["n"] == 2
    invalidate_ttl_caches()


def test_ttl_cached_expires_after_ttl():
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"value": calls["n"]}

    invalidate_ttl_caches()
    ttl_cached("test_key", (1,), ttl_seconds=0.05, compute=compute)
    ttl_cached("test_key", (1,), ttl_seconds=0.05, compute=compute)
    assert calls["n"] == 1  # cached within TTL

    time.sleep(0.1)
    ttl_cached("test_key", (1,), ttl_seconds=0.05, compute=compute)
    assert calls["n"] == 2  # expired -> recompute
    invalidate_ttl_caches()


def test_ttl_cached_scope_isolates_entries():
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"value": calls["n"]}

    class FakeEngine:
        pass

    e1, e2 = FakeEngine(), FakeEngine()
    invalidate_ttl_caches()
    ttl_cached("test_key", (1,), ttl_seconds=10, compute=compute, scope=e1)
    ttl_cached("test_key", (1,), ttl_seconds=10, compute=compute, scope=e1)
    assert calls["n"] == 1  # same scope -> cached

    ttl_cached("test_key", (1,), ttl_seconds=10, compute=compute, scope=e2)
    assert calls["n"] == 2  # different scope -> recompute
    invalidate_ttl_caches()
