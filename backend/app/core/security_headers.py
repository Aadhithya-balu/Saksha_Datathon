"""
HTTP security headers and request-size protection.

Headers are applied to every response (API and docs). The CSP is scoped to
what this backend actually serves:
- /docs and /redoc (Swagger/ReDoc) require inline styles/scripts from their
  embedded bundles, so those paths get a pragmatic CSP.
- API responses get a locked-down CSP (defense-in-depth if ever rendered).
- connect-src includes the LLM provider hosts used by server-side code only —
  irrelevant to clients, so it stays restrictive.

The body-size guard rejects oversized JSON/form payloads early (DoS guard);
evidence uploads enforce their own stricter streaming limit separately.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

_API_CSP = (
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
)
_DOCS_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "font-src 'self' https://cdn.jsdelivr.net data; img-src 'self' data:; "
    "connect-src 'self'; frame-ancestors 'none'"
)

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(self), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        is_docs = request.url.path.startswith(("/docs", "/redoc"))
        response.headers["Content-Security-Policy"] = _DOCS_CSP if is_docs else _API_CSP
        for name, value in _SECURITY_HEADERS.items():
            # Do not overwrite a value already set by the route.
            response.headers.setdefault(name, value)
        # HSTS only meaningful over TLS; harmless to emit in development but we
        # gate it on production-like environments to keep local HTTP simple.
        if settings.APP_ENV.lower() in ("production", "prod", "staging"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject request bodies larger than MAX_REQUEST_BODY_BYTES early.

    Uses Content-Length when present (cheap fast-path); chunked bodies are
    capped while streaming to avoid trusting headers alone.
    """

    def __init__(self, app, max_bytes: int | None = None):
        super().__init__(app)
        self.max_bytes = max_bytes or settings.MAX_REQUEST_BODY_BYTES

    def _too_large(self) -> JSONResponse:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "REQUEST_TOO_LARGE",
                    "message": f"Request body exceeds the {self.max_bytes // (1024 * 1024)} MB limit.",
                    "status": 413,
                }
            },
        )

    async def dispatch(self, request: Request, call_next):
        # Multipart (file) uploads are excluded here — they are validated and
        # size-capped while streaming in evidence_service.save_upload_file.
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("multipart/form-data"):
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > self.max_bytes:
            return self._too_large()

        body = b""
        async for chunk in request.stream():
            body += chunk
            if len(body) > self.max_bytes:
                return self._too_large()
        request._body = body
        return await call_next(request)
