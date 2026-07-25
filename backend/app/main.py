"""
SAKSHA Backend — FastAPI application entrypoint.
"""
import warnings
warnings.filterwarnings("ignore", message=".*sklearn.utils.parallel.delayed.*")
warnings.filterwarnings("ignore", message=".*deprecated.*PyPDF2.*")
warnings.filterwarnings("ignore", message=".*deprecated.*pypdf.*")
warnings.filterwarnings("ignore", message=".*NumPy array shape.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="joblib")

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import configure_logging, logger
from app.database.neo4j import close_neo4j_driver, verify_neo4j_connectivity
from app.database.postgres import Base, engine
import app.models  # ensure models are registered


_migration_done = False


def _migrate_notifications_table():
    """Add new columns to the notifications table if they don't exist.
    Uses a flag to ensure this only runs once per process lifetime,
    avoiding repeated ALTER TABLE statements on every startup.
    """
    global _migration_done
    if _migration_done:
        return

    new_columns = [
        ("sender_id", "UUID REFERENCES users(id)"),
        ("subject", "VARCHAR(500) NOT NULL DEFAULT ''"),
        ("category", "VARCHAR(50) NOT NULL DEFAULT 'system_notification'"),
        ("priority", "VARCHAR(20) NOT NULL DEFAULT 'medium'"),
        ("status", "VARCHAR(20) NOT NULL DEFAULT 'unread'"),
        ("related_case_number", "VARCHAR(50)"),
        ("related_fir_number", "VARCHAR(50)"),
        ("is_broadcast", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("parent_id", "UUID"),
        ("attachment_url", "VARCHAR(500)"),
        ("acknowledged_at", "TIMESTAMPTZ"),
        ("resolved_at", "TIMESTAMPTZ"),
    ]
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'notifications'"
            ))
            existing = {row[0] for row in result}

            alter_needed = False
            for col_name, col_def in new_columns:
                if col_name not in existing:
                    alter_needed = True
                    try:
                        conn.execute(text(f"ALTER TABLE notifications ADD COLUMN {col_name} {col_def}"))
                    except Exception:
                        pass
            if alter_needed:
                conn.commit()
        _migration_done = True
        logger.info("Notifications table migration complete")
    except Exception as exc:
        logger.warning(f"Notifications table migration skipped: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")

    try:
        Base.metadata.create_all(bind=engine)
        _migrate_notifications_table()
        with engine.connect():
            logger.info("PostgreSQL connection OK")
    except Exception as exc:
        logger.error(f"PostgreSQL connection failed: {exc}")

    # Neo4j connectivity is verified lazily on first use, not at startup.
    # This avoids blocking server readiness on a remote Neo4j Aura connection.
    logger.info("Neo4j will be verified lazily on first use")

    yield

    close_neo4j_driver()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    description="Core backend for the SAKSHA Crime Intelligence Platform — auth, records, and APIs for the AI/ML modules.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["System"])
def health_check():
    """Liveness/readiness probe for Docker/orchestration and uptime monitoring."""
    pg_ok = True
    try:
        with engine.connect():
            pass
    except Exception:
        pg_ok = False

    neo4j_ok = verify_neo4j_connectivity()

    status_ok = pg_ok and neo4j_ok
    return {
        "status": "ok" if status_ok else "degraded",
        "postgresql": "up" if pg_ok else "down",
        "neo4j": "up" if neo4j_ok else "down",
    }


@app.get("/", tags=["System"])
def root():
    return {"message": f"{settings.APP_NAME} is running", "docs": "/docs"}
