"""
Centralized application configuration.
Loads from environment variables / .env file via pydantic-settings.
"""
from functools import lru_cache
from urllib.parse import quote_plus
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "SAKSHA Backend"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    APP_DEBUG: bool = True

    # --- PostgreSQL ---
    POSTGRES_DATABASE_URL: str = "postgresql+psycopg2://saksha_user:saksha_user@localhost:5432/saksha_db"
    SUPABASE_DB_HOST: str | None = None
    SUPABASE_DB_PORT: int = 6543
    SUPABASE_DB_NAME: str | None = None
    SUPABASE_DB_USER: str | None = None
    SUPABASE_DB_PASSWORD: str | None = None
    SUPABASE_DB_SSLMODE: str = "require"

    # --- Neo4j Aura ---
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j"

    # --- JWT ---
    JWT_SECRET_KEY: str = "super-secret-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        """Build a SQLAlchemy database URL from Supabase settings when provided."""
        if self.SUPABASE_DB_HOST and self.SUPABASE_DB_NAME and self.SUPABASE_DB_USER and self.SUPABASE_DB_PASSWORD:
            user = quote_plus(self.SUPABASE_DB_USER)
            password = quote_plus(self.SUPABASE_DB_PASSWORD)
            db_url = (
                f"postgresql+psycopg2://{user}:{password}@"
                f"{self.SUPABASE_DB_HOST}:{self.SUPABASE_DB_PORT}/{self.SUPABASE_DB_NAME}"
                f"?sslmode={self.SUPABASE_DB_SSLMODE}"
            )
            # pgbouncer=true is a Supabase hint not supported by psycopg2 — omit it
            return db_url
        return self.POSTGRES_DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
