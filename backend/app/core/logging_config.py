"""Application-wide logging configuration using loguru."""
import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    logger.remove()
    logger.add(
        sys.stdout,
        level="DEBUG" if settings.debug_enabled else "INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    log_path = Path("logs/saksha_backend.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_path,
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        enqueue=False,
    )
    _configured = True


__all__ = ["logger", "configure_logging"]
