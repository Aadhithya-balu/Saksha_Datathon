"""
Neo4j Graph Database Client & Cypher Query Engine for Criminal Intelligence.

Handles syncing relational records into graph nodes/edges and running graph queries
(shortest path, gang networks, centralities, neighborhood expansions).

Gap #129.4: sync now covers all 8 schema node types (Criminal, Victim, Officer,
Case, Vehicle, Weapon, Organization, Location) and all 7 relationship types
(KNOWS, ASSOCIATED_WITH, USED, ARRESTED_BY, LINKED_TO, OCCURRED_AT, VICTIM_OF).
Gap #129.3: adds ``fetch_full_graph_neo4j`` so production graph responses can be
served directly from Neo4j instead of always falling back to SQL reconstruction.
"""

import re
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.database.neo4j import get_neo4j_driver, verify_neo4j_connectivity
from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.location import Location


def is_neo4j_available() -> bool:
    """Check if Neo4j graph database is active and responsive."""
    return verify_neo4j_connectivity()


# Node label -> unique-constraint suffix, one entry per schema node type.
_NODE_CONSTRAINTS: list[tuple[str, str]] = [
    ("criminal_id", "Criminal"),
    ("case_id", "Case"),
    ("location_id", "Location"),
    ("victim_id", "Victim"),
    ("officer_id", "Officer"),
    ("vehicle_id", "Vehicle"),
    ("weapon_id", "Weapon"),
    ("organization_id", "Organization"),
]

_PLATE_RE = re.compile(r"\bKA[-\s]?\d{1,2}[-\s]?[A-Z]{1,3}[-\s]?\d{3,4}\b", re.IGNORECASE)
_WEAPON_KEYWORDS = [
    "knife", "pistol", "revolver", "gun", "firearm", "country-made pistol",
    "machete", "sword", "iron rod", "blade", "rifle", "explosive",
]


def _ensure_constraints(session: Any) -> None:
    for prop, label in _NODE_CONSTRAINTS:
        session.run(
            f"CREATE CONSTRAINT {prop} IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
        )


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _extract_tools(text: str) -> tuple[list[str], list[str]]:
    """Extract vehicle plates and weapon mentions from free text."""
    plates = sorted({m.group(0).upper().replace(" ", "-") for m in _PLATE_RE.finditer(text)})
    lowered = text.lower()
    weapons = sorted({w for w in _WEAPON_KEYWORDS if w in lowered})
    return plates, weapons


def sync_postgres_to_neo4j(db: Session) -> dict[str, int]:
    """Sync PostgreSQL entities into Neo4j across all schema node/relationship types."""
    if not is_neo4j_available():
        return {"synced_nodes": 0, "synced_edges": 0, "status": 0, "error": "Neo4j unavailable"}

    driver = get_neo4j_driver()
    node_count = 0
    edge_count = 0

    with driver.session() as session:
        _ensure_constraints(session)

        # 1. Sync Criminals (+ gang affiliation Organizations)
        criminals = db.query(Criminal).all()
        for c in criminals:
            cases_count = len(c.fir_links)
            risk_score = min(100.0, 45.0 + cases_count * 10)
            session.run(
                """
                MERGE (cr:Criminal {id: $id})
                SET cr.name = $name,
                    cr.aliases = $aliases,
                    cr.status = $status,
                    cr.category = CASE WHEN $status = 'at_large' THEN 'suspect' ELSE 'offender' END,
                    cr.mo_summary = $mo,
                    cr.identifying_marks = $marks,
                    cr.gang_affiliation = $gang,
                    cr.riskScore = $risk,
                    cr.casesCount = $cases
                """,
                id=f"criminal-{c.id}",
                name=c.full_name,
                aliases=c.aliases or "",
                status=c.status or "active",
                mo=c.mo_summary or "",
                marks=c.identifying_marks or "",
                gang=(c.gang_affiliation or "").strip(),
                risk=risk_score,
                cases=cases_count,
            )
            node_count += 1

            gang_name = (c.gang_affiliation or "").strip()
            if gang_name:
                session.run(
                    """
                    MERGE (o:Organization {id: $org_id})
                    SET o.name = $org_name, o.category = 'gang'
                    WITH o
                    MATCH (cr:Criminal {id: $crim_id})
                    MERGE (cr)-[r:ASSOCIATED_WITH]->(o)
                    SET r.role = 'member'
                    """,
                    org_id=f"org-{_slug(gang_name)}",
                    org_name=gang_name,
                    crim_id=f"criminal-{c.id}",
                )
                edge_count += 1

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

        # 3. Sync Cases/FIRs, officers, victims, co-accused, tools
        firs = (
            db.query(FIR)
            .options(
                joinedload(FIR.crime_case).joinedload(CrimeCase.location),
                joinedload(FIR.criminal_links).joinedload(FIRCriminalLink.criminal),
                joinedload(FIR.victim_links).joinedload(FIRVictimLink.victim),
                joinedload(FIR.investigating_officer),
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

            if fir.investigating_officer is not None:
                officer = fir.investigating_officer
                officer_id = f"officer-{officer.id}"
                session.run(
                    """
                    MERGE (of:Officer {id: $officer_id})
                    SET of.name = $officer_name,
                        of.badge_id = $badge,
                        of.rank = $rank,
                        of.district = $district,
                        of.category = 'officer'
                    """,
                    officer_id=officer_id,
                    officer_name=officer.name,
                    badge=officer.badge_number or "",
                    rank=officer.rank or "",
                    district=officer.district or "",
                )
                node_count += 1
                for link in fir.criminal_links:
                    session.run(
                        """
                        MATCH (cr:Criminal {id: $crim_id})
                        MATCH (of:Officer {id: $officer_id})
                        MERGE (cr)-[r:ARRESTED_BY]->(of)
                        SET r.relationship = 'Investigated by'
                        """,
                        crim_id=f"criminal-{link.criminal_id}",
                        officer_id=officer_id,
                    )
                    edge_count += 1

            linked_criminal_ids = [f"criminal-{link.criminal_id}" for link in fir.criminal_links]
            for link in fir.criminal_links:
                session.run(
                    """
                    MATCH (cr:Criminal {id: $crim_id})
                    MATCH (cs:Case {id: $case_id})
                    MERGE (cr)-[r:LINKED_TO]->(cs)
                    SET r.relationship = 'Accused in FIR'
                    """,
                    crim_id=f"criminal-{link.criminal_id}",
                    case_id=case_node_id,
                )
                edge_count += 1

            # Co-accused KNOWS edges between every pair sharing this FIR
            for i in range(len(linked_criminal_ids)):
                for j in range(i + 1, len(linked_criminal_ids)):
                    session.run(
                        """
                        MATCH (a:Criminal {id: $a_id})
                        MATCH (b:Criminal {id: $b_id})
                        MERGE (a)-[r:KNOWS]->(b)
                        SET r.relationship = 'Co-accused in ' + $fir_number
                        """,
                        a_id=linked_criminal_ids[i],
                        b_id=linked_criminal_ids[j],
                        fir_number=fir.fir_number,
                    )
                    edge_count += 1

            for vlink in fir.victim_links:
                v = vlink.victim
                v_id = f"victim-{v.id}"
                session.run(
                    """
                    MERGE (v:Victim {id: $v_id})
                    SET v.name = $v_name,
                        v.age = $v_age,
                        v.category = 'victim'
                    """,
                    v_id=v_id,
                    v_name=v.full_name,
                    v_age=v.age,
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

            # USED edges: vehicles/weapons extracted from narratives + MO summaries
            for link in fir.criminal_links:
                criminal = link.criminal
                text = " \n".join(filter(None, [criminal.mo_summary, fir.narrative]))
                if not text.strip():
                    continue
                plates, weapons = _extract_tools(text)
                for plate in plates:
                    vehicle_id = f"vehicle-{_slug(plate)}"
                    session.run(
                        """
                        MERGE (vh:Vehicle {id: $vehicle_id})
                        SET vh.name = $plate, vh.registration = $plate, vh.category = 'vehicle'
                        WITH vh
                        MATCH (cr:Criminal {id: $crim_id})
                        MERGE (cr)-[r:USED]->(vh)
                        SET r.relationship = 'Vehicle used in ' + $fir_number
                        """,
                        vehicle_id=vehicle_id,
                        plate=plate,
                        crim_id=f"criminal-{criminal.id}",
                        fir_number=fir.fir_number,
                    )
                    node_count += 1
                    edge_count += 1
                for weapon in weapons:
                    weapon_id = f"weapon-{_slug(weapon)}"
                    session.run(
                        """
                        MERGE (wp:Weapon {id: $weapon_id})
                        SET wp.name = $weapon_name, wp.type = $weapon_name, wp.category = 'weapon'
                        WITH wp
                        MATCH (cr:Criminal {id: $crim_id})
                        MERGE (cr)-[r:USED]->(wp)
                        SET r.relationship = 'Weapon used in ' + $fir_number
                        """,
                        weapon_id=weapon_id,
                        weapon_name=weapon.title(),
                        crim_id=f"criminal-{criminal.id}",
                        fir_number=fir.fir_number,
                    )
                    node_count += 1
                    edge_count += 1

    return {"synced_nodes": node_count, "synced_edges": edge_count, "status": 1}


def fetch_full_graph_neo4j() -> dict[str, Any] | None:
    """Fetch the entire graph (nodes + relationships) directly from Neo4j.

    Returns ``{"nodes": [...], "edges": [...]}`` shaped for NetworkNode /
    NetworkEdge models, or None when Neo4j is unavailable/empty.
    """
    if not is_neo4j_available():
        return None

    driver = get_neo4j_driver()
    with driver.session() as session:
        node_result = session.run(
            """
            MATCH (n)
            WHERE n.id IS NOT NULL
            RETURN n.id AS id, labels(n)[0] AS label, n
            """
        )
        raw_nodes = [record.data() for record in node_result]
        if not raw_nodes:
            return None

        rel_result = session.run(
            """
            MATCH (a)-[r]->(b)
            WHERE a.id IS NOT NULL AND b.id IS NOT NULL
            RETURN a.id AS source, b.id AS target, type(r) AS rel_type, r AS props
            """
        )
        raw_rels = [record.data() for record in rel_result]

    label_to_category = {
        "Criminal": "suspect",
        "Case": "case",
        "Location": "location",
        "Victim": "victim",
        "Officer": "officer",
        "Vehicle": "vehicle",
        "Weapon": "weapon",
        "Organization": "gang",
    }

    nodes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in raw_nodes:
        node_id = row["id"]
        if node_id in seen_ids:
            continue
        seen_ids.add(node_id)
        props = row["n"] or {}
        category = props.get("category") or label_to_category.get(row["label"], "suspect")
        nodes.append({
            "id": node_id,
            "name": props.get("name", node_id),
            "category": category,
            "riskScore": float(props.get("riskScore", 50.0)),
            "details": props.get("mo_summary") or props.get("details") or props.get("relationship") or "",
            "casesCount": int(props.get("casesCount", 1)),
            "gangAffiliation": props.get("gang_affiliation"),
            "status": props.get("status"),
            "district": props.get("district"),
            "date": props.get("filed_at"),
        })

    rel_label_map = {
        "KNOWS": "Known associate",
        "ASSOCIATED_WITH": "Gang / organization member",
        "USED": "Used tool or vehicle",
        "ARRESTED_BY": "Arrested / investigated by",
        "LINKED_TO": "Accused in FIR",
        "OCCURRED_AT": "Occurred At Jurisdiction",
        "VICTIM_OF": "Victim in FIR",
    }
    edges: list[dict[str, Any]] = []
    for row in raw_rels:
        props = row["props"] or {}
        edges.append({
            "source": row["source"],
            "target": row["target"],
            "relationship": props.get("relationship") or rel_label_map.get(row["rel_type"], row["rel_type"]),
        })

    return {"nodes": nodes, "edges": edges}


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
                "casesCount": node.get("casesCount", 1),
            })

        for rel in path.relationships:
            edges.append({
                "source": rel.start_node.get("id"),
                "target": rel.end_node.get("id"),
                "relationship": rel.get("relationship") or rel.type,
            })

        return {
            "found": True,
            "distance": len(path.relationships),
            "nodes": nodes,
            "edges": edges,
        }
