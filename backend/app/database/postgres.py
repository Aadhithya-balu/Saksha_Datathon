# Monkeypatch PostgreSQL UUID and JSONB for SQLite compatibility
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import UUID, JSON
pg.UUID = UUID
pg.JSONB = JSON

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings
from app.core.logging_config import configure_logging, logger

configure_logging()


def _engine_options(url, *, worker: bool = False) -> dict:
    if url.drivername.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}, "echo": settings.debug_enabled}

    connect_args = {}
    if url.drivername.startswith("postgresql"):
        connect_args["connect_timeout"] = 8
        # The Supabase transaction pooler (port 6543) does not accept
        # session-level startup options (`options=-c ...`); sending them can
        # break pooled connections. Only set statement_timeout for direct
        # (non-pooled) connections.
        is_pooled = "pooler.supabase.com" in (url.host or "") or url.port == 6543
        if not is_pooled:
            connect_args["options"] = "-c statement_timeout=30000"

    if worker:
        pool_size = settings.DB_WORKER_POOL_SIZE
        max_overflow = settings.DB_WORKER_MAX_OVERFLOW
        pool_timeout = settings.DB_WORKER_POOL_TIMEOUT
    else:
        pool_size = settings.DB_POOL_SIZE
        max_overflow = settings.DB_MAX_OVERFLOW
        pool_timeout = settings.DB_POOL_TIMEOUT

    return {
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_pre_ping": True,
        "pool_recycle": 120,
        "pool_timeout": pool_timeout,
        "connect_args": connect_args,
        "echo": settings.debug_enabled,
    }


def _create_engine(url=None, *, worker: bool = False) -> Engine:
    target_url = url or settings.DATABASE_URL
    return create_engine(target_url, **_engine_options(make_url(target_url), worker=worker))


def _try_connect(eng) -> bool:
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


engine = _create_engine()

if not settings.DATABASE_URL.startswith("sqlite") and not _try_connect(engine):
    logger.warning("PostgreSQL unreachable — falling back to local SQLite database")
    engine.dispose()
    settings.DATABASE_URL = "sqlite:///./saksha.db"
    engine = _create_engine("sqlite:///./saksha.db")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dedicated worker pool for long-running background jobs (model training /
# retrain, parallel AI worker threads). Kept on a SEPARATE engine so heavy
# jobs hold those connections instead of the request-path ones — a saturated
# worker pool can never block auth/CRUD traffic (QueuePool TimeoutError).
# SQLite (demo/test) reuses the main engine to avoid file-lock contention.
_use_worker_pool = not settings.DATABASE_URL.startswith("sqlite")
worker_engine = _create_engine(worker=True) if _use_worker_pool else engine
WorkerSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=worker_engine)


def get_worker_session():
    """Return a DB session bound to the dedicated worker pool.

    Background/worker code (model training, retrain jobs, parallel AI worker
    threads that perform CPU-heavy inference while holding a session) must use
    this instead of ``SessionLocal()`` so the request-path pool stays free.
    """
    return WorkerSessionLocal()


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    """FastAPI dependency that yields a DB session and guarantees it is closed."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
