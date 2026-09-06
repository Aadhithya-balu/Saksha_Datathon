"""
Custom exception types and centralized exception handlers.
Registered on the FastAPI app in main.py so every route gets
consistent error responses: {"error": {"code": ..., "message": ..., "status": ...}}
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import OperationalError, TimeoutError as SQLAlchemyTimeoutError


class AppException(Exception):
    def __init__(self, message: str, code: str = "APP_ERROR", status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.code = code
        self.status_code = status_code


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(message, code="UNAUTHORIZED", status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message, code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, code="CONFLICT", status_code=status.HTTP_409_CONFLICT)


def _error_body(code: str, message: str, status_code: int) -> dict:
    return {"error": {"code": code, "message": message, "status": status_code}}


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message, exc.status_code))


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body("HTTP_ERROR", str(exc.detail), exc.status_code),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import traceback
    import logging
    logging.getLogger("saksha").error("Unhandled exception: %s", traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("INTERNAL_SERVER_ERROR", "An internal server error occurred. Please try again later.", 500),
    )


async def pool_timeout_exception_handler(request: Request, exc: SQLAlchemyTimeoutError) -> JSONResponse:
    """QueuePool exhaustion (all DB connections busy).

    Returned as a recoverable 503 with a short Retry-After so clients know the
    infrastructure is temporarily saturated and can wait instead of treating it
    as a hard failure. The frontend listens for ``DB_POOL_EXHAUSTED`` and shows
    a "please wait" alert (and auto-retries safe GET requests).
    """
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=_error_body(
            "DB_POOL_EXHAUSTED",
            "Database connection pool is temporarily exhausted. Please wait a moment and retry.",
            503,
        ),
        headers={"Retry-After": "5"},
    )


async def db_unreachable_exception_handler(request: Request, exc: OperationalError) -> JSONResponse:
    """DB connection/execution failures during transient cold start.

    Serverless hosts (Zoho Catalyst AppSail) spin instances up/down, so the
    first requests on a cold instance can hit a still-warming DB connection
    (TLS + pool warm-up). Treat those as a recoverable 503 carrying the same
    ``DB_POOL_EXHAUSTED`` code the frontend already auto-retries, instead of a
    hard 500.
    """
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=_error_body(
            "DB_POOL_EXHAUSTED",
            "Database is temporarily unreachable. Please wait a moment and retry.",
            503,
        ),
        headers={"Retry-After": "5"},
    )


def register_exception_handlers(app) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    # More specific than the generic Exception handler, so QueuePool timeouts
    # surface as a machine-readable 503 instead of a raw 500 traceback.
    app.add_exception_handler(SQLAlchemyTimeoutError, pool_timeout_exception_handler)
    app.add_exception_handler(OperationalError, db_unreachable_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
