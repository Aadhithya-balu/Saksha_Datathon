"""
Neo4j Graph Database Client & Cypher Query Engine for Criminal Intelligence.

Handles syncing relational records into graph nodes/edges and running graph queries
(shortest path, gang networks, centralities, neighborhood expansions).
"""

from typing import Any
from sqlalchemy.orm import Session, joinedload
from app.database.neo4j import get_neo4j_driver, verify_neo4j_connectivity
from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.location import Location
from app.models.victim import Victim


def is_neo4j_available() -> bool:
    """Check if Neo4j graph database is active and responsive."""
    return verify_neo4j_connectivity()


def sync_postgres_to_neo4j(db: Session) -> dict[str, int]:
    """Sync PostgreSQL entities (Criminals, Cases, Locations, Victims) into Neo4j nodes and edges."""
    if not is_neo4j_available():
        return {"synced_nodes": 0, "synced_edges": 0, "status": 0, "error": "Neo4j unavailable"}

    driver = get_neo4j_driver()
    node_count = 0
    edge_count = 0

    with driver.session() as session:
        # Create constraint indices
        session.run("CREATE CONSTRAINT criminal_id IF NOT EXISTS FOR (c:Criminal) REQUIRE c.id IS UNIQUE")
        session.run("CREATE CONSTRAINT case_id IF NOT EXISTS FOR (k:Case) REQUIRE k.id IS UNIQUE")
        session.run("CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.id IS UNIQUE")
        session.run("CREATE CONSTRAINT victim_id IF NOT EXISTS FOR (v:Victim) REQUIRE v.id IS UNIQUE")

        # 1. Sync Criminals
        criminals = db.query(Criminal).all()
        for c in criminals:
            session.run(
                """
                MERGE (cr:Criminal {id: $id})
                SET cr.name = $name,
                    cr.aliases = $aliases,
                    cr.status = $status,
                    cr.category = CASE WHEN $status = 'at_large' THEN 'suspect' ELSE 'offender' END,
                    cr.mo_summary = $mo,
                    cr.identifying_marks = $marks
                """,
                id=f"criminal-{c.id}",
                name=c.full_name,
                aliases=c.aliases or "",
                status=c.status or "active",
                mo=c.mo_summary or "",
                marks=c.identifying_marks or "",
            )
            node_count += 1

        # 2. Sync Locations
        locations = db.query(Location).all()
        for loc in locations:
            session.run(
                """
                MERGE (l:Location {id: $id})
                SET l.name = $name,
                    l.district = $district,
                    l.station = $station,
                    l.category = 'location'
                """,
                id=f"location-{loc.id}",
                name=f"{loc.station or ''}, {loc.district}",
                district=loc.district,
                station=loc.station or "",
            )
            node_count += 1

        # 3. Sync Cases & FIRs
        firs = (
            db.query(FIR)
            .options(
                joinedload(FIR.crime_case).joinedload(CrimeCase.location),
                joinedload(FIR.criminal_links).joinedload(FIRCriminalLink.criminal),
                joinedload(FIR.victim_links).joinedload(FIRVictimLink.victim),
            )
            .all()
        )

        for fir in firs:
            case_node_id = f"case-{fir.id}"
            session.run(
                """
                MERGE (cs:Case {id: $id})
                SET cs.name = $fir_number,
                    cs.complainant = $complainant,
                    cs.sections = $sections,
                    cs.category = 'case',
                    cs.filed_at = $filed_at
                """,
                id=case_node_id,
                fir_number=fir.fir_number,
                complainant=fir.complainant_name,
                sections=fir.sections or "",
                filed_at=fir.filed_at.isoformat() if fir.filed_at else "",
            )
            node_count += 1

            if fir.crime_case and fir.crime_case.location:
                loc_id = f"location-{fir.crime_case.location.id}"
                session.run(
                    """
                    MATCH (cs:Case {id: $case_id})
                    MATCH (l:Location {id: $loc_id})
                    MERGE (cs)-[r:OCCURRED_AT]->(l)
                    """,
                    case_id=case_node_id,
                    loc_id=loc_id,
                )
                edge_count += 1

            for link in fir.criminal_links:
                crim_id = f"criminal-{link.criminal_id}"
                session.run(
                    """
                    MATCH (cr:Criminal {id: $crim_id})
                    MATCH (cs:Case {id: $case_id})
                    MERGE (cr)-[r:LINKED_TO]->(cs)
                    SET r.relationship = 'Accused in FIR'
                    """,
                    crim_id=crim_id,
                    case_id=case_node_id,
                )
                edge_count += 1

            for vlink in fir.victim_links:
                v = vlink.victim
                v_id = f"victim-{v.id}"
                session.run(
                    """
                    MERGE (v:Victim {id: $v_id})
                    SET v.name = $v_name,
                        v.category = 'victim'
                    """,
                    v_id=v_id,
                    v_name=v.full_name,
                )
                node_count += 1

                session.run(
                    """
                    MATCH (v:Victim {id: $v_id})
                    MATCH (cs:Case {id: $case_id})
                    MERGE (v)-[r:VICTIM_OF]->(cs)
                    """,
                    v_id=v_id,
                    case_id=case_node_id,
                )
                edge_count += 1

    return {"synced_nodes": node_count, "synced_edges": edge_count, "status": 1}


def query_shortest_path_neo4j(source_id: str, target_id: str, max_depth: int = 5) -> dict[str, Any] | None:
    """Cypher query for shortest path between two nodes in Neo4j."""
    if not is_neo4j_available():
        return None

    driver = get_neo4j_driver()
    query = f"""
    MATCH (start {{id: $source_id}}), (end {{id: $target_id}})
    MATCH p = shortestPath((start)-[*..{max_depth}]-(end))
    RETURN p
    """

    with driver.session() as session:
        result = session.run(query, source_id=source_id, target_id=target_id)
        record = result.single()
        if not record:
            return {"found": False, "distance": 0, "nodes": [], "edges": []}

        path = record["p"]
        nodes = []
        edges = []

        for node in path.nodes:
            nodes.append({
                "id": node.get("id"),
                "name": node.get("name", "Unknown"),
                "category": node.get("category", "suspect"),
                "details": node.get("mo_summary", node.get("details", "")),
                "riskScore": node.get("riskScore", 65.0),
                "casesCount": 1
            })

        for rel in path.relationships:
            edges.append({
                "source": rel.start_node.get("id"),
                "target": rel.end_node.get("id"),
                "relationship": rel.type
            })

        return {
            "found": True,
            "distance": len(path.relationships),
            "nodes": nodes,
            "edges": edges
        }
