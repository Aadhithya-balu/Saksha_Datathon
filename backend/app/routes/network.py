"""
FastAPI Router for Graph-Based Criminal Intelligence, Neo4j Graph Queries,
Link Analysis, Gang Networks, Shortest Path Analysis, and AI Graph Insights.
"""

from typing import Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.auth.dependencies import get_current_user
from app.auth.rbac import ALL_ROLES, require_roles
from app.database.postgres import get_db
from app.models.network import (
    AIGraphInsight,
    GangNetworkSummary,
    LinkAnalysisResponse,
    NetworkGraphResponse,
    ShortestPathRequest,
    ShortestPathResponse,
)
from app.services.neo4j.client import sync_postgres_to_neo4j, is_neo4j_available
from app.services.network import network_service

router = APIRouter(prefix="/network", tags=["Network Graph Intelligence"], dependencies=[Depends(require_roles(*ALL_ROLES))])


@router.get("/graph", response_model=NetworkGraphResponse)
def get_full_graph(
    category_filter: str | None = Query(None),
    min_risk: float = Query(0.0, ge=0.0, le=100.0),
    provenance_filter: str | None = Query(None),
    exclude_demo: bool = Query(False),
    limit: int = Query(500, ge=1, le=2000, description="Max nodes returned. Large values may be slow."),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Retrieve full criminal relationship network graph."""
    return network_service.get_full_network_graph(
        db,
        category_filter=category_filter,
        min_risk=min_risk,
        provenance_filter=provenance_filter,
        exclude_demo=exclude_demo,
        limit=limit,
    )


@router.get("/person/{person_id}", response_model=NetworkGraphResponse)
def get_person_network(
    person_id: str,
    depth: int = Query(1, ge=1, le=4, description="Graph traversal depth expansion"),
    provenance_filter: str | None = Query(None, description="Filter edges by provenance or verification status"),
    exclude_demo: bool = Query(False, description="Exclude demo/seed records"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Retrieve relationship graph centered around a specific criminal, suspect, officer, or victim."""
    return network_service.get_person_network_graph(
        db,
        person_id=person_id,
        depth=depth,
        provenance_filter=provenance_filter,
        exclude_demo=exclude_demo,
    )


@router.get("/search")
def search_network_entities(
    q: str = Query(..., min_length=1, max_length=200, description="Search term (name, FIR number, case number, station, district)"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Search for criminals, victims, officers, FIRs, and cases by name/number/station/district."""
    from app.models.criminal import Criminal
    from app.models.victim import Victim
    from app.models.officer import Officer
    from app.models.fir import FIR
    from app.models.crime import CrimeCase
    from app.models.location import Location

    pattern = f"%{q}%"
    results: list[dict[str, Any]] = []

    criminals = db.query(Criminal).filter(
        or_(Criminal.full_name.ilike(pattern), Criminal.aliases.ilike(pattern))
    ).limit(limit).all()
    for c in criminals:
        results.append({
            "id": f"criminal-{c.id}",
            "type": "criminal",
            "name": c.full_name,
            "detail": f"Status: {c.status or 'unknown'} | Cases: {len(c.fir_links)}",
            "status": c.status,
            "risk_score": min(100.0, 45.0 + len(c.fir_links) * 10),
        })

    victims = db.query(Victim).filter(Victim.full_name.ilike(pattern)).limit(limit).all()
    for v in victims:
        results.append({
            "id": f"victim-{v.id}",
            "type": "victim",
            "name": v.full_name,
            "detail": f"Contact: {v.contact_number or 'N/A'}",
            "status": "victim",
        })

    officers = db.query(Officer).filter(
        or_(Officer.name.ilike(pattern), Officer.badge_number.ilike(pattern))
    ).limit(limit).all()
    for o in officers:
        results.append({
            "id": f"officer-{o.id}",
            "type": "officer",
            "name": o.name,
            "detail": f"Badge: {o.badge_number} | Rank: {o.rank or 'N/A'} | Station: {o.station or 'N/A'}",
            "status": o.status,
        })

    firs = db.query(FIR).filter(
        or_(FIR.fir_number.ilike(pattern), FIR.complainant_name.ilike(pattern))
    ).limit(limit).all()
    for f in firs:
        results.append({
            "id": f"case-{f.id}",
            "type": "case",
            "name": f"FIR #{f.fir_number}",
            "detail": f"Complainant: {f.complainant_name} | Sections: {f.sections or 'N/A'}",
            "status": "filed",
        })

    cases = db.query(CrimeCase).filter(
        or_(CrimeCase.case_number.ilike(pattern), CrimeCase.description.ilike(pattern))
    ).limit(limit).all()
    for c in cases:
        results.append({
            "id": f"case-{c.id}",
            "type": "case",
            "name": f"Case {c.case_number}",
            "detail": f"Status: {c.status or 'open'} | Priority: {c.priority or 'N/A'}",
            "status": c.status,
        })

    locations = db.query(Location).filter(
        or_(Location.station.ilike(pattern), Location.district.ilike(pattern))
    ).limit(limit).all()
    for loc in locations:
        results.append({
            "id": f"location-{loc.id}",
            "type": "location",
            "name": f"{loc.station}, {loc.district}",
            "detail": f"District: {loc.district} | Lat: {loc.latitude}, Lon: {loc.longitude}",
            "status": "active",
        })

    results.sort(key=lambda x: 0 if q.lower() in x["name"].lower() else 1)
    return {"results": results[:limit], "query": q, "total": len(results[:limit])}


@router.get("/case/{case_id}", response_model=NetworkGraphResponse)
def get_case_network(
    case_id: str,
    provenance_filter: str | None = Query(None, description="Filter edges by provenance or verification status"),
    exclude_demo: bool = Query(False, description="Exclude demo/seed records"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Retrieve relationship network associated with a specific crime case or FIR."""
    return network_service.get_case_network_graph(
        db,
        case_id=case_id,
        provenance_filter=provenance_filter,
        exclude_demo=exclude_demo,
    )


@router.get("/gangs", response_model=list[GangNetworkSummary])
def list_gang_networks(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """List active criminal gangs, syndicates, hierarchy structures, and member networks."""
    return network_service.get_organization_gang_networks(db)


@router.get("/gangs/{gang_id}", response_model=GangNetworkSummary)
def get_gang_network_detail(
    gang_id: str,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Retrieve details and hierarchy tree for a specific criminal gang syndicate."""
    gangs = network_service.get_organization_gang_networks(db)
    for g in gangs:
        if g.gang_id == gang_id:
            return g
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Gang syndicate '{gang_id}' not found")


@router.post("/shortest-path", response_model=ShortestPathResponse)
def calculate_shortest_path(
    req: ShortestPathRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Calculate shortest relationship path and degree separation between two entities in the graph."""
    return network_service.find_shortest_path(db, source_id=req.source_id, target_id=req.target_id, max_depth=req.max_depth)


@router.post("/link-analysis", response_model=LinkAnalysisResponse)
def perform_graph_link_analysis(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Perform network centrality calculations, identify key broker nodes, and bridge connections."""
    return network_service.perform_link_analysis(db)


@router.get("/insights", response_model=list[AIGraphInsight])
def get_ai_graph_insights(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Generate AI graph intelligence threat alerts, broker node detection, and investigation recommendations."""
    return network_service.generate_ai_graph_insights(db)


@router.post("/sync-neo4j", dependencies=[Depends(require_roles("admin", "crime_analyst"))])
def sync_neo4j_database(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Trigger synchronization of PostgreSQL database records into Neo4j graph nodes & edges."""
    if not is_neo4j_available():
        return {
            "status": "warning",
            "message": "Neo4j database is currently unreachable. Operating under PostgreSQL fallback mode.",
            "neo4j_active": False,
        }
    res = sync_postgres_to_neo4j(db)
    return {
        "status": "success",
        "message": f"Successfully synced {res.get('synced_nodes', 0)} nodes and {res.get('synced_edges', 0)} edges to Neo4j.",
        "neo4j_active": True,
        "details": res,
    }
