from app.core.config import Settings


def test_neo4j_username_alias_populates_user():
    settings = Settings(
        _env_file=None,
        DATABASE_URL="sqlite:///:memory:",
        NEO4J_USERNAME="aura-user",
        NEO4J_PASSWORD="secret",
        JWT_SECRET_KEY="test-secret-key-for-unit-test",
    )

    assert settings.NEO4J_USER == "aura-user"


def test_supabase_configuration_takes_precedence_over_demo_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(
        _env_file=None,
        SUPABASE_DB_HOST="aws-0-ap-south-1.pooler.supabase.com",
        SUPABASE_DB_PORT=6543,
        SUPABASE_DB_NAME="postgres",
        SUPABASE_DB_USER="postgres.projectref",
        SUPABASE_DB_PASSWORD="test-password",
        JWT_SECRET_KEY="test-secret-key-for-unit-test",
    )

    assert settings.DATABASE_URL == (
        "postgresql+psycopg2://postgres.projectref:test-password"
        "@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
    )
