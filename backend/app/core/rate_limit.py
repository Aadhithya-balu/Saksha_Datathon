"""
Global API rate limiting — sliding window per client IP.

Design decisions:
- Pure-Python in-process implementation (no Redis dependency) so it works
  identically on Windows / Linux / Docker single-instance deployments.
  For horizontally-scaled multi-instance deployments the per-IP budget is
  per-instance; configure a shared store (e.g. Redis) if strict global limits
  are required (documented in .env.example).
- Endpoint-class budgets: stricter limits on credential (/auth/*), upload,
  and AI paths than the general API, all configurable via environment.
- Excluded paths: health probes and OpenAPI docs so orchestration checks and
  developer tooling are never throttled.
"""
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings


def _bucket_for(path: str) -> tuple[str, int]:
    """Map a request path to (bucket name, max requests per window)."""
    if path.startswith(f"{settings.API_V2_PREFIX}/auth/"):
        return ("auth", settings.RATE_LIMIT_AUTH_MAX_REQUESTS)
    if path.endswith(("/upload", "/uploads", "/upload-image")) or "/upload" in path.rsplit("/", 1)[-1]:
        return ("upload", settings.RATE_LIMIT_UPLOAD_MAX_REQUESTS)
    if path.startswith(f"{settings.API_V2_PREFIX}/ai/") or "/chat" in path:
        return ("ai", settings.RATE_LIMIT_AI_MAX_REQUESTS)
    return ("general", settings.RATE_LIMIT_MAX_REQUESTS)


def resolve_client_ip(request: Request) -> str:
    """Return the real client IP used as the rate-limit / audit key.

    Behind the packaged nginx reverse proxy, `request.client.host` is always
    the proxy (127.0.0.1), so every request would otherwise share a single
    budget and genuine users behind the proxy would hit 429s together. When
    ``RATE_LIMIT_TRUST_XFF`` is enabled (default) we key on the original client
    IP from the ``X-Forwarded-For`` chain (leftmost hop, as appended by nginx),
    falling back to ``X-Real-IP`` and finally the socket peer. Set the flag to
    false when the backend is directly exposed (no trusted proxy) so clients
    cannot spoof fresh budgets by sending their own forwarding headers.
    """
    if settings.RATE_LIMIT_TRUST_XFF:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            first = xff.split(",")[0].strip()
            if first:
                return first
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    EXCLUDED_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")

    def __init__(self, app):
        super().__init__(app)
        # {ip: {bucket: [timestamps]}}
        self._hits: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._last_prune = time.time()

    def _prune(self, now: float) -> None:
        """Periodically drop stale entries to bound memory usage."""
        cutoff = now - settings.RATE_LIMIT_WINDOW_SECONDS
        for ip in list(self._hits.keys()):
            buckets = self._hits[ip]
            empty = True
            for bucket in list(buckets.keys()):
                recent = [t for t in buckets[bucket] if t > cutoff]
                if recent:
                    buckets[bucket] = recent
                    empty = False
                else:
                    del buckets[bucket]
            if empty:
                del self._hits[ip]
        self._last_prune = now

    async def dispatch(self, request: Request, call_next):
        if (
            not settings.RATE_LIMIT_ENABLED
            or settings.APP_ENV == "test"
            or request.method == "OPTIONS"  # CORS preflight must never be blocked
            or any(request.url.path.startswith(p) for p in self.EXCLUDED_PREFIXES)
        ):
            return await call_next(request)

        now = time.time()
        if now - self._last_prune > 300:
            self._prune(now)

        ip = resolve_client_ip(request)
        bucket, limit = _bucket_for(request.url.path)
        window = settings.RATE_LIMIT_WINDOW_SECONDS

        hits = self._hits[ip][bucket]
        hits[:] = [t for t in hits if now - t < window]
        if len(hits) >= limit:
            retry_after = int(hits[0] + window - now) + 1
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={"error": {"code": "RATE_LIMITED", "message": f"Too many requests. Try again in {retry_after}s.", "status": 429}},
            )
        hits.append(now)

        response = await call_next(request)
        remaining = max(0, limit - len(hits))
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
