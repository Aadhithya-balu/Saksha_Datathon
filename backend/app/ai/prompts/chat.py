from __future__ import annotations

from typing import Iterable


def build_summary_prompt(question: str, evidence: Iterable[str]) -> str:
    evidence_lines = [f"- {item}" for item in evidence]
    evidence_block = "\n".join(evidence_lines) if evidence_lines else "- No supporting records found."
    return (
        "Summarize the investigation context using the retrieved records.\n"
        f"Query: {question}\n"
        f"Evidence:\n{evidence_block}"
    )


def build_answer_prompt(question: str, summary: str, evidence: Iterable[str]) -> str:
    evidence_lines = [f"- {item}" for item in evidence]
    evidence_block = "\n".join(evidence_lines) if evidence_lines else "- No direct evidence found."
    return (
        "Answer the investigator clearly and concisely using only the supplied context.\n"
        f"Query: {question}\n"
        f"Context summary: {summary}\n"
        f"Evidence:\n{evidence_block}"
    )
