"""Backend fetcher — executes query plans against PostgreSQL, Neo4j, and ML services."""
from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.ai.chat.query_planner import BackendCall, QueryPlan


@dataclass
class BackendResult:
    source: str
    data_type: str
    content: str
    raw_data: Any = None
    success: bool = True
    error: str | None = None


class BackendFetcher:
    """Executes query plans by calling existing backend services directly."""

    def execute(self, plan: QueryPlan, db: Session) -> list[BackendResult]:
        if plan.parallel and len(plan.backend_calls) > 1:
            return self._execute_parallel(plan, db)
        return self._execute_sequential(plan, db)

    def _execute_parallel(self, plan: QueryPlan, db: Session) -> list[BackendResult]:
        results: list[BackendResult] = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(self._execute_call, call, db): call
                for call in plan.backend_calls
            }
            for future in as_completed(futures):
                call = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    results.append(BackendResult(
                        source=call.service,
                        data_type=call.method,
                        content="",
                        success=False,
                        error=str(exc),
                    ))
        return results

    def _execute_sequential(self, plan: QueryPlan, db: Session) -> list[BackendResult]:
        results: list[BackendResult] = []
        for call in plan.backend_calls:
            results.append(self._execute_call(call, db))
        return results

    def _execute_call(self, call: BackendCall, db: Session) -> BackendResult:
        try:
            if call.service == "postgres":
                return self._exec_postgres(call, db)
            if call.service == "neo4j":
                return self._exec_neo4j(call, db)
            if call.service == "ml":
                return self._exec_ml(call)
            if call.service == "analytics":
                return self._exec_analytics(call, db)
            return BackendResult(
                source=call.service, data_type=call.method,
                content="Unknown service", success=False,
            )
        except Exception as exc:
            tb = traceback.format_exc()
            return BackendResult(
                source=call.service, data_type=call.method,
                content="", success=False, error=f"{exc}\n{tb}",
            )

    def _exec_postgres(self, call: BackendCall, db: Session) -> BackendResult:
        method = call.method
        params = call.params

        if method == "get_fir":
            return self._pg_get_fir(db, params)
        if method == "search_firs":
            return self._pg_search_firs(db, params)
        if method == "list_firs":
            return self._pg_list_firs(db, params)
        if method == "get_case":
            return self._pg_get_case(db, params)
        if method == "search_cases":
            return self._pg_search_cases(db, params)
        if method == "list_cases":
            return self._pg_list_cases(db, params)
        if method == "get_criminal":
            return self._pg_get_criminal(db, params)
        if method == "get_officer":
            return self._pg_get_officer(db, params)
        if method == "list_officers":
            return self._pg_list_officers(db, params)
        if method == "list_notifications":
            return self._pg_list_notifications(db, params)
        if method == "get_victims":
            return self._pg_get_victims(db, params)
        return BackendResult(source="postgres", data_type=method, content="Method not implemented")

    def _pg_get_fir(self, db: Session, params: dict) -> BackendResult:
        from app.models.fir import FIR
        fir_num = params.get("fir_number", "")
        fir = db.query(FIR).filter(FIR.fir_number.ilike(f"%{fir_num}%")).first()
        if not fir:
            return BackendResult(source="postgres", data_type="fir", content="No FIR found.", raw_data=None)
        content = self._format_fir(fir)
        return BackendResult(source="postgres", data_type="fir", content=content, raw_data={"fir_number": fir.fir_number, "id": str(fir.id)})

    def _pg_search_firs(self, db: Session, params: dict) -> BackendResult:
        from app.models.fir import FIR
        query = params.get("query", "")
        firs = db.query(FIR).filter(
            FIR.fir_number.ilike(f"%{query}%")
            | FIR.complainant_name.ilike(f"%{query}%")
            | FIR.narrative.ilike(f"%{query}%")
        ).limit(10).all()
        if not firs:
            return BackendResult(source="postgres", data_type="firs", content="No FIRs match the search.")
        parts = [self._format_fir(f) for f in firs]
        return BackendResult(
            source="postgres", data_type="firs",
            content="\n---\n".join(parts),
            raw_data=[{"fir_number": f.fir_number, "id": str(f.id)} for f in firs],
        )

    def _pg_list_firs(self, db: Session, params: dict) -> BackendResult:
        from app.models.fir import FIR
        limit = params.get("limit", 20)
        firs = db.query(FIR).order_by(FIR.filed_at.desc()).limit(limit).all()
        if not firs:
            return BackendResult(source="postgres", data_type="firs", content="No FIRs in the database.")
        parts = [self._format_fir(f) for f in firs]
        return BackendResult(
            source="postgres", data_type="firs",
            content="\n---\n".join(parts),
            raw_data=[{"fir_number": f.fir_number, "id": str(f.id)} for f in firs],
        )

    def _pg_get_case(self, db: Session, params: dict) -> BackendResult:
        from app.models.crime import CrimeCase
        case_num = params.get("case_number", "")
        case = db.query(CrimeCase).filter(CrimeCase.case_number.ilike(f"%{case_num}%")).first()
        if not case:
            return BackendResult(source="postgres", data_type="case", content="No case found.")
        content = self._format_case(case)
        return BackendResult(source="postgres", data_type="case", content=content, raw_data={"case_number": case.case_number, "id": str(case.id)})

    def _pg_search_cases(self, db: Session, params: dict) -> BackendResult:
        from app.models.crime import CrimeCase
        query_text = params.get("query", "")
        category = params.get("category", "")
        q = db.query(CrimeCase)
        if query_text:
            q = q.filter(
                CrimeCase.case_number.ilike(f"%{query_text}%")
                | CrimeCase.description.ilike(f"%{query_text}%")
                | CrimeCase.mo_tags.ilike(f"%{query_text}%")
            )
        if category:
            q = q.join(CrimeCase.category).filter(
                CrimeCase.category.has(name=category) if hasattr(CrimeCase.category, 'has')
                else CrimeCase.description.ilike(f"%{category}%")
            )
        cases = q.limit(10).all()
        if not cases:
            return BackendResult(source="postgres", data_type="cases", content="No matching cases found.")
        parts = [self._format_case(c) for c in cases]
        return BackendResult(
            source="postgres", data_type="cases",
            content="\n---\n".join(parts),
            raw_data=[{"case_number": c.case_number, "id": str(c.id)} for c in cases],
        )

    def _pg_list_cases(self, db: Session, params: dict) -> BackendResult:
        from app.models.crime import CrimeCase
        limit = params.get("limit", 20)
        cases = db.query(CrimeCase).order_by(CrimeCase.reported_at.desc()).limit(limit).all()
        if not cases:
            return BackendResult(source="postgres", data_type="cases", content="No cases in database.")
        parts = [self._format_case(c) for c in cases]
        return BackendResult(
            source="postgres", data_type="cases",
            content="\n---\n".join(parts),
            raw_data=[{"case_number": c.case_number, "id": str(c.id)} for c in cases],
        )

    def _pg_get_criminal(self, db: Session, params: dict) -> BackendResult:
        from app.models.criminal import Criminal
        name = params.get("name", "")
        criminals = db.query(Criminal).filter(Criminal.full_name.ilike(f"%{name}%")).all()
        if not criminals:
            criminals = db.query(Criminal).filter(Criminal.aliases.ilike(f"%{name}%")).all()
        if not criminals:
            return BackendResult(source="postgres", data_type="criminal", content="No criminal record found.")
        parts = [self._format_criminal(c) for c in criminals]
        return BackendResult(
            source="postgres", data_type="criminal",
            content="\n---\n".join(parts),
            raw_data=[{"name": c.full_name, "id": str(c.id), "status": c.status} for c in criminals],
        )

    def _pg_get_officer(self, db: Session, params: dict) -> BackendResult:
        from app.models.officer import Officer
        name = params.get("name", "")
        officer = db.query(Officer).filter(
            Officer.name.ilike(f"%{name}%") | Officer.badge_number.ilike(f"%{name}%")
        ).first()
        if not officer:
            return BackendResult(source="postgres", data_type="officer", content="No officer found.")
        content = (
            f"Officer: {officer.name}, Badge: {officer.badge_number}, "
            f"Rank: {officer.rank or 'N/A'}, Station: {officer.station}, "
            f"District: {officer.district or 'N/A'}, Status: {officer.status}"
        )
        return BackendResult(source="postgres", data_type="officer", content=content, raw_data={"name": officer.name, "badge": officer.badge_number})

    def _pg_list_officers(self, db: Session, params: dict) -> BackendResult:
        from app.models.officer import Officer
        limit = params.get("limit", 20)
        officers = db.query(Officer).limit(limit).all()
        if not officers:
            return BackendResult(source="postgres", data_type="officers", content="No officers found.")
        parts = [
            f"{o.name} (Badge: {o.badge_number}, Rank: {o.rank or 'N/A'}, Station: {o.station})"
            for o in officers
        ]
        return BackendResult(source="postgres", data_type="officers", content="\n".join(parts))

    def _pg_list_notifications(self, db: Session, params: dict) -> BackendResult:
        from app.models.notification import Notification
        limit = params.get("limit", 20)
        notifs = db.query(Notification).order_by(Notification.created_at.desc()).limit(limit).all()
        if not notifs:
            return BackendResult(source="postgres", data_type="notifications", content="No notifications.")
        parts = [f"[{n.severity.upper()}] {n.title}: {n.message}" for n in notifs]
        return BackendResult(source="postgres", data_type="notifications", content="\n".join(parts))

    def _pg_get_victims(self, db: Session, params: dict) -> BackendResult:
        from app.models.victim import Victim
        name = params.get("name", "")
        victims = db.query(Victim).filter(Victim.full_name.ilike(f"%{name}%")).all()
        if not victims:
            return BackendResult(source="postgres", data_type="victims", content="No victims found.")
        parts = [f"Victim: {v.full_name}, Age: {v.age or 'N/A'}, Gender: {v.gender or 'N/A'}" for v in victims]
        return BackendResult(source="postgres", data_type="victims", content="\n".join(parts))

    def _exec_neo4j(self, call: BackendCall, db: Session) -> BackendResult:
        method = call.method
        params = call.params
        try:
            from app.services.neo4j.client import is_neo4j_available
            if not is_neo4j_available():
                return self._neo4j_sql_fallback(method, params, db)
        except Exception:
            return self._neo4j_sql_fallback(method, params, db)

        if method == "get_person_network":
            return self._neo4j_person_network(params, db)
        if method == "get_full_network":
            return self._neo4j_full_network(db)
        if method == "get_gangs":
            return self._neo4j_gangs()
        if method == "shortest_path":
            return self._neo4j_shortest_path(params, db)
        return BackendResult(source="neo4j", data_type=method, content="Method not implemented")

    def _neo4j_person_network(self, params: dict, db: Session) -> BackendResult:
        from app.services.network.network_service import get_person_network_graph
        name = params.get("name", "")
        graph = get_person_network_graph(db, person_id=name, depth=2)
        if not graph.nodes:
            return BackendResult(source="neo4j", data_type="network", content="No network data found.")
        parts = []
        for node in graph.nodes[:15]:
            parts.append(f"Node: {node.name} (Type: {node.category.value}, Risk: {node.riskScore})")
        for edge in graph.edges[:15]:
            parts.append(f"Link: {edge.source} --[{edge.relationship}]--> {edge.target}")
        return BackendResult(
            source="neo4j", data_type="network",
            content="\n".join(parts),
            raw_data={"nodes": len(graph.nodes), "edges": len(graph.edges)},
        )

    def _neo4j_full_network(self, db: Session) -> BackendResult:
        from app.services.network.network_service import get_full_network_graph
        graph = get_full_network_graph(db)
        parts = [f"Network: {graph.total_nodes} nodes, {graph.total_edges} edges"]
        for node in graph.nodes[:20]:
            parts.append(f"  {node.name} ({node.category.value}, risk={node.riskScore})")
        return BackendResult(source="neo4j", data_type="network", content="\n".join(parts))

    def _neo4j_gangs(self) -> BackendResult:
        from app.services.network.network_service import get_organization_gang_networks
        gangs = get_organization_gang_networks()
        parts = []
        for g in gangs:
            members = ", ".join(m.name for m in g.members)
            parts.append(
                f"Gang: {g.name} (Leader: {g.leader_name}, Risk: {g.risk_level}, "
                f"Territory: {g.territory}, Members: {members})"
            )
        return BackendResult(source="neo4j", data_type="gangs", content="\n".join(parts))

    def _neo4j_shortest_path(self, params: dict, db: Session) -> BackendResult:
        from app.services.network.network_service import find_shortest_path
        source = params.get("source", "")
        target = params.get("target", "")
        result = find_shortest_path(db, source, target)
        if not result.found:
            return BackendResult(source="neo4j", data_type="shortest_path", content=result.explanation)
        path_names = " -> ".join(n.name for n in result.path_nodes)
        return BackendResult(
            source="neo4j", data_type="shortest_path",
            content=f"Path ({result.distance} hops): {path_names}",
        )

    def _neo4j_sql_fallback(self, method: str, params: dict, db: Session) -> BackendResult:
        if method == "get_person_network":
            from app.services.analytics_service import network_person
            name = params.get("name", "")
            result = network_person(db, person_name=name)
            if not result:
                return BackendResult(source="postgres", data_type="network_fallback", content="No network data.")
            parts = [f"{r.get('source_name', '')} --[{r.get('relationship', '')}]--> {r.get('target_name', '')}" for r in result[:20]]
            return BackendResult(source="postgres", data_type="network_fallback", content="\n".join(parts))
        if method == "get_full_network":
            from app.services.network.network_service import get_full_network_graph
            graph = get_full_network_graph(db)
            return BackendResult(
                source="postgres", data_type="network_fallback",
                content=f"Network (SQL fallback): {graph.total_nodes} nodes, {graph.total_edges} edges",
            )
        if method == "get_gangs":
            return self._neo4j_gangs()
        return BackendResult(source="neo4j", data_type=method, content="Neo4j unavailable, no SQL fallback.")

    def _exec_ml(self, call: BackendCall) -> BackendResult:
        method = call.method
        params = call.params

        if method == "risk_predict":
            return self._ml_risk_predict(params)
        if method == "forecast":
            return self._ml_forecast(params)
        if method == "hotspot_predict":
            return self._ml_hotspot_predict(params)
        if method == "find_similar_offenders":
            return self._ml_similar(params)
        if method == "criminal_risk":
            return self._ml_criminal_risk(params)
        return BackendResult(source="ml", data_type=method, content="ML method not implemented")

    def _ml_risk_predict(self, params: dict) -> BackendResult:
        from app.ai.inference.risk import predict_risk
        district = params.get("district", "Bengaluru Urban")
        result = predict_risk([{"district": district, "crime_count": 10, "open_cases": 5}])
        if not result:
            return BackendResult(source="ml", data_type="risk", content="No prediction available.")
        r = result[0] if isinstance(result, list) else result
        risk_score = r.get("risk_score", 0) if isinstance(r, dict) else getattr(r, "risk_score", 0)
        risk_band = r.get("risk_band", "UNKNOWN") if isinstance(r, dict) else getattr(r, "risk_band", "UNKNOWN")
        return BackendResult(
            source="ml", data_type="risk",
            content=f"District {district}: Risk Score {risk_score}/100 ({risk_band})",
            raw_data=r if isinstance(r, dict) else {"risk_score": risk_score, "risk_band": risk_band},
        )

    def _ml_forecast(self, params: dict) -> BackendResult:
        from app.ai.inference.risk import predict_forecast
        district = params.get("district", "Bengaluru Urban")
        months = params.get("months", 6)
        result = predict_forecast(district, months)
        if not result:
            return BackendResult(source="ml", data_type="forecast", content="No forecast available.")
        if isinstance(result, list):
            parts = [f"Month {f.get('month', i+1)}: Predicted {f.get('predicted_count', 'N/A')} crimes" for i, f in enumerate(result[:months])]
        else:
            parts = [f"Forecast for {district}: {result}"]
        return BackendResult(source="ml", data_type="forecast", content="\n".join(parts), raw_data=result)

    def _ml_hotspot_predict(self, params: dict) -> BackendResult:
        from app.ai.inference.hotspot import predict as hotspot_predict
        district = params.get("district", "")
        result = hotspot_predict([{"district": district, "lat": 12.97, "lon": 77.59, "hour": 14, "day_of_week": 2}])
        if not result:
            return BackendResult(source="ml", data_type="hotspot", content="No hotspot prediction available.")
        return BackendResult(source="ml", data_type="hotspot", content=str(result), raw_data=result)

    def _ml_similar(self, params: dict) -> BackendResult:
        from app.ai.inference.criminal import find_similar_offenders
        name = params.get("name", "")
        result = find_similar_offenders(name)
        if not result:
            return BackendResult(source="ml", data_type="similar", content="No similar offenders found.")
        if isinstance(result, list):
            parts = [f"Similar: {s.get('name', 'N/A')} (similarity: {s.get('score', 'N/A')})" for s in result[:5]]
        else:
            parts = [str(result)]
        return BackendResult(source="ml", data_type="similar", content="\n".join(parts))

    def _ml_criminal_risk(self, params: dict) -> BackendResult:
        from app.ai.inference.criminal import score_criminal_risk
        criminal_id = params.get("criminal_id", "")
        result = score_criminal_risk(criminal_id)
        if not result:
            return BackendResult(source="ml", data_type="criminal_risk", content="No risk score available.")
        return BackendResult(source="ml", data_type="criminal_risk", content=str(result), raw_data=result)

    def _exec_analytics(self, call: BackendCall, db: Session) -> BackendResult:
        method = call.method
        try:
            from app.services.analytics_service import (
                dashboard_summary, category_breakdown, district_comparison,
                hotspots, anomalies, offender_dossiers,
            )
            if method == "dashboard_summary":
                s = dashboard_summary(db)
                content = (
                    f"Total crimes: {s.get('total_crimes', 0)}. "
                    f"Open cases: {s.get('open_crimes', 0)}. "
                    f"Total FIRs: {s.get('total_firs', 0)}. "
                    f"Resolution rate: {s.get('resolution_rate_percent', 0)}%."
                )
                return BackendResult(source="analytics", data_type="summary", content=content, raw_data=s)

            if method == "category_breakdown":
                cats = category_breakdown(db)
                parts = [f"{c['category']}: {c['count']} cases" for c in cats[:10]]
                return BackendResult(source="analytics", data_type="categories", content=". ".join(parts) or "No data.", raw_data=cats)

            if method == "district_comparison":
                districts = district_comparison(db)
                parts = [f"{d['district']}: {d['count']} cases" for d in districts[:10]]
                return BackendResult(source="analytics", data_type="districts", content=". ".join(parts) or "No data.", raw_data=districts)

            if method == "hotspots":
                h = hotspots(db)
                hotspot_list = h.get("hotspots", []) if isinstance(h, dict) else (h if isinstance(h, list) else [])
                if not hotspot_list:
                    return BackendResult(source="analytics", data_type="hotspots", content="No hotspot data.")
                parts = [f"{hs.get('name', 'Unknown')} ({hs.get('district_id', 'N/A')}): score={hs.get('score', 0)}" for hs in hotspot_list[:10]]
                return BackendResult(source="analytics", data_type="hotspots", content="\n".join(parts), raw_data=hotspot_list)

            if method == "anomalies":
                a = anomalies(db)
                if not a:
                    return BackendResult(source="analytics", data_type="anomalies", content="No anomalies detected.")
                parts = [f"Anomaly: {an.get('title', 'Unknown')} (severity: {an.get('severity', 'N/A')})" for an in a[:10]]
                return BackendResult(source="analytics", data_type="anomalies", content="\n".join(parts), raw_data=a)

            if method == "offender_dossiers":
                d = offender_dossiers(db)
                if not d:
                    return BackendResult(source="analytics", data_type="dossiers", content="No offender data.")
                parts = [
                    f"{o.get('full_name', 'N/A')}: Status={o.get('status', 'N/A')}, "
                    f"Classification={o.get('classification', 'N/A')}, Risk={o.get('risk_score', 'N/A')}"
                    for o in d[:10]
                ]
                return BackendResult(source="analytics", data_type="dossiers", content="\n".join(parts), raw_data=d)

            return BackendResult(source="analytics", data_type=method, content="Analytics method not found.")
        except Exception as exc:
            return BackendResult(source="analytics", data_type=method, content="", success=False, error=str(exc))

    @staticmethod
    def _format_fir(fir: Any) -> str:
        parts = [
            f"FIR Number: {fir.fir_number}",
            f"Complainant: {fir.complainant_name}",
            f"Status: {fir.status}",
            f"Sections: {fir.sections or 'N/A'}",
            f"Filed: {fir.filed_at.strftime('%Y-%m-%d %H:%M') if fir.filed_at else 'N/A'}",
        ]
        if fir.narrative:
            narrative = fir.narrative[:300] + ("..." if len(fir.narrative or "") > 300 else "")
            parts.append(f"Narrative: {narrative}")
        if hasattr(fir, "criminal_links") and fir.criminal_links:
            names = [link.criminal.full_name for link in fir.criminal_links if link.criminal]
            if names:
                parts.append(f"Accused/Suspects: {', '.join(names)}")
        return " | ".join(parts)

    @staticmethod
    def _format_case(case: Any) -> str:
        parts = [
            f"Case: {case.case_number}",
            f"Status: {case.status}",
            f"Priority: {case.priority or 'medium'}",
            f"Progress: {case.progress or 0}%",
        ]
        if case.description:
            desc = case.description[:300] + ("..." if len(case.description or "") > 300 else "")
            parts.append(f"Description: {desc}")
        if case.mo_tags:
            parts.append(f"MO Tags: {case.mo_tags}")
        if hasattr(case, "category") and case.category:
            parts.append(f"Category: {case.category.name}")
        if hasattr(case, "location") and case.location:
            loc = case.location
            loc_str = loc.name if hasattr(loc, "name") else str(loc)
            district = getattr(loc, "district", "")
            if district:
                loc_str += f", {district}"
            parts.append(f"Location: {loc_str}")
        if case.occurred_at:
            parts.append(f"Occurred: {case.occurred_at.strftime('%Y-%m-%d %H:%M') if case.occurred_at else 'N/A'}")
        if case.reported_at:
            parts.append(f"Reported: {case.reported_at.strftime('%Y-%m-%d %H:%M') if case.reported_at else 'N/A'}")
        if hasattr(case, "firs") and case.firs:
            fir_nums = [f.fir_number for f in case.firs]
            parts.append(f"Linked FIRs: {', '.join(fir_nums)}")
        if hasattr(case, "assigned_officer") and case.assigned_officer:
            parts.append(f"Assigned Officer: {case.assigned_officer.name} ({case.assigned_officer.badge_number})")
        return " | ".join(parts)

    @staticmethod
    def _format_criminal(c: Any) -> str:
        parts = [
            f"Name: {c.full_name}",
            f"Status: {c.status}",
        ]
        if c.aliases:
            parts.append(f"Aliases: {c.aliases}")
        if c.gender:
            parts.append(f"Gender: {c.gender}")
        if c.address:
            parts.append(f"Address: {c.address}")
        if c.mo_summary:
            mo = c.mo_summary[:200] + ("..." if len(c.mo_summary or "") > 200 else "")
            parts.append(f"MO: {mo}")
        if c.identifying_marks:
            parts.append(f"Marks: {c.identifying_marks}")
        return " | ".join(parts)
