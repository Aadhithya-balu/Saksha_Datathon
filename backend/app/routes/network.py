"""
FastAPI Router for Graph-Based Criminal Intelligence, Neo4j Graph Queries,
Link Analysis, Gang Networks, Shortest Path Analysis, and AI Graph Insights.
"""

from typing import Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
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

router = APIRouter(prefix="/network", tags=["Network Graph Intelligence"])


@router.get("/graph", response_model=NetworkGraphResponse)
def get_full_graph(
    category_filter: str | None = Query(None, description="Filter nodes by category: suspect, offender, location, victim, case, gang"),
    min_risk: float = Query(0.0, ge=0.0, le=100.0, description="Minimum risk score threshold"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Retrieve full criminal relationship network graph with category and risk score filters."""
    return network_service.get_full_network_graph(db, category_filter=category_filter, min_risk=min_risk)


@router.get("/person/{person_id}", response_model=NetworkGraphResponse)
def get_person_network(
    person_id: str,
    depth: int = Query(1, ge=1, le=4, description="Graph traversal depth expansion"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Retrieve relationship graph centered around a specific criminal, suspect, officer, or victim."""
    return network_service.get_person_network_graph(db, person_id=person_id, depth=depth)


@router.get("/case/{case_id}", response_model=NetworkGraphResponse)
def get_case_network(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Retrieve relationship network associated with a specific crime case or FIR."""
    return network_service.get_case_network_graph(db, case_id=case_id)


@router.get("/gangs", response_model=list[GangNetworkSummary])
def list_gang_networks(
    current_user: Any = Depends(get_current_user),
):
    """List active criminal gangs, syndicates, hierarchy structures, and member networks."""
    return network_service.get_organization_gang_networks()


@router.get("/gangs/{gang_id}", response_model=GangNetworkSummary)
def get_gang_network_detail(
    gang_id: str,
    current_user: Any = Depends(get_current_user),
):
    """Retrieve details and hierarchy tree for a specific criminal gang syndicate."""
    gangs = network_service.get_organization_gang_networks()
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


@router.post("/sync-neo4j")
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
