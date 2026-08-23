"""Context builder — merges backend results into structured context for the LLM."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.ai.chat.backend_fetcher import BackendResult
from app.ai.chat.entity_extractor import ExtractedEntities


SYSTEM_PROMPT = """You are SAKSHA AI, an enterprise-grade Crime Intelligence Assistant for the Karnataka State Police.

CRITICAL RULES:
- Answer ONLY using the supplied context data from the Saksha database.
- NEVER fabricate names, dates, IDs, case numbers, FIR numbers, officer names, or statistics.
- NEVER invent criminal relationships or associations not present in the context.
- If the context does not contain enough information, say: "I could not find matching records in the Saksha database for that query."
- Be concise, professional, and direct — this is a law enforcement tool.
- When presenting data, use structured format with bullet points and bold field names.
- When discussing criminals or cases, always reference specific IDs, numbers, or names from the context.
- Do not use emojis.
- Do not add disclaimers about being an AI unless explicitly asked.
- TEMPORAL RULE: A "System Clock" section states the current date/time and every
  record carries created_at / filed_at timestamps. For questions about "today",
  "yesterday", "this week", or recency, compare those timestamps against the
  System Clock and use the "recent activity" figures when present. Never guess.
  Lead with those recency figures ("No new FIRs were filed today" or the counts)
  and do NOT pad the reply with unrelated dossiers or record lists.

RESPONSE FORMAT GUIDELINES:
- For case queries: Present case number, status, priority, progress, description, and MO tags clearly.
- For criminal queries: Present name, status, aliases, MO, identifying marks, and linked cases.
- For FIR queries: Present FIR number, complainant, sections, status, narrative summary, and linked suspects.
- For statistics: Present numbers in a clear structured format with bullet points.
- For officer queries: Present name, badge, rank, station, and district.
- Always end with a brief summary or key takeaway when presenting case/criminal data.
- When multiple records are found, present them as a numbered list with key details for each."""


@dataclass
class BuiltContext:
    system_prompt: str
    context_block: str
    summary: str
    sources: list[str] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)


_SOURCE_LABELS = {
    "postgres": "Saksha PostgreSQL Database",
    "neo4j": "Saksha Neo4j Graph Database",
    "ml": "Saksha ML Prediction Engine",
    "analytics": "Saksha Analytics Engine",
}


class ContextBuilder:
    """Merges BackendResult objects into a structured context block for the LLM."""

    def build(
        self,
        results: list[BackendResult],
        entities: ExtractedEntities,
        message: str,
    ) -> BuiltContext:
        sections: list[str] = []
        sources: list[str] = []
        citations: list[dict[str, Any]] = []
        successful = [r for r in results if r.success and r.content.strip()]

        if not successful:
            return BuiltContext(
                system_prompt=SYSTEM_PROMPT,
                context_block="No relevant data was found in the Saksha database for this query.",
                summary="No backend data retrieved.",
                sources=[],
                citations=[],
            )

        # Ground every answer in wall-clock time so temporal questions
        # ("any crime today?") are answerable from record timestamps.
        sections.append(
            "### System Clock\n"
            f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M (%A)')}"
        )

        for result in successful:
            label = _SOURCE_LABELS.get(result.source, result.source)
            header = f"### {label} — {result.data_type.replace('_', ' ').title()}"
            sections.append(f"{header}\n{result.content}")
            sources.append(label)
            citations.append({
                "source": result.source,
                "title": f"{result.data_type} from {label}",
                "score": 1.0,
            })

        context_block = "\n\n".join(sections)
        summary = self._build_summary(successful, entities)
        return BuiltContext(
            system_prompt=SYSTEM_PROMPT,
            context_block=context_block,
            summary=summary,
            sources=sources,
            citations=citations,
        )

    def _build_summary(self, results: list[BackendResult], entities: ExtractedEntities) -> str:
        parts = [f"Retrieved data from {len(results)} backend source(s)."]
        entity_parts = []
        if entities.fir_number:
            entity_parts.append(f"FIR #{entities.fir_number}")
        if entities.case_id:
            entity_parts.append(f"Case {entities.case_id}")
        if entities.person_name:
            entity_parts.append(f"Person: {entities.person_name}")
        if entities.district:
            entity_parts.append(f"District: {entities.district}")
        if entity_parts:
            parts.append("Entities: " + ", ".join(entity_parts))
        return " ".join(parts)
