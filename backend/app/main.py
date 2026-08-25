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
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v2 import api_router
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


def _migrate_criminals_table():
    """Add gang_affiliation to criminals if missing (issue #141 gang network derivation).

    ``create_all`` only applies new columns on fresh tables, so existing
    deployments get the column via idempotent DDL here.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'criminals'"
            ))
            existing = {row[0] for row in result}
            if "gang_affiliation" not in existing:
                conn.execute(text("ALTER TABLE criminals ADD COLUMN gang_affiliation VARCHAR(255)"))
                conn.commit()
                logger.info("Criminals table migration complete (gang_affiliation added)")
    except Exception as exc:
        logger.warning(f"Criminals table migration skipped: {exc}")


def _ensure_realtime_indexes():
    """Create indexes required for fast real-time case feeds if missing.

    ``create_all`` only applies model indexes when a table is first created,
    so existing deployments get the created_at index via idempotent DDL here.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_crime_cases_created_at "
                "ON crime_cases (created_at)"
            ))
            conn.commit()
        logger.info("Real-time index check complete")
    except Exception as exc:
        logger.warning(f"Real-time index creation skipped: {exc}")


def _migrate_evidence_metadata_table():
    """Add storage_url column to evidence_metadata if missing (issue #126).

    Existing deployments get the column via idempotent DDL so create_all()
    does not need to drop/recreate the table.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'evidence_metadata'"
            ))
            existing = {row[0] for row in result}
            if "storage_url" not in existing:
                conn.execute(text("ALTER TABLE evidence_metadata ADD COLUMN storage_url VARCHAR(1000)"))
                conn.commit()
                logger.info("evidence_metadata table migration complete (storage_url added)")
    except Exception as exc:
        logger.warning(f"evidence_metadata table migration skipped: {exc}")


def _migrate_person_image_fields():
    """Issue #107: add image_url to criminals, victims, officers.
    All DDL is idempotent — safe to run on every startup.
    """
    migrations: list[tuple[str, str, str]] = [
        ("criminals", "image_url", "VARCHAR(1000)"),
        ("victims",   "image_url", "VARCHAR(1000)"),
        ("officers",  "image_url", "VARCHAR(1000)"),
    ]
    try:
        with engine.connect() as conn:
            changed = False
            for table, col, col_def in migrations:
                result = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    f"WHERE table_name = '{table}' AND column_name = '{col}'"
                ))
                if not result.fetchone():
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
                    changed = True
            if changed:
                conn.commit()
                logger.info("Person image migration complete (#107)")
    except Exception as exc:
        logger.warning(f"Person image migration skipped: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")

    # Issue #126: warn when running with SQLite (data lost on container restart).
    db_url = settings.DATABASE_URL or ""
    if db_url.startswith("sqlite"):
        logger.warning(
            "[STORAGE] DATABASE_URL is SQLite (%s). "
            "Set SUPABASE_DB_* or DATABASE_URL env vars for a persistent database. "
            "SQLite data will be lost on container restart.",
            db_url,
        )

    try:
        Base.metadata.create_all(bind=engine)
        _migrate_notifications_table()
        _migrate_criminals_table()
        _migrate_evidence_metadata_table()
        _migrate_person_image_fields()
        _ensure_realtime_indexes()
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
    version="2.0.0",
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

app.include_router(api_router, prefix=settings.API_V2_PREFIX)

# Serve local evidence files only in development. Person profile images use
# persistent Supabase Storage and never fall back to this directory.
from app.services.evidence_service import UPLOAD_DIR  # noqa: E402
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


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
