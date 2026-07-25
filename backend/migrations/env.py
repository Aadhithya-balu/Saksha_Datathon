"""Alembic environment for Saksha.

Reads DATABASE_URL from app.core.config.settings and uses the full model
registry via app.models (which imports every ORM class).
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Alembic Config object ───────────────────────────────────────────────────
config = context.config

# ── Logging ──────────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import all models so metadata is populated ──────────────────────────────
# app.models.__init__ imports every ORM class, which registers them with
# SQLAlchemy's mapper so autogenerate can detect all tables.
import app.models  # noqa: F401, E402
from app.database.postgres import Base  # noqa: E402
from app.core.config import settings    # noqa: E402

# ── Override sqlalchemy.url from application settings ────────────────────────
# This ensures Alembic always connects to the same database as the app.
# We escape % chars for configparser and set directly on file_config to
# avoid interpolation issues with postgres URLs containing %21 etc.
if settings.DATABASE_URL:
    safe_url = settings.DATABASE_URL.replace("%", "%%")
    config.file_config.set(config.config_ini_section, "sqlalchemy.url", safe_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL without connecting to a live database — useful for
    generating SQL scripts or checking autogenerate output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Connects to the live database and applies migration scripts.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
