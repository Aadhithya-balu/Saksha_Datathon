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
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.api.v2 import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import configure_logging, logger
from app.core.rate_limit import RateLimitMiddleware
from app.core.security_headers import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.database.neo4j import close_neo4j_driver, verify_neo4j_connectivity
from app.database.postgres import Base, engine
import app.models  # ensure models are registered


_migration_done = False


def _get_table_columns(conn, table_name: str) -> set[str]:
    if conn.dialect.name == "sqlite":
        res = conn.execute(text(f"PRAGMA table_info({table_name})"))
        return {row[1] for row in res}
    res = conn.execute(text(
        f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
    ))
    return {row[0] for row in res}


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
            existing = _get_table_columns(conn, "notifications")

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
            existing = _get_table_columns(conn, "criminals")
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
            inspector = inspect(conn)
            existing = {c["name"] for c in inspector.get_columns("evidence_metadata")}
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
            inspector = inspect(conn)
            changed = False
            for table, col, col_def in migrations:
                existing = {c["name"] for c in inspector.get_columns(table)}
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
                    changed = True
            if changed:
                conn.commit()
                logger.info("Person image migration complete (#107)")
    except Exception as exc:
        logger.warning(f"Person image migration skipped: {exc}")


def _migrate_provenance_columns():
    """Issue #164: add dataset_provenance and import lineage columns to core
    tables that previously lacked ImportProvenanceMixin.

    All DDL is idempotent — safe on every startup. Existing rows default to
    ``'unknown'`` so they are never silently treated as live operational data.
    """
    provenance_tables = ["criminals", "victims", "crime_cases", "locations", "firs", "evidence", "officers"]
    provenance_columns = [
        ("dataset_provenance", "VARCHAR(20) NOT NULL DEFAULT 'unknown'"),
        ("source_import_job_id", "UUID"),
        ("source_file", "VARCHAR(500)"),
        ("source_row_ref", "VARCHAR(100)"),
    ]
    try:
        with engine.connect() as conn:
            inspector = inspect(conn)
            changed = False
            for table in provenance_tables:
                try:
                    existing = {c["name"] for c in inspector.get_columns(table)}
                except Exception:
                    continue
                for col_name, col_def in provenance_columns:
                    if col_name not in existing:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"))
                        changed = True
                        logger.info(f"Provenance column '{col_name}' added to {table}")
            if changed:
                conn.commit()
    except Exception as exc:
        logger.warning(f"Provenance migration skipped: {exc}")


def _migrate_report_lifecycle_columns():
    """Issue #176: add report lifecycle columns and new tables for existing
    deployments that were created before the lifecycle model (idempotent DDL).

    ``create_all`` handles brand-new tables; this only ALTERs existing ones.
    """
    report_columns = [
        ("report_type", "VARCHAR(50) NOT NULL DEFAULT 'cases'"),
        ("title", "VARCHAR(255)"),
        ("case_id", "UUID"),
        ("provenance", "VARCHAR(20) NOT NULL DEFAULT 'unknown'"),
        ("integrity_hash", "VARCHAR(64)"),
        ("generation_method", "VARCHAR(50)"),
        ("analysis_fingerprint", "VARCHAR(200)"),
        ("failure_reason", "VARCHAR(500)"),
        ("source_record_count", "INTEGER NOT NULL DEFAULT 0"),
        ("evidence_count", "INTEGER NOT NULL DEFAULT 0"),
        ("generated_at", "TIMESTAMPTZ"),
        ("reviewed_at", "TIMESTAMPTZ"),
        ("finalized_at", "TIMESTAMPTZ"),
        ("archived_at", "TIMESTAMPTZ"),
        ("reviewed_by_id", "UUID"),
        ("finalized_by_id", "UUID"),
        ("version", "INTEGER NOT NULL DEFAULT 1"),
        ("content_snapshot", "TEXT"),
        ("ai_reported", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("ai_metadata", "TEXT"),
    ]
    try:
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            if "reports" in tables:
                existing = {c["name"] for c in inspector.get_columns("reports")}
                changed = False
                for col_name, col_def in report_columns:
                    if col_name not in existing:
                        conn.execute(text(f"ALTER TABLE reports ADD COLUMN {col_name} {col_def}"))
                        changed = True
                if "audit_logs" in tables:
                    audit_existing = {c["name"] for c in inspector.get_columns("audit_logs")}
                    for col_name in ("result", "metadata"):
                        if col_name not in audit_existing:
                            col_def = "VARCHAR(20) NOT NULL DEFAULT 'success'" if col_name == "result" else "TEXT"
                            conn.execute(text(f"ALTER TABLE audit_logs ADD COLUMN {col_name} {col_def}"))
                            changed = True
                if changed:
                    conn.commit()
                    logger.info("Report lifecycle migration complete (issue #176)")
    except Exception as exc:
        logger.warning(f"Report lifecycle migration skipped: {exc}")

def _migrate_user_lockout_columns():
    """Round-2 security: brute-force lockout columns on users (idempotent DDL)."""
    try:
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            if "users" in tables:
                existing = {c["name"] for c in inspector.get_columns("users")}
                is_sqlite = engine.dialect.name == "sqlite"
                changed = False
                if "failed_login_attempts" not in existing:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0"
                    ))
                    changed = True
                if "locked_until" not in existing:
                    type_str = "DATETIME" if is_sqlite else "TIMESTAMPTZ"
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN locked_until {type_str}"))
                    changed = True
                if changed:
                    conn.commit()
                    logger.info("Users table migration complete (lockout columns added)")
    except Exception as exc:
        logger.warning(f"Users lockout column migration skipped: {exc}")


def _migrate_intervention_workflow_columns():
    """Add workflow stage, recommendation, simulation, and outcome columns to interventions (idempotent DDL)."""
    columns = [
        ("workflow_stage", "VARCHAR(30) DEFAULT 'draft'"),
        ("intelligence_id", "VARCHAR(100)"),
        ("pattern_type", "VARCHAR(100)"),
        ("affected_h3_cells", "TEXT"),
        ("relevant_time_period", "VARCHAR(100)"),
        ("reason", "TEXT"),
        ("supporting_intelligence", "TEXT"),
        ("estimated_coverage", "FLOAT"),
        ("assumptions", "TEXT"),
        ("simulation_data", "TEXT"),
        ("supervisor_notes", "TEXT"),
        ("subsequent_crime_count", "INTEGER"),
        ("pattern_persisted", "VARCHAR(50)"),
        ("observed_outcome", "TEXT"),
        ("review_notes", "TEXT"),
    ]
    try:
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            if "interventions" in tables:
                existing = {c["name"] for c in inspector.get_columns("interventions")}
                changed = False
                for col_name, col_type in columns:
                    if col_name not in existing:
                        conn.execute(text(f"ALTER TABLE interventions ADD COLUMN {col_name} {col_type}"))
                        changed = True
                if changed:
                    conn.commit()
                    logger.info("Interventions workflow columns migration complete")
    except Exception as exc:
        logger.warning(f"Interventions workflow migration skipped: {exc}")





def _prewarm_models() -> None:
    """Load all ML model artifacts into lru_cache at startup.

    This pays the joblib deserialisation cost once during startup so the
    first real inference request is fast instead of slow.
    """
    from app.core.config import settings
    if settings.APP_ENV == "test":
        return
    import threading

    def _load():
        try:
            loaders = [
                ("hotspot",  "app.ai.inference.hotspot",  ["_load_model", "_load_feature_columns", "_load_metadata"]),
                ("risk",     "app.ai.inference.risk",      ["_load_risk_model", "_load_forecast_model", "_load_metadata"]),
                ("criminal", "app.ai.inference.criminal",  ["_load_models"]),
                ("anomaly",  "app.ai.inference.anomaly",   ["_load_default_model"]),
            ]
            import importlib
            for key, module_path, fn_names in loaders:
                try:
                    mod = importlib.import_module(module_path)
                    for fn_name in fn_names:
                        fn = getattr(mod, fn_name, None)
                        if callable(fn):
                            fn()
                        else:
                            logger.warning("[prewarm] %s has no callable %s — add it so the domain prewarms", key, fn_name)
                    logger.info(f"[prewarm] {key} model loaded")
                except Exception as exc:
                    logger.warning("[prewarm] %s skipped: %s", key, exc)
        except Exception as exc:
            logger.error("[prewarm] Background model prewarm thread crashed: %s", exc, exc_info=True)

    threading.Thread(target=_load, name="saksha-prewarm", daemon=True).start()


def _prewarm_mo_profiles():
    """Warm the MO profile cache in a background thread.

    MO matching extracts a normalized profile for every crime case and every
    criminal in the database (~40s on real data). With this warm-up, the first
    criminal-detail / investigation lookup the operator performs is already
    fast because the profiles are cached. Best-effort: any failure is logged
    and left for the on-demand path.
    """
    import threading

    def _warm():
        try:
            from app.database.postgres import SessionLocal
            from sqlalchemy.orm import joinedload

            from app.models.crime import CrimeCase
            from app.models.criminal import Criminal
            from app.services.mo_matching_service import (
                extract_case_mo_profile,
                extract_criminal_mo_profile,
            )

            db = SessionLocal()
            try:
                cases = (
                    db.query(CrimeCase)
                    .options(joinedload(CrimeCase.category), joinedload(CrimeCase.location))
                    .all()
                )
                for case in cases:
                    extract_case_mo_profile(db, case)
                criminals = (
                    db.query(Criminal)
                    .options(joinedload(Criminal.fir_links))
                    .all()
                )
                for criminal in criminals:
                    extract_criminal_mo_profile(db, criminal)
                logger.info(
                    f"[prewarm] MO profiles cached: {len(cases)} cases, {len(criminals)} criminals"
                )
            finally:
                db.close()
        except Exception as exc:
            logger.warning("[prewarm] MO profile warm-up skipped: %s", exc)

    threading.Thread(target=_warm, name="saksha-prewarm-mo", daemon=True).start()


_bg_refresh_stop = False


def _start_background_refresh() -> None:
    """Run staleness checks every 5 minutes in a background thread.

    Moves check_external_updates() and maybe_refresh_async() off the
    hot inference path so every prediction request is fast.
    """
    from app.core.config import settings
    if settings.APP_ENV == "test":
        return
    import threading
    import time

    def _loop():
        # Initial delay — let the server finish starting up first.
        time.sleep(30)
        while not _bg_refresh_stop:
            try:
                from app.ai.inference.refresh import check_external_updates, maybe_refresh_async
                from app.database.postgres import SessionLocal
                check_external_updates()
                db = SessionLocal()
                try:
                    maybe_refresh_async(db=db, reason="background-scheduler")
                finally:
                    db.close()
            except Exception as exc:
                logger.debug("[bg-refresh] error: %s", exc)
            time.sleep(300)  # 5 minutes

    threading.Thread(target=_loop, name="saksha-bg-refresh", daemon=True).start()


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

    # Issue #167: Log production config warnings/errors at startup
    if settings.production_errors:
        for err in settings.production_errors:
            logger.error(f"[CONFIG] Production config error: {err}")
    if settings.production_warnings:
        for warn in settings.production_warnings:
            logger.warning(f"[CONFIG] Production config warning: {warn}")

    try:
        _db_connected = False
        for attempt in range(1, 4):
            try:
                Base.metadata.create_all(bind=engine)
                _migrate_notifications_table()
                _migrate_criminals_table()
                _migrate_evidence_metadata_table()
                _migrate_person_image_fields()
                _migrate_provenance_columns()
                _ensure_realtime_indexes()
                _migrate_user_lockout_columns()
                _migrate_report_lifecycle_columns()
                _migrate_intervention_workflow_columns()
                with engine.connect():
                    logger.info("PostgreSQL connection OK")
                _db_connected = True
                break
            except Exception as exc:
                wait = 2 ** attempt
                logger.warning(f"PostgreSQL attempt {attempt}/3 failed: {exc}. Retrying in {wait}s...")
                import time
                time.sleep(wait)
        if not _db_connected:
            logger.error("PostgreSQL connection failed after 3 attempts — running in degraded mode")
    except Exception as exc:
        logger.error(f"PostgreSQL setup error: {exc}")

    # Auto-seed demo data when the database has no users yet and demo fallback
    # is permitted (never in production). This gives operators a working login —
    # and the demo gang networks — out of the box on any fresh environment,
    # including Supabase/PostgreSQL deploys with an empty database.
    try:
        from app.core import data_mode as _data_mode
        from app.database.postgres import SessionLocal
        if not _data_mode.is_production():
            with SessionLocal() as _db:
                from app.models.user import User
                if _db.query(User).count() == 0:
                    logger.info("Database has no users — seeding demo data...")
                    from app.database.seed_db import seed
                    seed()
                    logger.info("Demo data seeded successfully")
    except Exception as exc:
        logger.warning(f"Auto-seed skipped: {exc}")

    # Neo4j connectivity is verified lazily on first use, not at startup.
    # This avoids blocking server readiness on a remote Neo4j Aura connection.
    logger.info("Neo4j will be verified lazily on first use")

    # Pre-warm all ML models in a background thread so the first inference
    # request is fast. Runs concurrently with server startup.
    _prewarm_models()

    # Pre-warm the MO profile cache in the background so criminal-detail /
    # investigation lookups don't pay the ~40s one-time extraction cost on the
    # user's first request. Best-effort and non-blocking.
    _prewarm_mo_profiles()

    # Materialize the synthetic face-recognition DEMO dataset so the gallery
    # images are available immediately when the Feature page is opened.
    try:
        from app.ai.face import synthetic as _face_synth
        _face_synth.ensure_demo_dataset()
        logger.info("Face-recognition demo dataset ready")
    except Exception as exc:
        logger.warning(f"Face-recognition demo dataset generation skipped: {exc}")

    # Move staleness checks off the hot inference path — run every 5 min.
    _start_background_refresh()

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

# --- Middleware stack (order = outermost first at request time) -------------
# CORS outermost so preflight OPTIONS bypasses rate limiting; security headers
# wrap every response including 429s from the rate limiter.
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    # Explicit method/header allow-lists — no wildcards on a credentialed API.
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    max_age=600,
)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.API_V2_PREFIX)


@app.get("/health/live", tags=["System"])
def liveness():
    """Liveness probe: is the process running? No dependency detail exposed."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["System"])
def readiness():
    """Readiness probe: can the app serve requests?

    Returns component status WITHOUT infrastructure internals (no hosts, no
    error text) so it is safe to expose to load balancers / orchestrators.
    """
    pg_ok = True
    try:
        with engine.connect():
            pass
    except Exception:
        pg_ok = False

    neo4j_ok = verify_neo4j_connectivity()

    status_ok = pg_ok  # Neo4j is optional (SQL fallback exists), PG is not
    return {
        "status": "ok" if status_ok else "degraded",
        "postgresql": "up" if pg_ok else "down",
        "neo4j": "up" if neo4j_ok else "degraded",
    }


@app.get("/health", tags=["System"], include_in_schema=False)
def health_check():
    """Backwards-compatible alias for the readiness probe."""
    return readiness()


@app.get("/", tags=["System"])
def root():
    return {"message": f"{settings.APP_NAME} is running", "docs": "/docs"}
