# Monkeypatch PostgreSQL UUID and JSONB for SQLite compatibility
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import UUID, JSON
pg.UUID = UUID
pg.JSONB = JSON

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


def _engine_options() -> dict:
    url = make_url(settings.DATABASE_URL)
    if url.drivername.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}, "echo": settings.debug_enabled}

    connect_args = {}
    if url.drivername.startswith("postgresql"):
        connect_args["connect_timeout"] = 8
        connect_args["options"] = "-c statement_timeout=30000"

    return {
        "pool_size": 10,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_timeout": 10,
        "connect_args": connect_args,
        "echo": settings.debug_enabled,
    }


engine = create_engine(settings.DATABASE_URL, **_engine_options())

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
