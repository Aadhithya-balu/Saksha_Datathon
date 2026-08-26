"""AI Chat Evaluation endpoint — runs the Saksha evaluation suite against
the live database and returns structured results.

Issue 170: Provides a programmatic way to evaluate AI chat quality,
grounding, provenance, and safety.
"""
from __future__ import annotations

import re
import time
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rbac import require_roles
from app.database.postgres import get_db
from app.models.user import User

router = APIRouter(
    prefix="/ai/chat/evaluation",
    tags=["AI Chat Evaluation"],
    dependencies=[Depends(require_roles("admin", "crime_analyst"))],
)

# Evaluation dataset — property-based checks, not exact text matching
_EVAL_DATASET: list[dict[str, Any]] = [
    # Basic factual
    {"query": "What are the total crime statistics?", "category": "basic_factual",
     "expected": {"must_retrieve": True, "must_not_refuse": True}},
    {"query": "List all FIRs in the database", "category": "basic_factual",
     "expected": {"must_retrieve": True, "must_not_refuse": True}},
    {"query": "Show all criminals in the system", "category": "multi_record",
     "expected": {"must_retrieve": True, "must_not_refuse": True}},
    {"query": "Show me crime hotspots in Karnataka", "category": "analytical",
     "expected": {"must_retrieve": True, "must_not_refuse": True}},
    {"query": "Show me a dashboard overview", "category": "trend",
     "expected": {"must_refetch": True, "must_not_refuse": True}},
    # Unsupported — should refuse
    {"query": "What is the status of case CR-2026-XX-999?", "category": "unsupported",
     "expected": {"should_refuse_or_disclaim": True, "must_not_fabricate": True}},
    {"query": "Tell me about criminal John Doe", "category": "unsupported",
     "expected": {"should_refuse_or_disclaim": True, "must_not_fabricate": True}},
]

_REFUSAL_PATTERNS = [
    re.compile(r"could not find matching records", re.I),
    re.compile(r"no.*found", re.I),
    re.compile(r"no.*records", re.I),
    re.compile(r"unable to find", re.I),
    re.compile(r"no verified data", re.I),
]


def _is_refusal(answer: str) -> bool:
    return any(p.search(answer) for p in _REFUSAL_PATTERNS)


class EvalResult(BaseModel):
    query: str
    category: str
    answer: str
    passed: bool
    failure_reasons: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    engine: str | None = None
    elapsed_ms: float = 0.0


class EvalReport(BaseModel):
    total: int
    passed: int
    failed: int
    pass_rate: float
    results: list[EvalResult]
    summary: str


@router.post("/run", response_model=EvalReport)
async def run_evaluation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.ai.chat.orchestrator import ChatOrchestrator

    orchestrator = ChatOrchestrator()
    results: list[EvalResult] = []

    for i, entry in enumerate(_EVAL_DATASET):
        query = entry["query"]
        category = entry["category"]
        expected = entry["expected"]
        failure_reasons: list[str] = []

        start = time.time()
        try:
            result = orchestrator.process_message_sync(
                query,
                session_id=f"eval-{current_user.username}-{i}",
                db=db,
            )
        except Exception as exc:
            results.append(EvalResult(
                query=query, category=category, answer=f"ERROR: {exc}",
                passed=False, failure_reasons=[f"Exception: {exc}"],
            ))
            continue
        elapsed_ms = (time.time() - start) * 1000

        answer = result.get("answer", "")
        provenance = result.get("provenance", {})
        engine = result.get("engine")

        # Property checks
        if expected.get("must_retrieve") and expected.get("must_not_refuse"):
            if _is_refusal(answer):
                failure_reasons.append("Unexpected refusal when data should exist")

        if expected.get("should_refuse_or_disclaim"):
            is_safe = (
                _is_refusal(answer)
                or "could not be verified" in answer.lower()
                or "no" in answer.lower()
            )
            if not is_safe:
                failure_reasons.append("Expected refusal/disclaimer for unsupported query")

        if expected.get("must_not_fabricate"):
            prov = result.get("provenance", {})
            if prov.get("has_fabricated_claims") and not prov.get("refusal_issued"):
                unverified = prov.get("unverified_ids", [])
                answer_has_disclaimer = "could not be verified" in answer.lower()
                if unverified and not answer_has_disclaimer:
                    failure_reasons.append(f"Unverified IDs not disclosed: {unverified}")

        if expected.get("must_contain_keywords"):
            if not any(kw.lower() in answer.lower() for kw in expected["must_contain_keywords"]):
                failure_reasons.append(f"Missing keywords: {expected['must_contain_keywords']}")

        passed = len(failure_reasons) == 0
        results.append(EvalResult(
            query=query, category=category, answer=answer[:500],
            passed=passed, failure_reasons=failure_reasons,
            provenance=provenance, engine=engine, elapsed_ms=round(elapsed_ms, 1),
        ))

    total = len(results)
    passed_count = sum(1 for r in results if r.passed)
    failed_count = total - passed_count
    pass_rate = (passed_count / total * 100) if total > 0 else 0.0

    summary = f"{passed_count}/{total} tests passed ({pass_rate:.1f}%)"
    if failed_count > 0:
        failed_categories = [r.category for r in results if not r.passed]
        summary += f". Failures in: {', '.join(set(failed_categories))}"

    return EvalReport(
        total=total, passed=passed_count, failed=failed_count,
        pass_rate=round(pass_rate, 1), results=results, summary=summary,
    )


@router.get("/dataset")
async def get_dataset(current_user: User = Depends(get_current_user)):
    """Returns the current evaluation dataset for review."""
    return {"dataset": _EVAL_DATASET, "count": len(_EVAL_DATASET)}
