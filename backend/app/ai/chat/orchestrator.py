"""AI Orchestrator — ties intent routing, entity extraction, backend fetching, context building, and LLM generation together."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from sqlalchemy.orm import Session

from app.ai.chat.backend_fetcher import BackendFetcher
from app.ai.chat.context_builder import ContextBuilder
from app.ai.chat.entity_extractor import EntityExtractor
from app.ai.chat.intent_router import IntentRouter
from app.ai.chat.llm_generator import LLMGenerator
from app.ai.chat.memory import memory
from app.ai.chat.query_planner import QueryPlanner
from app.ai.chat.rag_retriever import RagRetriever
from app.ai.chat.response_validator import ResponseValidator


class ChatOrchestrator:
    """Main orchestrator for the Saksha AI Chat pipeline."""

    def __init__(self) -> None:
        self.intent_router = IntentRouter()
        self.entity_extractor = EntityExtractor()
        self.query_planner = QueryPlanner()
        self.backend_fetcher = BackendFetcher()
        self.rag_retriever = RagRetriever()
        self.context_builder = ContextBuilder()
        self.llm_generator = LLMGenerator()
        self.response_validator = ResponseValidator()

    async def process_message(
        self,
        message: str,
        session_id: str | None,
        db: Session,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[bytes]:
        sid = session_id or "default"
        # When an explicit history is supplied (persistent chat), it replaces the
        # in-memory session store and nothing is written back to memory.
        external_history = history is not None
        hist = history if external_history else memory.get_history(sid)

        yield self._ndjson({"type": "status", "content": "Analyzing query intent..."})

        intent_result = self.intent_router.detect(message)
        entities = self.entity_extractor.extract(message)

        yield self._ndjson({
            "type": "status",
            "content": f"Intent: {', '.join(i.value for i in intent_result.intents)}",
        })

        plan = self.query_planner.plan(intent_result.intents, entities)

        yield self._ndjson({
            "type": "status",
            "content": f"Querying {len(plan.backend_calls)} backend service(s)...",
        })

        results = self.backend_fetcher.execute(plan, db)

        # Free-text vector recall over database records (FIRs, criminals,
        # evidence, cases) — augments structured intent-based fetching.
        rag_result = self.rag_retriever.fetch(db, message)
        if rag_result:
            results.append(rag_result)

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        yield self._ndjson({
            "type": "status",
            "content": f"Retrieved data from {len(successful)} source(s)."
            + (f" {len(failed)} source(s) unavailable." if failed else ""),
        })

        built_context = self.context_builder.build(results, entities, message)

        yield self._ndjson({"type": "status", "content": "Generating response..."})

        full_response = ""
        async for chunk in self.llm_generator.generate(
            message=message,
            context_block=built_context.context_block,
            system_prompt=built_context.system_prompt,
            history=hist,
        ):
            full_response += chunk
            yield self._ndjson({"type": "token", "content": chunk})

        validated_response = self.response_validator.validate(full_response, results)

        if not external_history:
            memory.add(sid, message, validated_response)

        final_payload = {
            "type": "final",
            "content": {
                "answer": validated_response,
                "summary": built_context.summary,
                "entities": [str(v) for v in entities.to_dict().values() if v is not None],
                "classification": intent_result.intents[0].value if intent_result.intents else "general",
                "sources": built_context.sources,
                "chart_suggestion": self._suggest_chart(intent_result.intents),
                "citations": built_context.citations,
                "engine": self._engine_label(),
            },
        }
        yield self._ndjson(final_payload)

    def process_message_sync(
        self,
        message: str,
        session_id: str | None,
        db: Session,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        sid = session_id or "default"
        external_history = history is not None
        hist = history if external_history else memory.get_history(sid)

        intent_result = self.intent_router.detect(message)
        entities = self.entity_extractor.extract(message)
        plan = self.query_planner.plan(intent_result.intents, entities)
        results = self.backend_fetcher.execute(plan, db)
        rag_result = self.rag_retriever.fetch(db, message)
        if rag_result:
            results.append(rag_result)
        built_context = self.context_builder.build(results, entities, message)

        import asyncio

        async def _collect() -> str:
            chunks: list[str] = []
            async for chunk in self.llm_generator.generate(
                message=message,
                context_block=built_context.context_block,
                system_prompt=built_context.system_prompt,
                history=hist,
            ):
                chunks.append(chunk)
            return "".join(chunks)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    full_response = pool.submit(asyncio.run, _collect()).result()
            else:
                full_response = loop.run_until_complete(_collect())
        except RuntimeError:
            full_response = asyncio.run(_collect())

        validated_response = self.response_validator.validate(full_response, results)
        if not external_history:
            memory.add(sid, message, validated_response)

        return {
            "answer": validated_response,
            "summary": built_context.summary,
            "entities": [str(v) for v in entities.to_dict().values() if v is not None],
            "classification": intent_result.intents[0].value if intent_result.intents else "general",
            "sources": built_context.sources,
            "chart_suggestion": self._suggest_chart(intent_result.intents),
            "citations": built_context.citations,
            "engine": self._engine_label(),
        }

    def _engine_label(self) -> str:
        """Reports the engine that ACTUALLY produced the last answer.

        Falls back to configured provider only before any generation ran.
        """
        return getattr(self.llm_generator, "last_engine", None) or "local-template"

    @staticmethod
    def _ndjson(payload: dict[str, Any]) -> bytes:
        return (json.dumps(payload, default=str) + "\n").encode("utf-8")

    @staticmethod
    def _suggest_chart(intents: list) -> str | None:
        from app.ai.chat.intent_router import Intent
        for intent in intents:
            if intent in (Intent.CRIME_STATISTICS, Intent.DASHBOARD_ANALYTICS):
                return "bar"
            if intent == Intent.HOTSPOT_ANALYSIS:
                return "heatmap"
            if intent == Intent.PREDICTIONS:
                return "line"
            if intent == Intent.CRIMINAL_NETWORK:
                return "graph"
        return None

