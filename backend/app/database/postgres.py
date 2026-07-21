"""Database connection setup with automatic SQLite fallback & demo user seeding when PostgreSQL is offline."""
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings
from app.core.logging_config import logger


class Base(DeclarativeBase):
    pass


def _seed_initial_data(eng):
    """Seed default roles and demo login accounts into the database if missing."""
    try:
        from sqlalchemy.orm import Session
        import app.models  # noqa: F401
        from app.models.role import Role
        from app.models.user import User
        from app.core.security import hash_password

        Base.metadata.create_all(bind=eng)

        with Session(eng) as session:
            if session.query(Role).count() == 0:
                default_roles = [
                    Role(name="admin", description="System Administrator"),
                    Role(name="crime_analyst", description="Crime Analyst"),
                    Role(name="investigator", description="Investigator"),
                    Role(name="policymaker", description="Policymaker"),
                    Role(name="scrb", description="SCRB Officer"),
                    Role(name="sp", description="Superintendent of Police"),
                    Role(name="inspector", description="Inspector"),
                    Role(name="forensic", description="Forensic Specialist"),
                ]
                session.add_all(default_roles)
                session.commit()

            roles_by_name = {r.name: r for r in session.query(Role).all()}
            admin_role = roles_by_name.get("admin") or list(roles_by_name.values())[0]

            demo_users = [
                ("SCRB-7740", "scrb7740@ksp.gov.in", "SCRB Commander Swamy", "123456", roles_by_name.get("scrb", admin_role)),
                ("SP-0088", "sp0088@ksp.gov.in", "Superintendent SP-0088", "123456", roles_by_name.get("sp", admin_role)),
                ("admin", "admin@ksp.gov.in", "System Administrator", "123456", admin_role),
                ("INSP-1111", "insp1111@ksp.gov.in", "Test Inspector", "123456", roles_by_name.get("inspector", admin_role)),
                ("FOR-2222", "for2222@ksp.gov.in", "Test Forensic", "123456", roles_by_name.get("forensic", admin_role)),
            ]

            for username, email, full_name, password, role in demo_users:
                if role and not session.query(User).filter(User.username == username).first():
                    usr = User(
                        username=username,
                        email=email,
                        full_name=full_name,
                        hashed_password=hash_password(password),
                        is_active=True,
                        role_id=role.id,
                        district="Bengaluru",
                        station="Central Station",
                    )
                    session.add(usr)
            session.commit()
            logger.info("Database roles & demo user accounts initialized successfully.")
    except Exception as err:
        logger.error(f"Failed to seed initial database records: {err}")


def _create_db_engine():
    """Attempt PostgreSQL connection; fallback seamlessly to local SQLite if unreachable."""
    pg_url = settings.DATABASE_URL
    try:
        url = make_url(pg_url)
        if url.drivername.startswith("sqlite"):
            eng = create_engine(pg_url, connect_args={"check_same_thread": False}, echo=settings.debug_enabled)
            with eng.connect():
                pass
            _seed_initial_data(eng)
            return eng

        connect_args = {"connect_timeout": 3} if url.drivername.startswith("postgresql") else {}
        options = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            "pool_recycle": 1800,
            "connect_args": connect_args,
            "echo": settings.debug_enabled,
        }
        eng = create_engine(pg_url, **options)
        with eng.connect():
            pass
        logger.info("Connected to primary PostgreSQL database.")
        _seed_initial_data(eng)
        return eng
    except Exception as exc:
        logger.warning(f"PostgreSQL unreachable ({exc}). Falling back to embedded local SQLite database.")
        sqlite_url = "sqlite:///./saksha.db"
        eng = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        _seed_initial_data(eng)
        return eng


engine = _create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """FastAPI dependency yielding DB session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
