"""
High-level Network Intelligence & Graph Analytics Service.

Provides Criminal Relationship Graph, Case Relationship Graph, Gang Networks,
Link Analysis, Shortest Path Analysis, Timeline Integration, and AI Graph Insights.

Gap #129.2: all fabricated seed nodes/edges and hardcoded syndicate rosters were
removed — every node/edge is now derived from PostgreSQL records or Neo4j.
Gap #129.3: full-graph reads prefer a live Neo4j instance and fall back to SQL;
the silent FIR ``limit(100)`` truncation was removed.
Issue #144 gap 132.4: records originating from the bundled demo seed dataset
are flagged (``isSeed`` / ``is_demo_derived`` / ``dataset_scope``) so UIs can
visually separate seeded demo content from live intelligence.
"""

from collections import Counter, defaultdict, deque
from datetime import datetime
from functools import lru_cache
from typing import Any
from sqlalchemy.orm import Session, joinedload

from app.models.crime import CrimeCase
from app.models.criminal import Criminal
from app.models.fir import FIR, FIRCriminalLink, FIRVictimLink
from app.models.network import (
    AIGraphInsight,
    CentralityMetric,
    GangHierarchyMember,
    GangNetworkSummary,
    LinkAnalysisResponse,
    NetworkEdge,
    NetworkGraphResponse,
    NetworkNode,
    NetworkNodeCategory,
    ShortestPathResponse,
)
from app.services.neo4j.client import fetch_full_graph_neo4j, is_neo4j_available, query_shortest_path_neo4j


@lru_cache(maxsize=1)
def _seed_identity_sets() -> tuple[set[str], set[str], set[str]]:
    """Names/numbers identifying bundled demo-seed records (gap 132.4).

    Lazily imports the seed manifest so importing this service never pays the
    cost (or risk) of loading the seeder module in production contexts where
    it may be absent.
    """
    try:
        from app.database.seed_db import CASES, CRIMINALS, VICTIMS

        return (
            {row[0] for row in CASES},      # exact case numbers
            {c[0] for c in CRIMINALS},      # criminal full names
            {v[0] for v in VICTIMS},        # victim full names
        )
    except Exception:  # pragma: no cover - manifest unavailable
        return set(), set(), set()


def _is_seed_case_number(case_number: str | None) -> bool:
    if not case_number:
        return False
    case_numbers, _, _ = _seed_identity_sets()
    return case_number in case_numbers or case_number.startswith("CR-2026-SYN-")


def _apply_seed_flags(nodes: list[NetworkNode], edges: list[NetworkEdge] | None = None) -> None:
    """Flag demo-seed origin on already-built nodes and edges (used for Neo4j path)."""
    case_numbers, criminal_names, victim_names = _seed_identity_sets()
    seed_node_ids = set()
    for node in nodes:
        if node.category in (NetworkNodeCategory.SUSPECT, NetworkNodeCategory.OFFENDER):
            node.isSeed = node.name in criminal_names
        elif node.category == NetworkNodeCategory.VICTIM:
            node.isSeed = node.name in victim_names
        elif node.category == NetworkNodeCategory.CASE:
            node.isSeed = any(cnum in node.name or cnum in node.details for cnum in case_numbers) or "SYN" in node.name
        if node.isSeed:
            seed_node_ids.add(node.id)

    if edges:
        for edge in edges:
            src_seed = edge.source in seed_node_ids
            tgt_seed = edge.target in seed_node_ids
            if src_seed and tgt_seed:
                edge.provenance = "DEMO_SEED"
                edge.is_demo_derived = True
            elif src_seed or tgt_seed:
                edge.provenance = "MIXED"
                edge.is_demo_derived = True


def _criminal_risk(criminal: Criminal) -> float:
    return min(100.0, 45.0 + len(criminal.fir_links) * 10)


def _build_sql_graph(db: Session, category_filter: str | None = None, min_risk: float = 0.0) -> tuple[list[NetworkNode], list[NetworkEdge]]:
    """Construct complete graph from PostgreSQL database relations with full provenance tracking."""
    _, seed_criminal_names, seed_victim_names = _seed_identity_sets()
    firs = (
        db.query(FIR)
        .options(
            joinedload(FIR.crime_case).joinedload(CrimeCase.location),
            joinedload(FIR.criminal_links).joinedload(FIRCriminalLink.criminal),
            joinedload(FIR.victim_links).joinedload(FIRVictimLink.victim),
        )
        .order_by(FIR.filed_at.desc())
        .all()
    )

    nodes_map: dict[str, NetworkNode] = {}
    edges_list: list[NetworkEdge] = []
    # Track co-accused pairs to aggregate multi-FIR links with calculated confidence
    co_accused_tracker: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    co_accused_seed_flags: dict[tuple[str, str], tuple[bool, bool]] = {}

    for fir in firs:
        case = fir.crime_case
        case_id = f"case-{fir.id}"
        case_is_seed = (
            _is_seed_case_number(case.case_number)
            or (case and getattr(case, "dataset_provenance", None) == "demo")
        ) if case else False
        nodes_map[case_id] = NetworkNode(
            id=case_id,
            name=f"FIR #{fir.fir_number}",
            category=NetworkNodeCategory.CASE,
            riskScore=70.0,
            details=f"Sections: {fir.sections or 'IPC'}, Complainant: {fir.complainant_name}",
            casesCount=1,
            date=fir.filed_at.isoformat() if fir.filed_at else None,
            isSeed=case_is_seed,
        )

        loc_node_id = None
        if case and case.location:
            loc_node_id = f"location-{case.location.id}"
            if loc_node_id not in nodes_map:
                nodes_map[loc_node_id] = NetworkNode(
                    id=loc_node_id,
                    name=f"{case.location.station or 'Station'}, {case.location.district}",
                    category=NetworkNodeCategory.LOCATION,
                    riskScore=60.0,
                    details=f"District: {case.location.district}",
                    casesCount=len(case.location.crimes) if hasattr(case.location, "crimes") else 1,
                    district=case.location.district,
                    isSeed=case_is_seed,
                )
            edges_list.append(NetworkEdge(
                source=case_id,
                target=loc_node_id,
                relationship="Occurred At Jurisdiction",
                relationship_type="CASE_LOCATION",
                provenance="DEMO_SEED" if case_is_seed else "DIRECT_DATABASE",
                verification_status="DEMO" if case_is_seed else "VERIFIED",
                confidence=1.0,
                confidence_level="HIGH",
                evidence=[{
                    "record_type": "fir_location",
                    "record_id": str(fir.id),
                    "record_number": fir.fir_number,
                    "details": f"FIR #{fir.fir_number} incident location jurisdiction in {case.location.district}",
                    "timestamp": fir.filed_at.isoformat() if fir.filed_at else None,
                }],
                is_demo_derived=case_is_seed,
            ))

        fir_criminals: list[tuple[str, bool]] = []
        for link in fir.criminal_links:
            criminal = link.criminal
            if criminal is None:
                continue
            crim_id = f"criminal-{criminal.id}"
            crim_is_seed = criminal.full_name in seed_criminal_names
            fir_criminals.append((crim_id, crim_is_seed))
            if crim_id not in nodes_map:
                nodes_map[crim_id] = NetworkNode(
                    id=crim_id,
                    name=criminal.full_name,
                    category=NetworkNodeCategory.SUSPECT if criminal.status == "at_large" else NetworkNodeCategory.OFFENDER,
                    riskScore=_criminal_risk(criminal),
                    details=criminal.mo_summary or criminal.identifying_marks or "Linked in FIR records",
                    casesCount=len(criminal.fir_links),
                    phone=None,
                    gangAffiliation=(criminal.gang_affiliation or "").strip() or None,
                    status=criminal.status,
                    isSeed=crim_is_seed,
                )
            # Direct database relationship: Person -> Case
            is_demo = crim_is_seed or case_is_seed
            edges_list.append(NetworkEdge(
                source=crim_id,
                target=case_id,
                relationship="Accused in FIR",
                relationship_type="PERSON_CASE",
                provenance="DEMO_SEED" if is_demo else "DIRECT_DATABASE",
                verification_status="VERIFIED",
                confidence=1.0,
                confidence_level="HIGH",
                evidence=[{
                    "record_type": "fir_charge",
                    "record_id": str(fir.id),
                    "record_number": fir.fir_number,
                    "details": f"Accused listed under sections {fir.sections or 'IPC'} in FIR #{fir.fir_number}",
                    "timestamp": fir.filed_at.isoformat() if fir.filed_at else None,
                }],
                is_demo_derived=is_demo,
            ))
            if loc_node_id:
                edges_list.append(NetworkEdge(
                    source=crim_id,
                    target=loc_node_id,
                    relationship="Operated in area",
                    relationship_type="PERSON_LOCATION",
                    provenance="DEMO_SEED" if crim_is_seed else "DIRECT_DATABASE",
                    verification_status="VERIFIED",
                    confidence=1.0,
                    confidence_level="HIGH",
                    evidence=[{
                        "record_type": "fir_jurisdiction",
                        "record_id": str(fir.id),
                        "record_number": fir.fir_number,
                        "details": f"Offence committed in {case.location.district if case and case.location else 'district'} jurisdiction",
                        "timestamp": fir.filed_at.isoformat() if fir.filed_at else None,
                    }],
                    is_demo_derived=crim_is_seed,
                ))

        # Record co-accused pairs for analytical inference
        for i in range(len(fir_criminals)):
            for j in range(i + 1, len(fir_criminals)):
                c1_id, c1_seed = fir_criminals[i]
                c2_id, c2_seed = fir_criminals[j]
                pair_key = (min(c1_id, c2_id), max(c1_id, c2_id))
                co_accused_tracker[pair_key].append({
                    "record_type": "fir_co_accused",
                    "record_id": str(fir.id),
                    "record_number": fir.fir_number,
                    "sections": fir.sections or "IPC",
                    "timestamp": fir.filed_at.isoformat() if fir.filed_at else None,
                    "factors": ["Co-accused in formal FIR charge", f"Shared FIR #{fir.fir_number}"],
                })
                co_accused_seed_flags[pair_key] = (c1_seed, c2_seed)

        for vlink in fir.victim_links:
            victim = vlink.victim
            vic_id = f"victim-{victim.id}"
            vic_is_seed = victim.full_name in seed_victim_names
            if vic_id not in nodes_map:
                nodes_map[vic_id] = NetworkNode(
                    id=vic_id,
                    name=victim.full_name,
                    category=NetworkNodeCategory.VICTIM,
                    riskScore=15.0,
                    details=victim.statement or "Victim named in FIR",
                    casesCount=len(victim.fir_links),
                    isSeed=vic_is_seed,
                )
            vic_is_demo = vic_is_seed or case_is_seed
            edges_list.append(NetworkEdge(
                source=vic_id,
                target=case_id,
                relationship="Victim in FIR",
                relationship_type="PERSON_VICTIM",
                provenance="DEMO_SEED" if vic_is_demo else "DIRECT_DATABASE",
                verification_status="VERIFIED",
                confidence=1.0,
                confidence_level="HIGH",
                evidence=[{
                    "record_type": "fir_victim",
                    "record_id": str(fir.id),
                    "record_number": fir.fir_number,
                    "details": f"Victim named in FIR #{fir.fir_number}",
                    "timestamp": fir.filed_at.isoformat() if fir.filed_at else None,
                }],
                is_demo_derived=vic_is_demo,
            ))

    # Construct Analytical Co-Accused Links with Calculated Confidence
    for (c1_id, c2_id), shared_evidences in co_accused_tracker.items():
        c1_seed, c2_seed = co_accused_seed_flags.get((c1_id, c2_id), (False, False))
        is_demo_pair = c1_seed and c2_seed
        is_mixed_pair = (c1_seed != c2_seed)
        
        if is_demo_pair:
            provenance = "DEMO_SEED"
        elif is_mixed_pair:
            provenance = "MIXED"
        else:
            provenance = "ANALYTICAL_INFERENCE"
        status = "POTENTIAL"

        shared_count = len(shared_evidences)
        # Calculated confidence based on multi-incident corroboration
        if shared_count >= 2:
            confidence = min(0.95, round(0.70 + (shared_count * 0.08), 2))
            conf_level = "HIGH"
        else:
            confidence = 0.70
            conf_level = "MEDIUM"

        edges_list.append(NetworkEdge(
            source=c1_id,
            target=c2_id,
            relationship=f"Co-accused in {shared_count} FIR{'s' if shared_count > 1 else ''}",
            relationship_type="SHARED_CASE",
            provenance=provenance,
            verification_status=status,
            weight=round(1.0 + (shared_count - 1) * 0.5, 2),
            confidence=confidence,
            confidence_level=conf_level,
            evidence=shared_evidences,
            is_demo_derived=(c1_seed or c2_seed),
            operational_warning="Analytical relationship identified from available records. This does not establish a confirmed association.",
        ))

    # Investigating officers connected to their cases
    officer_ids_seen: set[str] = set()
    for fir in firs:
        if fir.investigating_officer is None:
            continue
        officer = fir.investigating_officer
        officer_node_id = f"officer-{officer.id}"
        if officer_node_id not in officer_ids_seen:
            officer_ids_seen.add(officer_node_id)
            nodes_map[officer_node_id] = NetworkNode(
                id=officer_node_id,
                name=officer.name,
                category=NetworkNodeCategory.OFFICER,
                riskScore=10.0,
                details=f"{officer.rank or 'Officer'}, {officer.station} ({officer.badge_number})",
                casesCount=len(officer.firs),
                district=officer.district,
                isSeed=False,
            )
        edges_list.append(NetworkEdge(
            source=f"case-{fir.id}",
            target=officer_node_id,
            relationship="Investigated by",
            relationship_type="PERSON_INVESTIGATION",
            provenance="DIRECT_DATABASE",
            verification_status="VERIFIED",
            confidence=1.0,
            confidence_level="HIGH",
            evidence=[{
                "record_type": "fir_assignment",
                "record_id": str(fir.id),
                "record_number": fir.fir_number,
                "details": f"Investigating Officer assigned to FIR #{fir.fir_number}",
                "timestamp": fir.filed_at.isoformat() if fir.filed_at else None,
            }],
            is_demo_derived=False,
        ))

    # Apply Category & Risk filters
    filtered_nodes = [
        n for n in nodes_map.values()
        if (not category_filter or n.category.value == category_filter) and n.riskScore >= min_risk
    ]
    valid_node_ids = {n.id for n in filtered_nodes}
    filtered_edges = [
        e for e in edges_list
        if e.source in valid_node_ids and e.target in valid_node_ids
    ]

    return filtered_nodes, filtered_edges


def _graph_response(
    nodes: list[NetworkNode],
    edges: list[NetworkEdge],
    is_neo4j_backed: bool,
    provenance_filter: str | None = None,
    exclude_demo: bool = False,
) -> NetworkGraphResponse:
    """Assemble the response with comprehensive provenance summary and filtering (Issue #159, #166)."""
    seed_node_count = sum(1 for node in nodes if node.isSeed)
    
    # Baseline summary metrics reflecting full loaded subgraph for toolbar badge counts
    summary = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "verified_relationships": sum(1 for e in edges if e.verification_status == "VERIFIED" or e.relationship_type in ("PERSON_CASE", "PERSON_LOCATION", "CASE_LOCATION", "PERSON_INVESTIGATION", "PERSON_VICTIM")),
        "analytical_relationships": sum(1 for e in edges if e.verification_status == "POTENTIAL" or e.relationship_type == "SHARED_CASE" or e.provenance == "ANALYTICAL_INFERENCE"),
        "potential_relationships": sum(1 for e in edges if e.verification_status == "POTENTIAL" or e.relationship_type == "SHARED_CASE"),
        "demo_relationships": sum(1 for e in edges if e.is_demo_derived or e.provenance in ("DEMO_SEED", "MIXED")),
        "mixed_relationships": sum(1 for e in edges if e.provenance == "MIXED"),
        "unknown_relationships": sum(1 for e in edges if e.provenance == "UNKNOWN" or e.verification_status == "UNVERIFIED"),
    }

    if exclude_demo:
        nodes = [n for n in nodes if not n.isSeed]
        valid_nids = {n.id for n in nodes}
        edges = [e for e in edges if not e.is_demo_derived and e.source in valid_nids and e.target in valid_nids]

    if provenance_filter:
        p_filter = provenance_filter.upper()
        if p_filter == "VERIFIED":
            edges = [e for e in edges if e.verification_status == "VERIFIED" or (e.relationship_type in ("PERSON_CASE", "PERSON_LOCATION", "CASE_LOCATION", "PERSON_INVESTIGATION", "PERSON_VICTIM") and e.relationship_type != "SHARED_CASE")]
        elif p_filter in ("POTENTIAL", "ANALYTICAL_INFERENCE"):
            edges = [e for e in edges if e.verification_status == "POTENTIAL" or e.relationship_type == "SHARED_CASE" or e.provenance == "ANALYTICAL_INFERENCE"]
        elif p_filter in ("DIRECT_DATABASE", "DEMO_SEED", "MIXED", "UNKNOWN", "UNVERIFIED", "DEMO"):
            edges = [e for e in edges if e.provenance == p_filter or e.verification_status == p_filter]
        connected_node_ids = {e.source for e in edges} | {e.target for e in edges}
        nodes = [n for n in nodes if n.id in connected_node_ids]

    # Issue #166: Entity type counts
    entity_counts: dict[str, int] = Counter()
    for node in nodes:
        entity_counts[node.category.value] += 1

    # Issue #166: Confidence summary
    confidence_summary: dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    for edge in edges:
        level = (edge.confidence_level or "UNKNOWN").upper()
        if level in confidence_summary:
            confidence_summary[level] += 1
        else:
            confidence_summary["UNKNOWN"] += 1

    # Issue #166: Provenance warnings
    warnings: list[str] = []
    demo_count = summary.get("demo_relationships", 0)
    mixed_count = summary.get("mixed_relationships", 0)
    unknown_count = summary.get("unknown_relationships", 0)

    if demo_count > 0:
        warnings.append(
            f"Graph contains {demo_count} DEMO/seed-derived relationship(s). "
            "Results should not be treated as live operational intelligence."
        )
    if mixed_count > 0:
        warnings.append(
            f"Graph contains {mixed_count} mixed-source relationship(s) involving both "
            "LIVE and DEMO data. Interpret these connections with caution."
        )
    if unknown_count > 0:
        warnings.append(
            f"Graph contains {unknown_count} relationship(s) with unknown data provenance "
            "that should be interpreted cautiously."
        )

    return NetworkGraphResponse(
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
        is_neo4j_backed=is_neo4j_backed,
        seed_node_count=seed_node_count,
        dataset_scope="contains_seed_demo_records" if seed_node_count or summary["demo_relationships"] else "live_records",
        provenance_summary=summary,
        entity_counts=dict(entity_counts),
        warnings=warnings,
        confidence_summary=confidence_summary,
    )


def get_full_network_graph(
    db: Session,
    category_filter: str | None = None,
    min_risk: float = 0.0,
    provenance_filter: str | None = None,
    exclude_demo: bool = False,
    limit: int = 500,
) -> NetworkGraphResponse:
    """Fetch complete or filtered relationship network (Neo4j-first, SQL fallback)."""
    neo4j_data = fetch_full_graph_neo4j() if is_neo4j_available() else None
    if neo4j_data:
        nodes = [NetworkNode(**n) for n in neo4j_data["nodes"]]
        edges = [NetworkEdge(**e) for e in neo4j_data["edges"]]
        _apply_seed_flags(nodes, edges)
        filtered_nodes = [
            n for n in nodes
            if (not category_filter or n.category.value == category_filter) and n.riskScore >= min_risk
        ]
        valid_ids = {n.id for n in filtered_nodes}
        filtered_edges = [e for e in edges if e.source in valid_ids and e.target in valid_ids]
        return _graph_response(
            filtered_nodes[:limit],
            [e for e in filtered_edges if e.source in {n.id for n in filtered_nodes[:limit]} and e.target in {n.id for n in filtered_nodes[:limit]}],
            is_neo4j_backed=True,
            provenance_filter=provenance_filter,
            exclude_demo=exclude_demo,
        )

    nodes, edges = _build_sql_graph(db, category_filter=category_filter, min_risk=min_risk)
    limited_nodes = nodes[:limit]
    limited_ids = {n.id for n in limited_nodes}
    limited_edges = [e for e in edges if e.source in limited_ids and e.target in limited_ids]
    return _graph_response(
        limited_nodes,
        limited_edges,
        is_neo4j_backed=False,
        provenance_filter=provenance_filter,
        exclude_demo=exclude_demo,
    )


def get_person_network_graph(
    db: Session,
    person_id: str,
    depth: int = 1,
    provenance_filter: str | None = None,
    exclude_demo: bool = False,
) -> NetworkGraphResponse:
    """Fetch relationship graph centered on a specific person or node."""
    nodes, edges = _build_sql_graph(db)
    if person_id not in {n.id for n in nodes}:
        return NetworkGraphResponse(
            nodes=[],
            edges=[],
            total_nodes=0,
            total_edges=0,
            is_neo4j_backed=is_neo4j_available(),
            provenance_summary={
                "total_nodes": 0, "total_edges": 0, "verified_relationships": 0,
                "analytical_relationships": 0, "potential_relationships": 0,
                "demo_relationships": 0, "mixed_relationships": 0, "unknown_relationships": 0,
            },
        )
    target_id = person_id

    visited_nodes: set[str] = {target_id}
    current_frontier = {target_id}

    for _ in range(depth):
        next_frontier = set()
        for edge in edges:
            if edge.source in current_frontier:
                next_frontier.add(edge.target)
            elif edge.target in current_frontier:
                next_frontier.add(edge.source)
        visited_nodes.update(next_frontier)
        current_frontier = next_frontier

    sub_nodes = [n for n in nodes if n.id in visited_nodes]
    sub_edges = [e for e in edges if e.source in visited_nodes and e.target in visited_nodes]

    return _graph_response(
        sub_nodes,
        sub_edges,
        is_neo4j_backed=is_neo4j_available(),
        provenance_filter=provenance_filter,
        exclude_demo=exclude_demo,
    )


def get_case_network_graph(
    db: Session,
    case_id: str,
    provenance_filter: str | None = None,
    exclude_demo: bool = False,
) -> NetworkGraphResponse:
    """Fetch case relationship graph."""
    normalized = case_id if case_id.startswith(("case-", "fir-")) else f"case-{case_id}"
    return get_person_network_graph(
        db,
        normalized,
        depth=2,
        provenance_filter=provenance_filter,
        exclude_demo=exclude_demo,
    )


def get_organization_gang_networks(db: Session) -> list[GangNetworkSummary]:
    """Derive organized-crime gang hierarchies from criminal gang affiliations."""
    criminals = (
        db.query(Criminal)
        .options(joinedload(Criminal.fir_links))
        .all()
    )

    by_gang: dict[str, list[Criminal]] = defaultdict(list)
    for criminal in criminals:
        gang_name = (criminal.gang_affiliation or "").strip()
        if gang_name:
            by_gang[gang_name].append(criminal)

    summaries: list[GangNetworkSummary] = []
    _, seed_criminal_names, _ = _seed_identity_sets()
    for gang_name, members in sorted(by_gang.items()):
        ranked = sorted(members, key=lambda c: (len(c.fir_links), _criminal_risk(c)), reverse=True)
        leader = ranked[0]
        avg_risk = sum(_criminal_risk(c) for c in members) / len(members)
        # Gap 132.4: a gang is demo-derived when every member offender comes
        # from the bundled seed dataset rather than live records.
        all_seeded = bool(members) and all(m.full_name in seed_criminal_names for m in members)

        hierarchy_members = []
        hierarchy_edges = []
        for idx, member in enumerate(ranked[:10]):
            role = "Kingpin" if idx == 0 else ("Lieutenant" if idx <= 2 else "Operative")
            hierarchy_members.append(GangHierarchyMember(
                id=f"criminal-{member.id}",
                name=member.full_name,
                role=role,
                rank_level=idx + 1,
                riskScore=_criminal_risk(member),
                status=member.status or "unknown",
                casesCount=len(member.fir_links),
                isSeed=member.full_name in seed_criminal_names,
            ))
            if idx > 0:
                hierarchy_edges.append(NetworkEdge(
                    source=f"criminal-{leader.id}",
                    target=f"criminal-{member.id}",
                    relationship="Reports to" if idx <= 2 else "Associated with",
                    relationship_type="GANG_ASSOCIATION",
                    provenance="DEMO_SEED" if all_seeded else "ANALYTICAL_INFERENCE",
                    verification_status="DEMO" if all_seeded else "POTENTIAL",
                    confidence=0.85 if idx <= 2 else 0.70,
                    confidence_level="HIGH" if idx <= 2 else "MEDIUM",
                    evidence=[{
                        "record_type": "gang_affiliation",
                        "details": f"Mutual recorded gang affiliation: '{gang_name}'",
                    }],
                    is_demo_derived=all_seeded,
                    operational_warning="Analytical relationship identified from available records. This does not establish a confirmed association.",
                ))

        risk_level = "CRITICAL" if avg_risk >= 80 else ("HIGH" if avg_risk >= 65 else "MODERATE")
        summaries.append(GangNetworkSummary(
            gang_id=f"gang-{_gang_slug(gang_name)}",
            name=gang_name,
            leader_name=leader.full_name,
            leader_id=f"criminal-{leader.id}",
            active_members=len(members),
            risk_level=risk_level,
            territory=", ".join(sorted({lk.fir.crime_case.location.district for lk in leader.fir_links if lk.fir and lk.fir.crime_case and lk.fir.crime_case.location})),
            primary_racket="Derived from linked FIR categories" ,
            members=hierarchy_members,
            relationships=hierarchy_edges,
            is_demo_derived=all_seeded,
        ))
    return summaries


def _gang_slug(value: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-") or "unknown"


def find_shortest_path(db: Session, source_id: str, target_id: str, max_depth: int = 5) -> ShortestPathResponse:
    """Find shortest path between two nodes using Neo4j or BFS on SQL graph."""
    if is_neo4j_available():
        neo_res = query_shortest_path_neo4j(source_id, target_id, max_depth)
        if neo_res and neo_res["found"]:
            return ShortestPathResponse(
                found=True,
                distance=neo_res["distance"],
                path_nodes=[NetworkNode(**n) for n in neo_res["nodes"]],
                path_edges=[NetworkEdge(**e) for e in neo_res["edges"]],
                explanation=f"Neo4j pathfinder identified {neo_res['distance']} degree separation.",
            )

    nodes, edges = _build_sql_graph(db)
    nodes_by_id = {n.id: n for n in nodes}

    if source_id not in nodes_by_id or target_id not in nodes_by_id:
        missing = [sid for sid in (source_id, target_id) if sid not in nodes_by_id]
        return ShortestPathResponse(
            found=False,
            distance=0,
            path_nodes=[],
            path_edges=[],
            explanation=(
                f"No path computed: entity reference(s) not present in current network data: "
                f"{', '.join(missing)}."
            ),
        )

    s_id, t_id = source_id, target_id

    adj = defaultdict(list)
    edge_map = {}
    for edge in edges:
        adj[edge.source].append(edge.target)
        adj[edge.target].append(edge.source)
        edge_map[(edge.source, edge.target)] = edge
        edge_map[(edge.target, edge.source)] = edge

    queue = deque([[s_id]])
    visited = {s_id}
    found_path = None

    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == t_id:
            found_path = path
            break
        if len(path) > max_depth + 1:
            continue
        for neighbor in adj[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    if not found_path:
        return ShortestPathResponse(
            found=False,
            distance=0,
            path_nodes=[],
            path_edges=[],
            explanation=f"No relationship path within {max_depth} degrees between selected entities.",
        )

    path_nodes = [nodes_by_id[nid] for nid in found_path]
    path_edges = []
    for i in range(len(found_path) - 1):
        u, v = found_path[i], found_path[i + 1]
        e = edge_map.get((u, v))
        if e:
            path_edges.append(e)
        else:
            path_edges.append(NetworkEdge(
                source=u,
                target=v,
                relationship="Linked Relationship",
                relationship_type="OTHER",
                provenance="UNKNOWN",
                verification_status="UNVERIFIED",
                confidence=None,
                confidence_level="UNKNOWN",
            ))

    return ShortestPathResponse(
        found=True,
        distance=len(path_edges),
        path_nodes=path_nodes,
        path_edges=path_edges,
        explanation=f"Found {len(path_edges)}-hop connection chain: {' -> '.join([n.name for n in path_nodes])}.",
    )


def perform_link_analysis(db: Session) -> LinkAnalysisResponse:
    """Compute network centrality, bridge nodes, broker scores, and graph density."""
    nodes, edges = _build_sql_graph(db)
    degree_counts = Counter()
    adjacency: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        degree_counts[e.source] += 1
        degree_counts[e.target] += 1
        adjacency[e.source].add(e.target)
        adjacency[e.target].add(e.source)

    total_nodes = len(nodes)
    max_possible_edges = (total_nodes * (total_nodes - 1)) / 2 if total_nodes > 1 else 1
    density = round(len(edges) / max_possible_edges, 3)

    centralities: list[CentralityMetric] = []
    for n in nodes:
        deg = degree_counts[n.id]
        norm_deg = round(deg / (total_nodes - 1), 3) if total_nodes > 1 else 0.0
        # Betweenness approximated via neighbor diversity: a node connecting
        # otherwise-disconnected neighbors acts as a bridge/broker.
        neighbor_count = len(adjacency[n.id])
        inter_links = sum(
            1 for x in adjacency[n.id] for y in adjacency[n.id]
            if x < y and y in adjacency[x]
        )
        possible_pairs = neighbor_count * (neighbor_count - 1) / 2 if neighbor_count > 1 else 1
        brokerage_ratio = 1 - (inter_links / possible_pairs) if possible_pairs else 0.0
        betweenness = round(min(1.0, norm_deg * 1.2 + brokerage_ratio * 0.5 + (n.riskScore / 400)), 2)
        is_bridge = betweenness > 0.4 or deg >= 4
        centralities.append(
            CentralityMetric(
                node_id=n.id,
                node_name=n.name,
                category=n.category.value,
                degree_centrality=norm_deg,
                betweenness_score=betweenness,
                is_bridge_node=is_bridge,
                riskScore=n.riskScore,
            )
        )

    sorted_brokers = sorted(centralities, key=lambda c: c.betweenness_score, reverse=True)
    sorted_impact = sorted(centralities, key=lambda c: c.degree_centrality, reverse=True)
    bridges = [c for c in centralities if c.is_bridge_node]

    gang_networks = get_organization_gang_networks(db)

    return LinkAnalysisResponse(
        graph_density=density,
        total_clusters=len(gang_networks),
        top_broker_nodes=sorted_brokers[:5],
        high_impact_nodes=sorted_impact[:5],
        bridge_nodes=bridges,
    )


def generate_ai_graph_insights(db: Session) -> list[AIGraphInsight]:
    """Derive criminal-network pattern insights from the live graph structure."""
    nodes, edges = _build_sql_graph(db)
    insights: list[AIGraphInsight] = []

    if not nodes:
        return insights

    nodes_by_id = {n.id: n for n in nodes}
    link_analysis = perform_link_analysis(db)
    now_iso = datetime.now().isoformat()

    # Insight 1: highest-betweenness broker node (data-driven, no fabricated names)
    top_broker = link_analysis.top_broker_nodes[0] if link_analysis.top_broker_nodes else None
    if top_broker is not None and top_broker.degree_centrality > 0:
        insights.append(AIGraphInsight(
            id="insight-broker",
            insight_type="broker_identification",
            title=f"Critical Broker Node Detected: {top_broker.node_name}",
            description=(
                f"{top_broker.node_name} exhibits the highest betweenness centrality "
                f"({top_broker.betweenness_score}) across {len(edges)} recorded relationships. "
                f"Removing or monitoring this node would disrupt cross-entity coordination."
            ),
            threat_level="CRITICAL" if top_broker.betweenness_score >= 0.6 else "HIGH",
            target_node_ids=[top_broker.node_id],
            recommendation="Prioritize surveillance and travel-record checks for this hub entity.",
            timestamp=now_iso,
        ))

    # Insight 2: multi-jurisdiction offenders (same person active across districts)
    districts_by_entity: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if edge.relationship == "Operated in area":
            loc = nodes_by_id.get(edge.target)
            actor = nodes_by_id.get(edge.source)
            if loc and actor and loc.district:
                districts_by_entity[edge.source].add(loc.district)
    multi_district = {
        eid: dset for eid, dset in districts_by_entity.items()
        if len(dset) >= 2 and eid in nodes_by_id
    }
    for entity_id, dset in sorted(multi_district.items(), key=lambda kv: -len(kv[1]))[:2]:
        entity = nodes_by_id[entity_id]
        insights.append(AIGraphInsight(
            id=f"insight-crossjur-{entity_id}",
            insight_type="cross_jurisdiction_link",
            title=f"Cross-District Activity Pattern: {entity.name}",
            description=(
                f"{entity.name} appears in incident records spanning {len(dset)} districts "
                f"({', '.join(sorted(dset))}), indicating likely interstate/inter-district operations."
            ),
            threat_level="HIGH" if entity.riskScore >= 70 else "MEDIUM",
            target_node_ids=[entity_id],
            recommendation="Coordinate intelligence sharing between the listed district units.",
            timestamp=now_iso,
        ))

    # Insight 3: densest co-accused cluster (gang-style grouping from shared FIRs)
    co_accused_pairs = [e for e in edges if e.relationship.startswith("Co-accused")]
    pair_counter = Counter()
    for edge in co_accused_pairs:
        pair_counter[frozenset({edge.source, edge.target})] += 1
    if pair_counter:
        strongest_pair = max(pair_counter, key=lambda fs: pair_counter[fs])
        pair_names = [nodes_by_id[nid].name for nid in strongest_pair if nid in nodes_by_id]
        insights.append(AIGraphInsight(
            id="insight-cluster",
            insight_type="syndicate_cluster",
            title="Repeat Co-Accused Cluster Identified",
            description=(
                f"{', '.join(pair_names)} repeatedly appear together in multiple FIRs "
                f"(shared-incident count: {max(pair_counter.values())}), indicating an "
                f"operational cell rather than coincidental association."
            ),
            threat_level="HIGH",
            target_node_ids=list(strongest_pair),
            recommendation="Track the cell's shared locations and check for common handlers.",
            timestamp=now_iso,
        ))

    # Insight 4: bridge-node concentration alert when density is low but bridges exist
    if link_analysis.bridge_nodes and link_analysis.graph_density < 0.2:
        bridge_names = ", ".join(b.node_name for b in link_analysis.bridge_nodes[:3])
        insights.append(AIGraphInsight(
            id="insight-fragility",
            insight_type="high_risk_hub",
            title="Sparse Network With Concentrated Bridge Nodes",
            description=(
                f"Graph density is only {link_analysis.graph_density}, yet bridge nodes exist "
                f"({bridge_names}). The network fragments quickly if these connectors are disrupted."
            ),
            threat_level="MEDIUM",
            target_node_ids=[b.node_id for b in link_analysis.bridge_nodes[:3]],
            recommendation="Focus disruption strategy on identified bridge entities.",
            timestamp=now_iso,
        ))

    return insights
