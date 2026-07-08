"""
Application-wide logging configuration using loguru.
Import `logger` anywhere in the app for consistent, structured logs.
"""
import sys

from loguru import logger

from app.core.config import settings


def configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level="DEBUG" if settings.APP_DEBUG else "INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )
    logger.add(
        "logs/saksha_backend.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        enqueue=True,
    )


__all__ = ["logger", "configure_logging"]
