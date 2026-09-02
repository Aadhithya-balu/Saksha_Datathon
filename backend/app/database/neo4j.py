"""
Neo4j driver setup for the criminological network graph
(Criminal, Victim, Officer, Case, Vehicle, Weapon, Organization, Location nodes).
"""
from collections.abc import Generator

from neo4j import Driver, GraphDatabase

from app.core.config import settings

_driver: Driver | None = None


def get_neo4j_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver


def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def get_neo4j_session() -> Generator:
    """FastAPI dependency that yields a Neo4j session."""
    driver = get_neo4j_driver()
    session = driver.session()
    try:
        yield session
    finally:
        session.close()


import time
import socket
from urllib.parse import urlparse

_neo4j_available: bool | None = None
_last_check: float = 0.0


def verify_neo4j_connectivity() -> bool:
    global _neo4j_available, _last_check
    now = time.time()
    if _neo4j_available is not None and (now - _last_check) < 60.0:
        return _neo4j_available
    _last_check = now
    try:
        parsed = urlparse(settings.NEO4J_URI)
        host = parsed.hostname or "localhost"
        port = parsed.port or 7687
        with socket.create_connection((host, port), timeout=0.15):
            pass
        get_neo4j_driver().verify_connectivity()
        _neo4j_available = True
        return True
    except Exception:
        _neo4j_available = False
        return False
