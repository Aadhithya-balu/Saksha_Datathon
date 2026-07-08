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
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
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


def verify_neo4j_connectivity() -> bool:
    try:
        get_neo4j_driver().verify_connectivity()
        return True
    except Exception:
        return False
