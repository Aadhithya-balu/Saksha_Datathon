"""
Quick-start table creation for the datathon timeline.
Run: python -m app.database.init_db
For production, use Alembic migrations:
    alembic upgrade head          # apply pending migrations
    alembic revision --autogenerate -m "description"  # generate new migration
"""
from app.database.postgres import Base, engine
from app.models import *  # noqa: F401,F403  (ensures all models are registered)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully.")

    # Stamp Alembic head so future ``alembic upgrade head`` is a no-op
    try:
        from alembic.config import Config
        from alembic import command
        from pathlib import Path

        alembic_cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        command.stamp(alembic_cfg, "head")
        print("Alembic revision stamped to head.")
    except Exception as exc:
        print(f"Alembic stamp skipped ({exc}). Run 'alembic stamp head' manually.")


if __name__ == "__main__":
    init_db()
