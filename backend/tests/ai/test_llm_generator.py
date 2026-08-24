"""Tests for LLMGenerator — provider resolution, key failover, and local fallback relevance (issue #122)."""
from __future__ import annotations

import asyncio
import json
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("APP_DEBUG", "false")

import httpx
import pytest

from app.ai.chat.llm_generator import LLMGenerator
from app.core.config import settings


def _collect_local(generator: LLMGenerator, message: str, context: str, system: str) -> str:
    async def _run() -> str:
        chunks: list[str] = []
        async for chunk in generator._generate_local(message, context, system):
            chunks.append(chunk)
        return "".join(chunks)

    return asyncio.run(_run())


def _collect_generate(generator: LLMGenerator, message: str, context: str, system: str) -> str:
    async def _run() -> str:
        chunks: list[str] = []
        async for chunk in generator.generate(message, context, system):
            chunks.append(chunk)
        return "".join(chunks)

    return asyncio.run(_run())


def _sse_openai(*tokens: str) -> str:
    frames = "".join(
        f'data: {json.dumps({"choices": [{"delta": {"content": token}}]})}\n\n' for token in tokens
    )
    return frames + "data: [DONE]\n\n"


def _sse_gemini(*tokens: str) -> str:
    frames = "".join(
        f'data: {json.dumps({"candidates": [{"content": {"parts": [{"text": token}]}}]})}\n\n'
        for token in tokens
    )
    return frames + "data: [DONE]\n\n"


@pytest.fixture
def no_keys(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "LLM_MODEL", "")


class TestProviderResolution:
    def test_auto_with_no_keys_is_local(self, no_keys, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
        assert LLMGenerator().provider == "local"

    def test_auto_prefers_groq(self, no_keys, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-test")
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
        gen = LLMGenerator()
        assert gen.provider == "groq"
        assert gen.model == settings.GROQ_MODEL

    def test_auto_falls_back_to_gemini_then_openai(self, no_keys, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "gem-test")
        assert LLMGenerator().provider == "gemini"
        monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
        assert LLMGenerator().provider == "openai"

    def test_explicit_provider_without_key_is_local(self, no_keys, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
        assert LLMGenerator().provider == "local"

    def test_explicit_local_stays_local_even_with_keys(self, no_keys, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "local")
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-test")
        assert LLMGenerator().provider == "local"

    def test_explicit_llm_model_overrides_provider_default(self, no_keys, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-test")
        monkeypatch.setattr(settings, "LLM_MODEL", "my-custom-model")
        assert LLMGenerator().model == "my-custom-model"


class TestLocalGeneration:
    @pytest.fixture
    def local_gen(self, no_keys, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "local")
        return LLMGenerator()

    def test_empty_context_yields_refusal(self, local_gen):
        answer = _collect_local(local_gen, "Show me FIR 1234/2026", "No relevant data was found in the Saksha database for this query.", "sys")
        assert "could not find matching records" in answer

    def test_all_empty_sources_yield_refusal(self, local_gen):
        context = (
            "### Saksha PostgreSQL Database — Officers\nNo officers found.\n\n"
            "### Saksha PostgreSQL Database — Fir\nNo FIR found."
        )
        answer = _collect_local(local_gen, "Any officers?", context, "sys")
        assert "could not find matching records" in answer

    def test_single_empty_source_does_not_poison_reply(self, local_gen):
        """Regression for issue #122: one 'No X found' source must not flip the
        whole reply into a canned refusal when other sources returned data."""
        context = (
            "### Saksha PostgreSQL Database — Fir\n"
            "FIR Number: 1234/2026 | Complainant: Ravi Kumar | Status: open | Sections: IPC 379\n\n"
            "### Saksha PostgreSQL Database — Officers\n"
            "No officers found."
        )
        answer = _collect_local(local_gen, "What is the status of FIR 1234/2026?", context, "sys")
        assert "could not find matching records" not in answer
        assert "1234/2026" in answer
        assert "Ravi Kumar" in answer

    def test_relevant_section_ranked_first(self, local_gen):
        context = (
            "### Saksha Analytics Engine — Crime Statistics\n"
            "Total crimes: 11. Open cases: 5. Resolution rate: 40%.\n\n"
            "### Saksha PostgreSQL Database — Criminal Record\n"
            "Name: Ramu Swamy | Status: at_large | Aliases: Ramu\n"
            "Name: Vikram Yadav | Status: arrested | Aliases: Vicky"
        )
        answer = _collect_local(local_gen, "Who is Ramu Swamy?", context, "sys")
        assert answer.index("Ramu Swamy") < answer.index("Total crimes")

    def test_smalltalk_gets_greeting_not_data_dump(self, local_gen):
        context = (
            "### Saksha Analytics Engine — Summary\n"
            "Total crimes: 11. Open cases: 5. Resolution rate: 40%."
        )
        answer = _collect_local(local_gen, "hello!", context, "sys")
        assert "SAKSHA AI" in answer
        assert "Total crimes" not in answer

    def test_answer_carries_source_footer(self, local_gen):
        context = (
            "### Saksha PostgreSQL Database — Case\n"
            "Case: CR-2026-KA-0001 | Status: open | Priority: high | Progress: 20%"
        )
        answer = _collect_local(local_gen, "Details of case CR-2026-KA-0001", context, "sys")
        assert "Saksha Database" in answer

    def test_zero_overlap_with_stats_yields_honest_overview(self, local_gen):
        context = (
            "### Saksha Analytics Engine — Crime Statistics\n"
            "Total crimes: 11. Open cases: 5. Resolution rate: 40%.\n\n"
            "### Saksha PostgreSQL Database — Criminal Record\n"
            "Name: Ramu Swamy | Status: at_large | Aliases: Ramu"
        )
        answer = _collect_local(local_gen, "What is the airspeed velocity of an unladen swallow?", context, "sys")
        assert "could not find records directly matching" in answer
        assert "Total crimes" in answer
        assert "Ramu Swamy" in answer  # all on-file records are shown honestly

    def test_zero_overlap_with_retrieved_records_shows_honest_overview(self, local_gen):
        """Records exist even when wording doesn't overlap — never claim the
        database has nothing (regression for 'Bengaluru criminal lists')."""
        context = (
            "### Saksha PostgreSQL Database — Dossiers\n"
            "Ramu Swamy: Status=INCARCERATED, Classification=A-CATEGORY, Risk=83, Active Districts=Mysuru\n"
            "Vikram Yadav: Status=ACTIVE, Classification=A-CATEGORY, Risk=71, Active Districts=Bengaluru"
        )
        answer = _collect_local(local_gen, "What is the airspeed velocity of an unladen swallow?", context, "sys")
        assert "could not find records directly matching" in answer
        assert "could not find matching records in the Saksha database for that query" not in answer
        assert "Ramu Swamy" in answer and "Vikram Yadav" in answer

    def test_bengaluru_criminal_lists_returns_records_not_refusal(self, local_gen):
        context = (
            "### Saksha PostgreSQL Database — Criminals\n"
            "Name: Vikram Yadav | Status: at_large | Address: 14, Whitefield, Bengaluru | MO: Warehouse burglaries\n"
            "Name: Ramu Swamy | Status: arrested | Address: Mysuru central | MO: Chain snatching"
        )
        answer = _collect_local(local_gen, "Bengaluru criminal lists", context, "sys")
        assert "could not find matching records in the Saksha database for that query" not in answer
        assert "Vikram Yadav" in answer

    def test_query_tokens_ignore_stopwords(self):
        tokens = LLMGenerator._query_tokens("What is the status of the theft case?")
        assert "status" in tokens
        assert "theft" in tokens
        assert "the" not in tokens

    def test_superlative_district_query_gets_direct_ranked_answer(self, local_gen):
        """Regression: 'Which district has high criminal rate?' must answer with a
        ranked summary — no relevance metadata, no N/A dossier noise, no dump."""
        context = (
            "### Saksha PostgreSQL Database — Vector Retrieval\n"
            "District Bengaluru Urban has 28 registered crime cases, District Mysuru has 13 registered crime cases, "
            "District Belagavi has 8 registered crime cases, District Dharwad has 8 registered crime cases, "
            "District Ballari has 7 registered crime cases\n\n"
            "### Saksha PostgreSQL Database — Dossiers\n"
            "N/A: Status=INCARCERATED, Classification=A-CATEGORY, Risk=N/A\n"
            "N/A: Status=ACTIVE, Classification=A-CATEGORY, Risk=N/A\n\n"
            "### Saksha Analytics Engine — Crime Statistics\n"
            "Total crime records: 61. Open active cases: 30."
        )
        answer = _collect_local(local_gen, "Which district has high criminal rate?", context, "sys")
        assert "Bengaluru Urban" in answer and "28" in answer
        assert "Mysuru (13)" in answer and "Belagavi (8)" in answer
        assert "N/A" not in answer
        assert "*" not in answer and "#" not in answer
        assert "Total crime records" not in answer

    def test_superlative_lowest_orders_ascending(self, local_gen):
        context = (
            "### Saksha PostgreSQL Database — Vector Retrieval\n"
            "District Bengaluru Urban has 28 registered crime cases, District Hassan has 2 registered crime cases"
        )
        answer = _collect_local(local_gen, "Which district has the lowest crime count?", context, "sys")
        assert "Hassan has the lowest count with 2" in answer
        assert "*" not in answer and "#" not in answer

    def test_list_answers_have_clean_lead_in_without_titles(self, local_gen):
        context = (
            "### Saksha PostgreSQL Database — Criminal Record\n"
            "Name: Ramu Swamy | Status: at_large | Aliases: Ramu"
        )
        answer = _collect_local(local_gen, "Who is Ramu Swamy?", context, "sys")
        assert "matching Saksha database records" in answer
        assert "# Suspect Profile Dossier" not in answer
        assert "Crime Intelligence Summary" not in answer

    def test_junk_na_lines_never_reach_any_answer(self, local_gen):
        context = (
            "### Saksha PostgreSQL Database — Dossiers\n"
            "N/A: Status=INCARCERATED, Classification=A-CATEGORY, Risk=N/A\n"
            "Name: Mohsin Pasha | Status: ACTIVE | Risk: 71"
        )
        answer = _collect_local(local_gen, "Show me offender dossiers", context, "sys")
        assert "N/A:" not in answer
        assert "Mohsin Pasha" in answer

    def test_duplicate_records_across_sources_are_listed_once(self, local_gen):
        """Vector retrieval and the structured FIR fetch return the SAME records —
        each FIR must appear exactly once in the answer."""
        context = (
            "### Saksha PostgreSQL Database — Vector Retrieval\n"
            "FIR Number: FIR-789/MYS/2026. Complainant: Dr. Vinay Murthy. Status: registered. "
            "Sections: IPC 379. Narrative: Backend-seeded FIR for CR-2026-MYS-001.\n"
            "FIR Number: FIR-790/MYS/2026. Complainant: Dr. Vinay Murthy. Status: closed.\n\n"
            "### Saksha PostgreSQL Database — Fir\n"
            "FIR Number: FIR-789/MYS/2026 | Complainant: Dr. Vinay Murthy | Status: registered | Sections: IPC 379\n"
            "FIR Number: FIR-790/MYS/2026 | Complainant: Dr. Vinay Murthy | Status: closed\n"
            "FIR Number: FIR-792/MYS/2026 | Complainant: State Complainant | Status: registered"
        )
        answer = _collect_local(local_gen, "Show me all FIRs", context, "sys")
        assert answer.count("FIR-789/MYS/2026") == 1
        assert answer.count("FIR-790/MYS/2026") == 1
        assert "FIR-792/MYS/2026" in answer
        assert "*" not in answer and "#" not in answer

    def test_answers_are_plain_text_without_markdown(self, local_gen):
        context = (
            "### Saksha PostgreSQL Database — Case\n"
            "Case: CR-2026-KA-0001 | Status: open | Priority: high | Progress: 20%"
        )
        answer = _collect_local(local_gen, "Details of case CR-2026-KA-0001", context, "sys")
        for char in ("*", "#", "`"):
            assert char not in answer
        assert "---" not in answer

    def test_streaming_preserves_line_structure(self, local_gen):
        """Regression for issue #124: typing-effect chunking must keep newlines —
        flattening the reply into one line left the chat UI with an unreadable
        blob instead of a lead-in, one record per line, and a footer."""
        context = (
            "### Saksha PostgreSQL Database — Criminal Record\n"
            "Name: Ramu Swamy | Status: at_large | Aliases: Ramu\n"
            "Name: Vikram Yadav | Status: arrested | Aliases: Vicky"
        )
        answer = _collect_local(local_gen, "Who is Ramu Swamy?", context, "sys")
        lines = [line.strip() for line in answer.split("\n") if line.strip()]
        assert len(lines) >= 4  # lead-in + two records + footer
        assert lines[0].startswith("Here are the matching")
        assert lines[1].startswith("1. Name:")
        assert lines[2].startswith("2. Name:")
        assert lines[-1].startswith("Source: Saksha Database")

    def test_stream_text_round_trips_whitespace_exactly(self):
        text = "Lead-in:\n\n1. First record\n2. Second record\n\nSource: Saksha Database."
        chunks = list(LLMGenerator._stream_text(text))
        assert "".join(chunks) == text
        assert len(chunks) > 1  # still delivered as multiple typing chunks


class TestKeyFailover:
    """Groq primary with comma-separated fallback keys, then provider cascade."""

    def test_parse_keys_splits_and_cleans(self):
        assert LLMGenerator._parse_keys("k1, k2;;k3 ,") == ["k1", "k2", "k3"]
        assert LLMGenerator._parse_keys("solo") == ["solo"]
        assert LLMGenerator._parse_keys("") == []
        assert LLMGenerator._parse_keys(None) == []

    def test_rotates_to_fallback_key_on_rate_limit(self, no_keys, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-primary,gsk-backup")

        seen_auth: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_auth.append(request.headers.get("Authorization", ""))
            if len(seen_auth) == 1:
                return httpx.Response(429, json={"error": {"message": "Rate limit reached"}})
            return httpx.Response(200, content=_sse_openai("Answer ", "from backup key").encode())

        gen = LLMGenerator()
        gen._transport = httpx.MockTransport(handler)
        answer = _collect_generate(gen, "Who is Ramu Swamy?", "Name: Ramu Swamy | Status: arrested", "sys")
        assert answer == "Answer from backup key"
        assert seen_auth == ["Bearer gsk-primary", "Bearer gsk-backup"]

    def test_cascades_to_gemini_when_all_groq_keys_exhausted(self, no_keys, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-a,gsk-b")
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "gem-x")

        groq_hits = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal groq_hits
            if "api.groq.com" in str(request.url):
                groq_hits += 1
                return httpx.Response(429, json={"error": {"message": "Rate limit reached"}})
            return httpx.Response(200, content=_sse_gemini("Gemini ", "answer").encode())

        gen = LLMGenerator()
        gen._transport = httpx.MockTransport(handler)
        answer = _collect_generate(gen, "Who is Ramu Swamy?", "Name: Ramu Swamy | Status: arrested", "sys")
        assert answer == "Gemini answer"
        assert groq_hits == 2

    def test_local_fallback_when_every_provider_fails(self, no_keys, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-only")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"error": {"message": "Rate limit reached"}})

        gen = LLMGenerator()
        gen._transport = httpx.MockTransport(handler)
        context = (
            "### Saksha PostgreSQL Database — FIR Record\n"
            "FIR Number: FIR/2026/77 | Complainant: Meena | Status: open\n"
            "Narrative: Gold chain snatching near KR Puram bus stand."
        )
        answer = _collect_generate(gen, "What happened in FIR 77?", context, "sys")
        assert "FIR/2026/77" in answer
        # the badge must reflect the engine that ACTUALLY answered
        assert gen.last_engine == "local-template"

    def test_last_engine_reports_successful_provider(self, no_keys, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-ok")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=_sse_openai("Hello ", "from groq").encode())

        gen = LLMGenerator()
        gen._transport = httpx.MockTransport(handler)
        _collect_generate(gen, "Who is Ramu Swamy?", "Name: Ramu Swamy | Status: arrested", "sys")
        assert gen.last_engine.startswith("groq/")

    def test_explicit_provider_ignores_other_providers_but_keeps_local(self, no_keys, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-a")
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-openai")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        gen = LLMGenerator()
        gen._transport = httpx.MockTransport(handler)
        context = (
            "### Saksha PostgreSQL Database — Criminal Record\n"
            "Name: Vikram Yadav | Status: at_large | Aliases: Vicky"
        )
        answer = _collect_generate(gen, "Who is Vikram Yadav?", context, "sys")
        assert "Vikram Yadav" in answer

