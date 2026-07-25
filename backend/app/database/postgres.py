# Monkeypatch PostgreSQL UUID and JSONB for SQLite compatibility
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import UUID, JSON
pg.UUID = UUID
pg.JSONB = JSON

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings
from app.core.logging_config import configure_logging, logger

configure_logging()


def _engine_options(url) -> dict:
    if url.drivername.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}, "echo": settings.debug_enabled}

    connect_args = {}
    if url.drivername.startswith("postgresql"):
        connect_args["connect_timeout"] = 8
        connect_args["options"] = "-c statement_timeout=30000"

    return {
        "pool_size": 20,
        "max_overflow": 30,
        "pool_pre_ping": False,
        "pool_recycle": 240,
        "pool_timeout": 15,
        "connect_args": connect_args,
        "echo": settings.debug_enabled,
    }


def _create_engine(url=None):
    target_url = url or settings.DATABASE_URL
    return create_engine(target_url, **_engine_options(make_url(target_url)))


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
