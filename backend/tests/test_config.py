from app.core.config import Settings


def test_neo4j_username_alias_populates_user():
    settings = Settings(
        _env_file=None,
        DATABASE_URL="sqlite:///:memory:",
        NEO4J_USERNAME="aura-user",
        NEO4J_PASSWORD="secret",
    )

    assert settings.NEO4J_USER == "aura-user"
