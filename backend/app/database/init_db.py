"""
Quick-start table creation for the datathon timeline.
Run: python -m app.database.init_db
For production, replace with Alembic migrations (alembic upgrade head).
"""
from app.database.postgres import Base, engine
from app.models import *  # noqa: F401,F403  (ensures all models are registered)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully.")


if __name__ == "__main__":
    init_db()
