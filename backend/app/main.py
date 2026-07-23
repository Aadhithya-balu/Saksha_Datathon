"""
SAKSHA Backend — FastAPI application entrypoint.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import configure_logging, logger
from app.database.neo4j import close_neo4j_driver, verify_neo4j_connectivity
from app.database.postgres import Base, engine
import app.models  # ensure models are registered

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")

    try:
        Base.metadata.create_all(bind=engine)
        with engine.connect():
            logger.info("PostgreSQL connection OK")
    except Exception as exc:
        logger.error(f"PostgreSQL connection failed: {exc}")


    if verify_neo4j_connectivity():
        logger.info("Neo4j connection OK")
    else:
        logger.warning("Neo4j connection could not be verified")

    yield

    close_neo4j_driver()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    description="Core backend for the SAKSHA Crime Intelligence Platform — auth, records, and APIs for the AI/ML modules.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["System"])
def health_check():
    """Liveness/readiness probe for Docker/orchestration and uptime monitoring."""
    pg_ok = True
    try:
        with engine.connect():
            pass
    except Exception:
        pg_ok = False

    neo4j_ok = verify_neo4j_connectivity()

    status_ok = pg_ok and neo4j_ok
    return {
        "status": "ok" if status_ok else "degraded",
        "postgresql": "up" if pg_ok else "down",
        "neo4j": "up" if neo4j_ok else "down",
    }


@app.get("/", tags=["System"])
def root():
    return {"message": f"{settings.APP_NAME} is running", "docs": "/docs"}
