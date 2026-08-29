"""Centralized application configuration."""
from functools import lru_cache
from pathlib import Path
import secrets
from typing import List
from urllib.parse import quote_plus

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent

# Canonical allowed data modes (Issue #190). A 'mixed' provenance state is
# deliberately never a runtime mode — mixed provenance is reported through the
# provenance pipeline, not configured.
VALID_DATA_MODES: tuple[str, ...] = ("production", "demo", "test")


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "SAKSHA Backend"
    APP_ENV: str = "development"
    API_V2_PREFIX: str = "/api/v2"
    # Debug defaults to OFF; must be explicitly enabled per environment.
    APP_DEBUG: bool = False
    DEBUG: bool = False

    # --- Data Mode (Issue #162, #190) ---
    # Controls whether fallback to demo/seed data is permitted and whether
    # DEMO badges are shown.  Valid values: 'production', 'demo', 'test'.
    # Production mode disables silent fallback to synthetic intelligence.
    # An invalid/missing value fails safely (defaults to 'demo', never to a
    # permissive mode that could silently present seed data as live).
    SAKSHA_DATA_MODE: str = "demo"

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
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    # --- Neo4j ---
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_USERNAME: str | None = None
    NEO4J_PASSWORD: str = "neo4j"

    # --- JWT ---
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Brute-force protection (account lockout) ---
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # --- Global API rate limiting (sliding window, per client IP) ---
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_REQUESTS: int = 300            # general API budget per IP/min
    RATE_LIMIT_AUTH_MAX_REQUESTS: int = 20        # /auth/* (login, refresh, register)
    RATE_LIMIT_UPLOAD_MAX_REQUESTS: int = 30      # evidence/file upload endpoints
    RATE_LIMIT_AI_MAX_REQUESTS: int = 40          # AI chat / prediction endpoints
    # When the backend runs behind the packaged nginx reverse proxy, the socket
    # peer is always the proxy (127.0.0.1), so `request.client.host` is the same
    # for every user. Trusting the X-Forwarded-For / X-Real-IP headers (which
    # nginx forwards) keys each budget on the real client IP instead of
    # throttling the whole user base as one. Set to false ONLY if the backend is
    # directly reachable without a trusted proxy (a spoofable header would then
    # let clients rotate their own budget).
    RATE_LIMIT_TRUST_XFF: bool = True

    # --- Notification broadcast deduplication ---
    # An identical broadcast (same notification_type + category + subject +
    # title) created within this many hours is treated as a duplicate and is
    # NOT re-created for every user. Guards against page-reload/tab/retry loops
    # flooding the notification center (e.g. repeated hotspot spike alerts).
    NOTIFICATION_BROADCAST_DEDUP_HOURS: int = 24

    # --- Request body size limit (bytes). Evidence uploads are separately
    # capped at MAX_FILE_SIZE_MB; this is a coarse DoS guard for JSON bodies.
    MAX_REQUEST_BODY_BYTES: int = 2 * 1024 * 1024

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
    # LLM generation controls for the AI chat (configurable so operators can
    # tune creativity/output length without code changes).
    LLM_CHAT_TEMPERATURE: float = 0.3
    LLM_CHAT_MAX_TOKENS: int = 2048

    # --- AI model auto-refresh (issue #145) ---
    # When enabled, inference entrypoints compare each trained artifact's
    # training timestamp against the newest relevant database record and kick
    # off a throttled background retrain when the data has moved forward.
    AUTO_RETRAIN_ENABLED: bool = True
    AUTO_RETRAIN_MIN_INTERVAL_SECONDS: int = 300

    # --- File Storage ---
    # When SUPABASE_STORAGE_BUCKET is set, uploaded evidence files are stored in
    # Supabase Storage (persistent across restarts/deployments). When unset the
    # backend falls back to the local UPLOAD_DIR (development only).
    SUPABASE_STORAGE_BUCKET: str = "evidence-files"
    # Override the local upload directory (used only when Supabase Storage is
    # unavailable, e.g. during local development without a storage key).
    UPLOAD_DIR: str = ""

    # --- CORS ---
    ALLOWED_ORIGINS: str = "https://saksha-datathon-csbcweuf.onslate.in,http://localhost:3000,http://localhost:5173"

    model_config = SettingsConfigDict(env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_jwt_secret(self):
        if not self.JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY must be set in environment. Refusing to start with empty secret.")
        # Enforce secret strength everywhere except the ephemeral test
        # environment, where tests bootstrap their own throwaway key.
        if self.APP_ENV != "test" and len(self.JWT_SECRET_KEY) < 64:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 64 characters. "
                "Generate one with: py -c \"import secrets; print(secrets.token_hex(64))\""
            )
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

    @field_validator("SAKSHA_DATA_MODE", mode="before")
    @classmethod
    def validate_data_mode(cls, value):
        """Fail safely on an invalid or missing data mode (Issue #190 §3).

        Valid values: 'production', 'demo', 'test'.  Any other value is
        rejected with a clear error rather than silently defaulting to a
        permissive mode, so no deployment can accidentally present seed/demo
        data as live operational data.
        """
        if value is None or str(value).strip() == "":
            raise ValueError(
                "SAKSHA_DATA_MODE must be one of 'production', 'demo', 'test'. "
                "Refusing to start with an unset/missing data mode."
            )
        normalized = str(value).strip().lower()
        if normalized not in VALID_DATA_MODES:
            raise ValueError(
                f"SAKSHA_DATA_MODE={value!r} is invalid. "
                "Must be one of 'production', 'demo', 'test'."
            )
        return normalized

    @staticmethod
    def _is_placeholder(value: str | None) -> bool:
        """Detect placeholder env-var values like ``<your-supabase-db-host>``."""
        if not value:
            return True
        stripped = value.strip()
        if stripped.startswith("<") and stripped.endswith(">"):
            return True
        return False

    @model_validator(mode="after")
    def derive_database_url(self):
        if self.NEO4J_USERNAME and self.NEO4J_USER == "neo4j":
            self.NEO4J_USER = self.NEO4J_USERNAME

        if self.DATABASE_URL:
            return self

        if (
            self.SUPABASE_DB_HOST
            and self.SUPABASE_DB_USER
            and self.SUPABASE_DB_PASSWORD
            and not self._is_placeholder(self.SUPABASE_DB_HOST)
            and not self._is_placeholder(self.SUPABASE_DB_USER)
            and not self._is_placeholder(self.SUPABASE_DB_PASSWORD)
        ):
            user = quote_plus(self.SUPABASE_DB_USER)
            password = quote_plus(self.SUPABASE_DB_PASSWORD)
            db_name = quote_plus(self.SUPABASE_DB_NAME or "postgres")
            self.DATABASE_URL = (
                f"postgresql+psycopg2://{user}:{password}"
                f"@{self.SUPABASE_DB_HOST}:{self.SUPABASE_DB_PORT}/{db_name}"
                f"?sslmode={quote_plus(self.SUPABASE_DB_SSLMODE)}"
            )
            return self

        if (
            self.POSTGRES_HOST
            and self.POSTGRES_USER
            and self.POSTGRES_PASSWORD
            and not self._is_placeholder(self.POSTGRES_HOST)
            and not self._is_placeholder(self.POSTGRES_USER)
            and not self._is_placeholder(self.POSTGRES_PASSWORD)
        ):
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

    @model_validator(mode="after")
    def validate_cors_no_wildcard(self):
        """Reject wildcard CORS in all environments — credentialed API must never use '*'."""
        if "*" in self.cors_origins:
            raise ValueError(
                "ALLOWED_ORIGINS must not contain '*'. "
                "Configure explicit origins (e.g. http://localhost:5173)."
            )
        return self

    @model_validator(mode="after")
    def validate_production_config(self):
        """Issue #167: Production configuration safety validation.

        Enforces stricter requirements when APP_ENV=production to prevent
        deployment with insecure defaults (weak secrets, wildcard CORS,
        default DB passwords, debug mode enabled).
        """
        if self.APP_ENV not in ("production", "prod"):
            return self  # Skip production checks in development/test

        warnings: list[str] = []
        errors: list[str] = []

        # 1. JWT secret strength: production must have high-entropy secret
        if self.JWT_SECRET_KEY:
            entropy = _estimate_jwt_entropy(self.JWT_SECRET_KEY)
            if entropy < 80:
                errors.append(
                    f"JWT_SECRET_KEY has insufficient entropy ({entropy:.0f} bits estimated). "
                    "Production requires ≥80 bits. Generate with: "
                    "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )

        # 2. CORS validation: no wildcard in production
        origins = self.cors_origins
        if "*" in origins:
            errors.append("ALLOWED_ORIGINS must not contain '*' in production. Configure explicit origins.")

        # 3. Debug mode must be OFF in production
        if self.APP_DEBUG or self.DEBUG:
            errors.append("APP_DEBUG and DEBUG must be False in production. Current configuration enables debug mode.")

        # 4. Database credential validation.  A local SQLite database has no
        # access-control boundary suitable for police records, and known
        # defaults must never be accepted merely because they were supplied
        # through environment variables.
        if self.DATABASE_URL and "sqlite" in self.DATABASE_URL:
            errors.append("Production must use PostgreSQL; SQLite is not supported for sensitive production data.")
        if self.POSTGRES_PASSWORD and self.POSTGRES_PASSWORD in ("postgres", "password", "admin", "123456"):
            errors.append("POSTGRES_PASSWORD appears to be a default/common password. Use a strong password.")
        if self.SUPABASE_DB_PASSWORD and self.SUPABASE_DB_PASSWORD in ("postgres", "password", "admin", "123456"):
            errors.append("SUPABASE_DB_PASSWORD appears to be a default/common password. Use a strong password.")

        # 5. Neo4j default credentials are a production startup failure.
        if self.NEO4J_PASSWORD == "neo4j":
            errors.append("NEO4J_PASSWORD must not use the default 'neo4j' password in production.")

        # 6. File upload directory warning
        if not self.UPLOAD_DIR and not self.SUPABASE_STORAGE_BUCKET:
            warnings.append("No UPLOAD_DIR or SUPABASE_STORAGE_BUCKET configured. Evidence uploads will fail.")

        # Store warnings and errors on the instance for startup logging
        self._production_warnings = warnings  # type: ignore[attr-defined]
        self._production_errors = errors  # type: ignore[attr-defined]

        if errors:
            import logging
            logger = logging.getLogger(__name__)
            for err in errors:
                logger.error(f"PRODUCTION CONFIG ERROR: {err}")
            raise ValueError(
                "Production configuration validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        if warnings:
            import logging
            logger = logging.getLogger(__name__)
            for warn in warnings:
                logger.warning(f"PRODUCTION CONFIG WARNING: {warn}")

        return self

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def debug_enabled(self) -> bool:
        return bool(self.APP_DEBUG and self.DEBUG)

    @property
    def production_warnings(self) -> list[str]:
        return getattr(self, "_production_warnings", [])

    @property
    def production_errors(self) -> list[str]:
        return getattr(self, "_production_errors", [])


def _estimate_jwt_entropy(secret: str) -> float:
    """Estimate the entropy of a JWT secret in bits.

    Uses a simple heuristic based on the character set size and length:
    entropy = log2(charset_size) * length

    This is a rough estimate; for cryptographic secrets generated with
    ``secrets.token_urlsafe()`` the actual entropy will be higher.
    """
    import math
    charset_size = 0
    if any(c.islower() for c in secret):
        charset_size += 26
    if any(c.isupper() for c in secret):
        charset_size += 26
    if any(c.isdigit() for c in secret):
        charset_size += 10
    special_chars = set(secret) - set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    charset_size += len(special_chars) * 4  # rough estimate for special chars
    if charset_size == 0:
        charset_size = 1  # avoid log2(0)
    return math.log2(charset_size) * len(secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
