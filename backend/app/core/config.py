"""Centralized application configuration."""
from functools import lru_cache
from pathlib import Path
from typing import List
from urllib.parse import quote_plus

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "SAKSHA Backend"
    APP_ENV: str = "development"
    API_V2_PREFIX: str = "/api/v2"
    APP_DEBUG: bool = True
    DEBUG: bool = True

    # --- PostgreSQL / Supabase PostgreSQL ---
    DATABASE_URL: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int = 5432
    POSTGRES_SSLMODE: str | None = None
    SUPABASE_DB_HOST: str | None = None
    SUPABASE_DB_PORT: int = 5432
    SUPABASE_DB_NAME: str | None = None
    SUPABASE_DB_USER: str | None = None
    SUPABASE_DB_PASSWORD: str | None = None
    SUPABASE_DB_SSLMODE: str = "require"

    # --- Supabase Auth (REST API) ---
    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None

    # --- Neo4j ---
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_USERNAME: str | None = None
    NEO4J_PASSWORD: str = "neo4j"

    # --- JWT ---
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- LLM ---
    # "auto" (default) builds a failover chain in priority order: groq -> gemini -> openai,
    # then falls back to local templates when no keys are configured.
    # Explicit values: "groq" | "gemini" | "openai" | "local".
    LLM_PROVIDER: str = "auto"
    LLM_MODEL: str = ""  # optional explicit model override for the selected provider
    # Comma-separated key lists are supported ("key1,key2"): when one key hits
    # its usage/rate limit the generator automatically rotates to the next.
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # --- CORS ---
    ALLOWED_ORIGINS: str = "https://saksha-datathon-csbcweuf.onslate.in,http://localhost:3000,http://localhost:5173"

    model_config = SettingsConfigDict(env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_jwt_secret(self):
        if not self.JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY must be set in environment. Refusing to start with empty secret.")
        return self

    @field_validator("DEBUG", "APP_DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return True
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y", "on", "debug", "development", "dev"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", "release", "production", "prod"}:
            return False
        return False

    @model_validator(mode="after")
    def derive_database_url(self):
        if self.NEO4J_USERNAME and self.NEO4J_USER == "neo4j":
            self.NEO4J_USER = self.NEO4J_USERNAME

        if self.DATABASE_URL:
            return self

        if self.SUPABASE_DB_HOST and self.SUPABASE_DB_USER and self.SUPABASE_DB_PASSWORD:
            user = quote_plus(self.SUPABASE_DB_USER)
            password = quote_plus(self.SUPABASE_DB_PASSWORD)
            db_name = quote_plus(self.SUPABASE_DB_NAME or "postgres")
            self.DATABASE_URL = (
                f"postgresql+psycopg2://{user}:{password}"
                f"@{self.SUPABASE_DB_HOST}:{self.SUPABASE_DB_PORT}/{db_name}"
                f"?sslmode={quote_plus(self.SUPABASE_DB_SSLMODE)}"
            )
            return self

        if self.POSTGRES_HOST and self.POSTGRES_USER and self.POSTGRES_PASSWORD:
            user = quote_plus(self.POSTGRES_USER)
            password = quote_plus(self.POSTGRES_PASSWORD)
            db_name = quote_plus(self.POSTGRES_DB or "postgres")
            query = f"?sslmode={quote_plus(self.POSTGRES_SSLMODE)}" if self.POSTGRES_SSLMODE else ""
            self.DATABASE_URL = (
                f"postgresql+psycopg2://{user}:{password}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{db_name}{query}"
            )
            return self

        self.DATABASE_URL = "sqlite:///./saksha.db"
        return self

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def debug_enabled(self) -> bool:
        return bool(self.APP_DEBUG and self.DEBUG)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
