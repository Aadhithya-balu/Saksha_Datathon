"""LLM generator — calls external LLM APIs (Groq/Gemini/OpenAI) or falls back to a
relevance-focused local template generation grounded strictly in retrieved context."""
from __future__ import annotations

import json
import re
from typing import AsyncIterator

import httpx

from app.core.config import settings


_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={key}"

# Groq is the primary provider (highest free-tier limits). API keys accept a
# comma-separated list; when one key hits its usage/rate limit the generator
# rotates to the next key, then to the next provider, then to local templates.
_PROVIDER_PRIORITY = ("groq", "gemini", "openai")
_PROVIDER_KEY_ATTR = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}
_PROVIDER_MODEL_ATTR = {"groq": "GROQ_MODEL", "gemini": "GEMINI_MODEL", "openai": "OPENAI_MODEL"}

_REQUEST_TIMEOUT = 60.0
_MAX_CONTEXT_LINES = 20
_HISTORY_LIMIT = 10

# HTTP statuses meaning "this key is done" — rotate to the next key.
_KEY_EXHAUSTED_STATUSES = {401, 402, 403, 429}


class _ProviderExhausted(Exception):
    """Raised when a provider attempt yields nothing usable (limits/errors)."""


_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "of", "in", "on", "at", "to", "for", "with",
    "about", "show", "me", "tell", "give", "list", "all", "and", "or",
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "many", "much", "any", "some", "please", "can", "could", "would",
    "should", "i", "you", "we", "they", "it", "its", "this", "that",
    "these", "those", "there", "here", "get", "need", "want", "know",
    "us", "my", "our", "am", "s", "t",
}

_SMALLTALK = {
    "hi", "hello", "hey", "yo", "thanks", "thank", "thx", "you", "ok",
    "okay", "good", "morning", "afternoon", "evening", "day", "namaste",
    "fine", "great", "cool", "welcome", "bye",
}

# Substrings that mark a context line as "this source had no data" — these must
# never poison an otherwise useful reply (issue #122: one empty source used to
# flip the entire answer into a canned refusal).
_NO_DATA_MARKERS = (
    "no relevant data",
    "no fir found", "no firs match", "no firs in",
    "no case found", "no matching cases", "no cases in database",
    "no criminal record found", "no criminal records match",
    "no officer found", "no officers found",
    "no victims found", "no notifications.", "no network data",
    "no hotspot data", "no anomalies detected", "no anomalies.",
    "no offender data", "no prediction available", "no forecast available",
    "no similar offenders", "no data.", "not implemented",
)

_REFUSAL_MESSAGE = (
    "I could not find matching records in the Saksha database for that query. "
    "Please try rephrasing your question or check the case/FIR number."
)

_SYSTEM_CLOCK_HEADER = "System Clock"

_RECENT_ACTIVITY_MARK = "recent activity"

_TEMPORAL_WORDS = {
    "today", "tonight", "yesterday", "morning", "evening",
    "recent", "recently", "latest", "newest", "new",
    "week", "month", "year", "day", "now", "current",
}
_MAX_OVERVIEW_LINES = 12

# Superlative/comparative questions ("which district has the highest crime
# rate?") get a direct ranked answer synthesized from numeric context lines.
_SUPERLATIVE_WORDS = (
    "highest", "high", "most", "top", "maximum", "max", "peak", "largest",
    "biggest", "lowest", "least", "minimum", "rank", "ranking", "compare",
)
_ASC_ORDER_WORDS = ("lowest", "least", "minimum")
_MAX_RANKED_BULLETS = 5
_TRAILING_LABEL_WORDS = {
    "has", "have", "with", "for", "of", "accounts", "record", "records",
    "registered", "total", "count", "is", "are", "at", "about", "and", "the", "in",
}

# Loose domain synonyms so recall survives wording differences between the
# question and database phrasing ("criminal rate" ↔ "registered crime cases").
_SYNONYMS: dict[str, tuple[str, ...]] = {
    "criminal": ("crime", "case", "offender", "suspect"),
    "crime": ("criminal", "case", "fir"),
    "rate": ("count", "total", "number", "cases", "statistic"),
    "district": ("area", "region"),
    "fir": ("case",),
    "victim": ("complainant",),
    "officer": ("police", "badge"),
    "gang": ("network", "organization"),
}

_GREETING_MESSAGE = (
    "I'm SAKSHA AI, your crime intelligence assistant. "
    "Ask me about cases, FIRs, criminals, suspects, officers, crime statistics, "
    "hotspots or district forecasts — I will pull the answers directly from the Saksha database."
)

_FOOTER_MESSAGE = (
    "Source: Saksha Database. Verify details against official records before taking action."
)

# Record identity extraction for cross-source de-duplication (vector retrieval
# and structured fetches often return the SAME FIR/case/person).
_RECORD_PATTERNS = (
    # Leading ID token that must contain a digit ("FIR-789/MYS/2026",
    # "1234/2026", "CR-2026-MYS-001" once its label prefix is stripped).
    re.compile(r"^[a-z0-9][a-z0-9/\-]*\d[a-z0-9/\-]*", re.IGNORECASE),
    re.compile(r"\bfir[\s:#-]*(?:no\.?\s*)?([a-z0-9/\-]*\d[a-z0-9/\-]*)", re.IGNORECASE),
    re.compile(r"(?:full name|criminal name|officer|victim name|officer name|name)\s*[:=]\s*([^|·\n.]+)", re.IGNORECASE),
)
# Leading "Label:" values that are fields, not person names — never used as identity.
_NON_NAME_LEADING_LABELS = {
    "fir", "fir number", "case", "case number", "case no", "status", "priority",
    "progress", "sections", "narrative", "filed", "complainant", "type",
    "evidence", "evidence title", "evidence type", "storage path", "description",
    "total", "source", "risk", "aliases", "ipc bns sections",
}
_LEADING_LABEL_RE = re.compile(r"^([A-Za-z][A-Za-z .'\-/]{1,38}):")


def _record_signature(line: str) -> str:
    """Stable identifier for a record line so duplicates collapse."""
    # Strip leading record-label prefixes so "FIR Number: 1234/2026" and
    # "FIR Number: FIR-789/MYS/2026" expose their real IDs to the patterns.
    cleaned = re.sub(r"^(?:fir|crime case|case)\s*(?:number|no\.?|id)?\s*[:#\-]\s*", "", line, flags=re.IGNORECASE)
    for pattern in _RECORD_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            value = match.group(1) if match.groups() else match.group(0)
            signature = re.sub(r"[^a-z0-9]", "", value.lower())
            if len(signature) >= 3:
                return signature
    leading = _LEADING_LABEL_RE.match(line)
    if leading and leading.group(1).strip().lower() not in _NON_NAME_LEADING_LABELS:
        return re.sub(r"[^a-z0-9]", "", leading.group(1).lower())
    return ""


def _strip_markdown(text: str) -> str:
    """Chat panels render plain text — strip every markdown decoration."""
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"`+", "", text)
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    return text.strip()


_PLATFORM_Q_RE = re.compile(
    r"\b(?:what\s+is|about|tell\s+me\s+about|describe|explain|purpose|goal|"
    r"who\s+(?:made|built|developed)|how\s+(?:does|do|did)|why\s+(?:is|was|are)|"
    r"architecture|tech\s+stack|features|capabilities|modules)\b"
    r".*?\b(?:saksha|platform|system|application|project|tool|crime\s+intelligence)\b",
    re.I,
)
_PLATFORM_KNOWLEDGE_RE = re.compile(
    r"SAKSHA PROJECT OVERVIEW.*?(?=RESPONSE FORMAT GUIDELINES|\Z)", re.S,
)
_PLATFORM_Q_LEAD = re.compile(
    r"^(?:what\s+is|about|tell\s+me\s+about|describe|explain|purpose|goal|overview)\b",
    re.I,
)
_PLATFORM_WORDS = {"saksha", "platform", "system", "application", "project", "crime intelligence"}


def _is_platform_question(message: str) -> bool:
    if _PLATFORM_Q_RE.search(message):
        return True
    lower = message.lower()
    if _PLATFORM_Q_LEAD.match(lower):
        return any(w in lower for w in _PLATFORM_WORDS)
    return False


def _extract_platform_knowledge(system_prompt: str) -> str:
    """Extracts the SAKSHA PROJECT OVERVIEW section from the system prompt."""
    match = _PLATFORM_KNOWLEDGE_RE.search(system_prompt)
    if match:
        return match.group(0).strip()
    return ""


class LLMGenerator:
    """Generates responses using an external LLM or a local relevance-focused fallback.

    Failover chain: every configured Groq key (primary, highest limits) → the
    next provider's key(s) → local template generation. A single answer is
    never stitched together from two providers: once a provider has streamed
    output, a later failure simply stops generation.
    """

    def __init__(self) -> None:
        self._transport = None  # test seam for httpx.MockTransport
        self._chain = self._provider_chain()
        self.provider = self._chain[0] if self._chain else "local"
        self.model = self._model_for(self.provider)
        # Engine that actually produced the most recent answer ("local-template"
        # when every provider failed) — the UI badge must reflect reality.
        self.last_engine: str = "local-template" if not self._chain else f"{self.provider}/{self.model}"

    @staticmethod
    def _parse_keys(value: str | None) -> list[str]:
        """Parses a comma-separated API key list ("key1,key2") into clean keys."""
        if not value:
            return []
        return [part.strip() for part in re.split(r"[,;]", value) if part.strip()]

    @classmethod
    def _provider_keys(cls, provider: str) -> list[str]:
        keys = cls._parse_keys(getattr(settings, _PROVIDER_KEY_ATTR[provider], None))
        return keys

    @classmethod
    def _provider_chain(cls) -> list[str]:
        requested = (settings.LLM_PROVIDER or "auto").strip().lower()
        if requested == "local":
            return []
        if requested in _PROVIDER_PRIORITY:
            return [requested] if cls._provider_keys(requested) else []
        return [name for name in _PROVIDER_PRIORITY if cls._provider_keys(name)]

    @classmethod
    def _model_for(cls, provider: str) -> str:
        explicit_model = (settings.LLM_MODEL or "").strip()
        if explicit_model and provider != "local":
            return explicit_model
        return getattr(settings, _PROVIDER_MODEL_ATTR.get(provider, "GEMINI_MODEL"))

    async def generate(
        self,
        message: str,
        context_block: str,
        system_prompt: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        produced = False
        for provider in self._chain:
            try:
                async for chunk in self._generate_via(provider, message, context_block, system_prompt, history):
                    produced = True
                    self.last_engine = f"{provider}/{self._model_for(provider)}"
                    yield chunk
                return
            except _ProviderExhausted:
                if produced:
                    # Partial answer already streamed — never stitch two providers.
                    return
                continue
        self.last_engine = "local-template"
        async for chunk in self._generate_local(message, context_block, system_prompt):
            yield chunk

    async def _generate_via(
        self,
        provider: str,
        message: str,
        context: str,
        system: str,
        history: list[dict[str, str]] | None,
    ) -> AsyncIterator[str]:
        if provider in ("groq", "openai"):
            url = _GROQ_URL if provider == "groq" else _OPENAI_URL
            async for chunk in self._stream_openai_compatible(
                url=url,
                api_keys=self._provider_keys(provider),
                model=self._model_for(provider),
                message=message,
                context=context,
                system=system,
                history=history,
            ):
                yield chunk
            return
        if provider == "gemini":
            async for chunk in self._stream_gemini(message, context, system, history):
                yield chunk
            return
        raise _ProviderExhausted(f"Unknown provider: {provider}")

    # ── Groq / OpenAI (OpenAI-compatible SSE with key rotation) ──────────

    async def _stream_openai_compatible(
        self,
        url: str,
        api_keys: list[str],
        model: str,
        message: str,
        context: str,
        system: str,
        history: list[dict[str, str]] | None,
    ) -> AsyncIterator[str]:
        messages = [{
            "role": "system",
            "content": system + "\n\n--- RETRIEVED CONTEXT ---\n" + context + "\n--- END CONTEXT ---",
        }]
        if history:
            for msg in history[-_HISTORY_LIMIT:]:
                role = msg.get("role", "user")
                messages.append({"role": "assistant" if role == "assistant" else "user", "content": msg.get("content", "")})
        messages.append({"role": "user", "content": message})

        payload = {"model": model, "messages": messages, "stream": True, "temperature": settings.LLM_CHAT_TEMPERATURE, "max_tokens": settings.LLM_CHAT_MAX_TOKENS}

        for index, api_key in enumerate(api_keys):
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            try:
                async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT, transport=self._transport) as client:
                    async with client.stream("POST", url, json=payload, headers=headers) as response:
                        if response.status_code >= 400:
                            await response.aread()
                            if response.status_code in _KEY_EXHAUSTED_STATUSES and index < len(api_keys) - 1:
                                continue  # key limit reached — rotate to next key
                            raise _ProviderExhausted(f"{url} returned HTTP {response.status_code}")
                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                        return
            except _ProviderExhausted:
                raise
            except Exception as exc:
                raise _ProviderExhausted(f"{url} failed: {exc}") from exc
        raise _ProviderExhausted(f"All {len(api_keys)} key(s) exhausted for {url}")

    # ── Gemini ────────────────────────────────────────────────────────────

    async def _stream_gemini(
        self, message: str, context: str, system: str, history: list[dict[str, str]] | None,
    ) -> AsyncIterator[str]:
        contents = []
        if history:
            for msg in history[-_HISTORY_LIMIT:]:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
        full_user_msg = f"{system}\n\n--- RETRIEVED CONTEXT ---\n{context}\n--- END CONTEXT ---\n\nUser Question: {message}"
        contents.append({"role": "user", "parts": [{"text": full_user_msg}]})

        gemini_keys = self._provider_keys("gemini")
        url = _GEMINI_URL.format(model=self._model_for("gemini"), key=gemini_keys[0] if gemini_keys else "")
        payload = {"contents": contents, "generationConfig": {"temperature": settings.LLM_CHAT_TEMPERATURE, "maxOutputTokens": settings.LLM_CHAT_MAX_TOKENS}}

        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT, transport=self._transport) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code >= 400:
                        await response.aread()
                        raise _ProviderExhausted(f"Gemini returned HTTP {response.status_code}")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                candidates = data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for part in parts:
                                        text = part.get("text", "")
                                        if text:
                                            yield text
                            except json.JSONDecodeError:
                                continue
        except _ProviderExhausted:
            raise
        except Exception as exc:
            raise _ProviderExhausted(f"Gemini failed: {exc}") from exc

    # ── Local fallback ────────────────────────────────────────────────────

    async def _generate_local(
        self, message: str, context: str, system: str,
    ) -> AsyncIterator[str]:
        # 1. Conversational / non-data replies come first: they require no
        #    database context and should never be mangled into a record list.
        conversation = self._conversation_reply(message)
        if conversation:
            for chunk in self._stream_text(conversation):
                yield chunk
            return

        tokens = self._query_tokens(message)
        if not tokens:
            for chunk in self._stream_text(_GREETING_MESSAGE):
                yield chunk
            return

        sections = self._useful_sections(context)

        if not sections:
            # No database records — try to answer from system prompt knowledge
            # (project overview, general Saksha info).
            if _is_platform_question(message):
                platform_knowledge = _extract_platform_knowledge(system)
                if platform_knowledge:
                    answer = (
                        f"**SAKSHA — Crime Intelligence & Analytical Platform**\n\n"
                        f"{platform_knowledge}\n\n"
                        f"{_FOOTER_MESSAGE}"
                    )
                    for chunk in self._stream_text(answer):
                        yield chunk
                    return
            for chunk in self._stream_text(_REFUSAL_MESSAGE):
                yield chunk
            return

        scored = []
        for header, lines in sections:
            # Header tokens count toward each line's score so a section whose
            # title matches the question ("Dossiers") surfaces its records.
            line_scores = [self._line_score(f"{header}\n{line}", tokens) for line in lines]
            scored.append((sum(line_scores), max(line_scores), header, lines, line_scores))

        # The clock/recency sections are only relevant to temporal questions;
        # otherwise they are metadata noise inside record lists.
        temporal = any(token in _TEMPORAL_WORDS for token in tokens)
        scored = [item for item in scored if item[2] != _SYSTEM_CLOCK_HEADER or temporal]
        if not scored:
            for chunk in self._stream_text(_REFUSAL_MESSAGE):
                yield chunk
            return

        positive = [item for item in scored if item[0] > 0]

        if not positive:
            response_parts: list[str] = [
                "I could not find records that directly match your question in the Saksha database.",
                "",
                _REFUSAL_MESSAGE,
            ]
            full_response = "\n".join(response_parts).strip()
            for chunk in self._stream_text(full_response):
                yield chunk
            return

        kept = positive if len(positive) >= 2 or (positive and temporal) else scored
        if temporal:
            # Time-window questions are answered ONLY by the clock/recency
            # sections — timeless dossiers/stats would bury the actual answer.
            windowed = [
                item for item in scored
                if item[2] == _SYSTEM_CLOCK_HEADER or _RECENT_ACTIVITY_MARK in item[2].lower()
            ]
            if windowed:
                kept = windowed
        kept.sort(key=lambda item: (-item[0],))

        # 2. ANSWER THE ACTUAL QUESTION instead of blindly dumping records:
        #    counts, field lookups (status/progress/when/where), and specific
        #    entity profiles are much more useful than a raw list.
        count_answer = self._count_answer(message, kept)
        if count_answer:
            for chunk in self._stream_text(count_answer):
                yield chunk
            return

        field_answer = self._field_answer(message, kept)
        if field_answer:
            for chunk in self._stream_text(field_answer):
                yield chunk
            return

        entity_answer = self._entity_profile_answer(message, kept)
        if entity_answer:
            for chunk in self._stream_text(entity_answer):
                yield chunk
            return

        ranked_answer = self._build_ranked_answer(message, kept)
        if ranked_answer:
            for chunk in self._stream_text(ranked_answer):
                yield chunk
            return

        # 3. General multi-record answer: a friendly lead-in followed by the
        #    deduplicated records rendered as clean bullet points.
        records = self._dedupe_lines(kept, _MAX_CONTEXT_LINES)
        if records:
            response_parts: list[str] = self._list_intro(message, len(records)) + [""]
            for i, line in enumerate(records, 1):
                response_parts.append(f"{i}. {self._format_line(line)}")
            response_parts.append("")
            response_parts.append(_FOOTER_MESSAGE)
            full_response = "\n".join(response_parts).strip()
            for chunk in self._stream_text(full_response):
                yield chunk
            return

        for chunk in self._stream_text(_REFUSAL_MESSAGE):
            yield chunk

    # -- Conversational helpers -------------------------------------------------

    @staticmethod
    def _conversation_reply(message: str) -> str | None:
        """Returns a natural reply for greetings/thanks/capability questions
        that are NOT database lookups. Returns None when the message should be
        treated as a data query."""
        cleaned = message.strip().lower().rstrip("?.!")
        words = [w.strip(".,!?;:") for w in message.lower().split()]
        words = [w for w in words if w]

        if not words:
            return _GREETING_MESSAGE

        # Gratitude / acknowledgement phrases ("thanks", "thank you", "thanks
        # for the help", "ok thanks") — even when extra connective words are
        # present, these are pure social replies, never data queries.
        if any(w in words for w in ("thanks", "thank", "thx", "ty", "gratitude")):
            return "You're welcome! Anything else you'd like me to pull from the Saksha database — cases, FIRs, criminals, or crime trends?"
        if any(w in words for w in ("bye", "goodbye", "goodnight")):
            return "Stay safe — I'm here whenever you need another look at the Saksha data."

        # Pure smalltalk (handles "hi", "hello", "ok", "good morning" etc.).
        core = [w for w in words if w not in _STOPWORDS]
        if 0 < len(words) <= 6 and all(w in _SMALLTALK for w in words):
            if any(w in {"hello", "hi", "hey", "yo", "namaste"} for w in words) and not any(w in {"crime", "case", "fir", "criminal"} for w in core):
                return _GREETING_MESSAGE
            return "Glad to help. Ask me about cases, FIRs, criminals, officers, crime statistics, hotspots or district forecasts."

        # Who / what are you
        if "who" in core and any(w in {"you", "are", "r"} for w in words):
            return (
                "I'm **SAKSHA AI**, the intelligence assistant for the Karnataka State Police platform. "
                "I can look up cases, FIRs, criminals, victims, officers and live statistics straight from the "
                "Saksha database, and I'll always cite the records I use. What would you like me to check?"
            )
        # What can you do / help
        if any(w in {"capabilities", "modules", "features"} for w in words) or cleaned in {
            "what can you do", "help", "what do you do", "how do you work", "what can you help with",
        }:
            return (
                "I can help you with the crime intelligence in Saksha. A few things I do well:\n\n"
                "- **Cases & FIRs** — pull case numbers, status, priority, sections and linked suspects.\n"
                "- **Criminals & offenders** — profile a person, their aliases, gang and linked cases.\n"
                "- **Statistics** — district and category breakdowns, trends and hotspots.\n"
                "- **Predictions** — district risk and 6-month crime forecasts.\n\n"
                "Try asking something like *\"Show case CR-2026-MYS-001\"* or *\"Which district has the most crime?\"*"
            )
        return None

    @staticmethod
    def _is_count_question(message: str) -> bool:
        lower = message.lower()
        return any(p in lower for p in (
            "how many", "number of", "count", "total number", "how much",
        ))

    @staticmethod
    def _count_answer(message: str, kept: list) -> str | None:
        """Answers 'how many' type questions with a concrete number."""
        if not LLMGenerator._is_count_question(message):
            return None
        records = LLMGenerator._dedupe_records(kept)
        if not records:
            return None
        tokens = [t.rstrip("s") for t in LLMGenerator._query_tokens(message)]
        subject = LLMGenerator._count_subject(message)
        kind = LLMGenerator._kind_for_subject(subject)
        # Narrow by subject type first, then by the query tokens.
        pool = records
        if kind is not None:
            pool = [r for r in records if LLMGenerator._record_kind(r) == kind]
        if not pool:
            pool = [r for r in records if LLMGenerator._line_score(LLMGenerator._record_text(r), tokens) > 0]
        if not pool:
            pool = records
        count = len(pool)
        matched = [r for r in pool if LLMGenerator._line_score(LLMGenerator._record_text(r), tokens) > 0]
        if matched and len(matched) < len(pool):
            count = len(matched)
        lead = "I found" if LLMGenerator._line_score(subject, tokens) or matched else "There are"
        noun = subject if count != 1 else subject.rstrip("s")
        return (
            f"{lead} **{count}** {noun} in the Saksha database matching your query."
            + f"\n\n{_FOOTER_MESSAGE}"
        )

    @staticmethod
    def _count_subject(message: str) -> str:
        lower = message.lower()
        for word in ("firs", "crimes", "cases", "criminals", "victims", "officers", "notifications", "anomalies"):
            if word in lower:
                return word
        return "records"

    @staticmethod
    def _field_answer(message: str, kept: list) -> str | None:
        """Answers field-specific questions (status/progress/when/where/who)."""
        lower = message.lower()
        field = None
        if any(w in lower for w in ("status", "state of", "condition")):
            field = "status"
        elif any(w in lower for w in ("progress", "how far", "investigation progress")):
            field = "progress"
        elif any(w in lower for w in ("when", "date", "filed on", "occurred")):
            field = "date"
        elif any(w in lower for w in ("where", "location", "district", "area")):
            field = "location"
        if field is None:
            return None

        records = LLMGenerator._dedupe_records(kept)
        if not records:
            return None
        # Pick the record that best matches the question tokens.
        tokens = [t.rstrip("s") for t in LLMGenerator._query_tokens(message)]
        records.sort(key=lambda r: -LLMGenerator._line_score(LLMGenerator._record_text(r), tokens))
        best = records[0]
        text = LLMGenerator._record_text(best)
        # Keep only field/values that are non-trivial and reasonably short.
        kept_bits = []
        for key, val in LLMGenerator._field_pairs(best):
            key_l = key.lower()
            if field == "status" and key_l in ("status", "case status", "fir status", "state"):
                kept_bits.append(f"Status: {val}")
            elif field == "progress" and "progress" in key_l:
                kept_bits.append(f"Progress: {val}")
            elif field == "location" and key_l in ("location", "district", "station", "area", "place", "region"):
                kept_bits.append(f"{key}: {val}")
            elif field == "date" and key_l in ("occurred", "reported", "filed", "filed at", "date", "occurred at", "reported at"):
                kept_bits.append(f"{key}: {val}")
        if not kept_bits:
            return None
        ident = LLMGenerator._record_ident(best) or "this record"
        return (
            f"Here's what the database shows for **{ident}**:\n\n"
            + "\n".join(f"- **{k}**: {v}" for k, v in (b.split(": ", 1) for b in kept_bits))
            + f"\n\n{_FOOTER_MESSAGE}"
        )

    @staticmethod
    def _entity_profile_answer(message: str, kept: list) -> str | None:
        """Builds a clean profile for a specific named/id'd entity.

        Only fires when the message clearly targets one entity (an explicit id,
        a named person, or a short 'tell me about X' request); blanket analytics
        questions never collapse into a single-entity profile.
        """
        tokens = [t.rstrip("s") for t in LLMGenerator._query_tokens(message)]
        if not tokens:
            return None
        records = LLMGenerator._dedupe_records(kept)
        if not records:
            return None
        records.sort(key=lambda r: -LLMGenerator._line_score(LLMGenerator._record_text(r), tokens))
        best = records[0]
        if not LLMGenerator._mentions_specific_entity(message, best):
            return None
        pairs = LLMGenerator._field_pairs(best)
        if len(pairs) < 2:
            return None
        ident = LLMGenerator._record_ident(best)
        if not ident:
            return None
        lines = [f"Here's the profile I found for **{ident}**:", ""]
        for key, val in pairs[:12]:
            if key == "_id":
                continue
            if LLMGenerator._is_no_data_line(f"{key}: {val}"):
                continue
            if val.lower() in {"n/a", "na", "none", "-", ""}:
                continue
            lines.append(f"- **{key}**: {val}")
        lines += ["", _FOOTER_MESSAGE]
        return "\n".join(lines)

    @staticmethod
    def _mentions_specific_entity(message: str, best: dict) -> bool:
        """True when the message points at one specific record (id, name, or a
        direct 'about <X>' / '<name>' request), not a broad analytics query."""
        lower = message.lower()
        # Explicit record id present in the message.
        if re.search(r"\b(?:cr|case|fir|if?r|no)[\s:-]{0,2}\d", lower) or re.search(r"\b\w{1,4}-\d{3,}", lower):
            return True
        ident = LLMGenerator._record_ident(best) or ""
        # A person/case name from the best record appears in the question.
        if ident and len(ident) >= 3 and ident.lower() in lower:
            return True
        if re.search(r"\b(?:about|profile|tell me about|details? on|info on|who is|what is)\b", lower):
            # Only a "specific" opener if followed by a noun, not "statistics/overview".
            if any(w in lower for w in ("statistics", "stats", "overview", "trend", "summary", "breakdown", "highest", "lowest", "most", "compare")):
                return False
            return True
        return False

    @staticmethod
    def _field_pairs(record: dict) -> list[tuple[str, str]]:
        """Flattens a parsed record dict to ('key', 'value') preserving order."""
        out: list[tuple[str, str]] = []
        for k, v in record.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    out.append((kk, str(vv)))
            else:
                out.append((k, str(v)))
        return out

    @staticmethod
    def _record_text(record: dict) -> str:
        return " ".join(f"{k}: {v}" for k, v in LLMGenerator._field_pairs(record))

    @staticmethod
    def _record_ident(record: dict) -> str | None:
        """Best identity token for a record (id/case/fir/name/badge)."""
        # Leading bare identifier captured by _parse_record (e.g. "CR-2026-MYS-001").
        if record.get("_id"):
            return str(record["_id"]).strip()
        normalized = {k.lower().replace(" ", "_"): str(v) for k, v in LLMGenerator._field_pairs(record)}
        for key in ("case_number", "fir_number", "criminal_name", "full_name", "person_name",
                    "offender_name", "officer_name", "victim_name", "name", "badge_number",
                    "id", "record_id", "case", "fir"):
            if normalized.get(key, "").strip():
                return normalized[key].strip()
        return None

    @staticmethod
    def _record_kind(record: dict) -> str:
        """Classifies a parsed record as case/fir/criminal/victim/officer."""
        _id = str(record.get("_id", "")).upper()
        if _id.startswith(("CR-", "CASE")) or "case_number" in record:
            return "case"
        if _id.startswith("FIR"):
            return "fir"
        keys = [k.lower().replace(" ", "_") for k in record.keys()]
        if any("criminal" in k or "offender" in k or "suspect" in k for k in keys):
            return "criminal"
        if any("victim" in k for k in keys):
            return "victim"
        if any("officer" in k or "badge" in k for k in keys):
            return "officer"
        if any("fir_number" in k or "fir" == k for k in keys):
            return "fir"
        if any("case" in k or "category" in k or "priority" in k for k in keys):
            return "case"
        return "record"

    @staticmethod
    def _kind_for_subject(subject: str) -> str | None:
        s = subject.lower().rstrip("s")
        if s == "case":
            return "case"
        if s in ("criminal", "offender", "suspect"):
            return "criminal"
        if s in ("fir",):
            return "fir"
        if s == "victim":
            return "victim"
        if s == "officer":
            return "officer"
        return None

    @staticmethod
    def _dedupe_lines(kept: list, cap: int) -> list[str]:
        """Collects deduplicated, non-junk context lines up to a cap."""
        emitted = 0
        seen_signatures: set[str] = set()
        out: list[str] = []
        for _, _, _header, lines, line_scores in kept:
            if emitted >= cap:
                break
            ranked = sorted(zip(lines, line_scores), key=lambda pair: -pair[1])
            for line, _score in ranked:
                if emitted >= cap:
                    break
                clean = _strip_markdown(line)
                if not clean:
                    continue
                signature = _record_signature(clean)
                if signature:
                    if signature in seen_signatures:
                        continue
                    seen_signatures.add(signature)
                emitted += 1
                out.append(clean)
        return out

    @staticmethod
    def _dedupe_records(kept: list) -> list[dict]:
        """Parses raw lines into ordered field/values, deduped by signature."""
        seen: set[str] = set()
        records: list[dict] = []
        for _, _, _header, lines, line_scores in kept:
            ranked = sorted(zip(lines, line_scores), key=lambda pair: -pair[1])
            for line, _score in ranked:
                clean = _strip_markdown(line)
                if not clean:
                    continue
                sig = _record_signature(clean)
                if sig:
                    if sig in seen:
                        continue
                    seen.add(sig)
                records.append(LLMGenerator._parse_record(clean))
        return [r for r in records if r]

    @staticmethod
    def _parse_record(line: str) -> dict:
        """Parses 'Key: Value | Key2: Value2' (or 'Key: Value') into an ordered dict.

        A leading bare token without a colon (e.g. 'CR-2026-MYS-001') is captured
        as the record's identifier under the '_id' key."""
        parts = [p.strip() for p in re.split(r"\s*\|\s*", line) if p.strip()]
        if not parts:
            return {}
        record: dict[str, str] = {}
        first = parts[0]
        if ":" not in first:
            record["_id"] = first
            parts = parts[1:]
        for part in parts:
            if ":" in part:
                key, _, val = part.partition(":")
                record[key.strip()] = val.strip()
            else:
                record.setdefault("value", part)
        return record if (record.get("_id") or len(record) > 0) else {}

    @staticmethod
    def _list_intro(message: str, count: int) -> list[str]:
        lower = message.lower()
        if _is_platform_question(message):
            return ["Here's what I found about Saksha:", ""]
        if any(w in lower for w in ("criminal", "offender", "suspect", "gang")):
            return [f"Here are the criminal/offender records I found ({count}):", ""]
        if any(w in lower for w in ("fir", "first information")):
            return [f"Here are the FIR records I found ({count}):", ""]
        if any(w in lower for w in ("case", "complaint")):
            return [f"Here are the case records I found ({count}):", ""]
        if any(w in lower for w in ("officer", "police", "badge")):
            return [f"Here are the officer records I found ({count}):", ""]
        if any(w in lower for w in ("statistic", "trend", "overview", "district", "category", "rate")):
            return [f"Here's the breakdown I found in the database ({count} entries):", ""]
        return [f"Here's what I found in the Saksha database ({count} records):", ""]

    @staticmethod
    def _stream_text(text: str) -> AsyncIterator[str]:
        """Yields typing-effect chunks while preserving EVERY newline and blank
        line — the chat UI's markdown renderer needs intact line breaks to lay
        out headings, lists and record rows (issue #124)."""
        segments = re.findall(r"\S+\s*|\s+", text)
        if not segments:
            return
        chunk_size = max(5, len(segments) // 30)
        for i in range(0, len(segments), chunk_size):
            yield "".join(segments[i:i + chunk_size])

    @staticmethod
    def _is_smalltalk(message: str) -> bool:
        words = [w.strip(".,!?;:") for w in message.lower().split()]
        words = [w for w in words if w]
        return 0 < len(words) <= 4 and all(w in _SMALLTALK for w in words)

    @staticmethod
    def _query_tokens(message: str) -> list[str]:
        raw_tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9/\-]*", message.lower())
        tokens: list[str] = []
        for token in raw_tokens:
            if token in _STOPWORDS:
                continue
            if len(token) <= 2 and not any(ch.isdigit() for ch in token):
                continue
            if token not in tokens:
                tokens.append(token)
        return tokens

    @staticmethod
    def _split_sections(context: str) -> list[tuple[str, list[str]]]:
        sections: list[tuple[str, list[str]]] = []
        current_header = ""
        current_lines: list[str] = []
        for raw_line in context.split("\n"):
            line = raw_line.strip()
            if line.startswith("### "):
                if current_header or current_lines:
                    sections.append((current_header, current_lines))
                current_header = line[4:].strip()
                current_lines = []
                continue
            if not line:
                continue
            current_lines.append(line)
        if current_header or current_lines:
            sections.append((current_header, current_lines))
        return sections

    @classmethod
    def _useful_sections(cls, context: str) -> list[tuple[str, list[str]]]:
        useful = []
        for header, lines in cls._split_sections(context):
            content_lines = [
                line for line in lines
                if not cls._is_no_data_line(line) and not cls._is_junk_line(line)
            ]
            if content_lines:
                useful.append((header, content_lines))
        return useful

    @staticmethod
    def _is_no_data_line(line: str) -> bool:
        lowered = line.lower()
        return any(marker in lowered for marker in _NO_DATA_MARKERS)

    @staticmethod
    def _is_junk_line(line: str) -> bool:
        """Lines dominated by missing values (e.g. 'N/A: Status=..., Risk=N/A')
        carry zero intelligence and must never reach the answer."""
        lowered = line.lower()
        if lowered.count("n/a") >= 2:
            return True
        leading_field = re.split(r"[:=|]", line, 1)[0].strip().lower()
        return leading_field in {"n/a", "na", "unknown", "null", "-"}

    @classmethod
    def _line_score(cls, line: str, tokens: list[str]) -> int:
        lowered = line.lower()
        score = 0
        for token in tokens:
            if token in lowered:
                score += 1
                continue
            # Naive plural stem so "crimes" matches "cyber crime" etc.
            stemmed = token[:-1] if len(token) > 3 and token.endswith("s") else token
            if len(stemmed) > 2 and stemmed in lowered:
                score += 1
                continue
            if any(syn in lowered or syn.rstrip("s") in lowered
                   for syn in _SYNONYMS.get(token, ())):
                score += 1
        return score

    @staticmethod
    def _has_superlative_intent(message: str) -> tuple[bool, bool]:
        """Returns (is_superlative, ascending)."""
        words = set(re.findall(r"[a-z]+", message.lower()))
        if not words & set(_SUPERLATIVE_WORDS):
            return False, False
        ascending = bool(words & set(_ASC_ORDER_WORDS))
        return True, ascending

    @staticmethod
    def _extract_ranked_pairs(lines: list[str], tokens: list[str]) -> list[tuple[str, int]]:
        """Extracts (label, single_number) pairs like 'District Bengaluru Urban
        has 28 registered crime cases'. Comma-joined enumerations (how the
        analytics service emits district/category distributions) are split
        into fragments first."""
        pairs: list[tuple[str, int]] = []
        seen_labels: set[str] = set()
        for line in lines:
            for fragment in re.split(r",\s+(?=[A-Z])", line):
                if "=" in fragment:
                    continue  # Key=Value dossier fields pollute rankings
                numbers = re.findall(r"\d[\d,]*", fragment)
                if len(numbers) != 1:
                    continue  # summaries/narratives pollute rankings
                match = re.search(r"\d[\d,]*", fragment)
                label = fragment[:match.start()].strip(" -–—*:|")
                # Drop a leading category word already implied by the question.
                first_word = label.split(" ", 1)
                if len(first_word) == 2 and first_word[0].lower().rstrip("s") in tokens:
                    label = first_word[1].strip()
                # Drop trailing connectives so labels read naturally.
                label_words = label.split()
                while label_words and label_words[-1].lower() in _TRAILING_LABEL_WORDS:
                    label_words.pop()
                label = " ".join(label_words)
                number = int(numbers[0].replace(",", ""))
                if not label or len(label) > 60 or number < 0 or label.lower() in seen_labels:
                    continue
                seen_labels.add(label.lower())
                pairs.append((label, number))
        return pairs

    @classmethod
    def _build_ranked_answer(cls, message: str, kept: list[tuple[int, int, str, list[str], list[int]]]) -> str | None:
        superlative, ascending = cls._has_superlative_intent(message)
        if not superlative:
            return None

        tokens = [t.rstrip("s") for t in cls._query_tokens(message)]
        scored_lines: list[tuple[str, int]] = []
        for total, _max_score, _header, lines, line_scores in kept:
            if total <= 0:
                continue
            for line, line_score in zip(lines, line_scores):
                if line_score > 0:
                    scored_lines.append((line, line_score))

        ranked = cls._extract_ranked_pairs([line for line, _ in scored_lines], tokens)
        if not ranked:
            return None
        ranked.sort(key=lambda pair: pair[1], reverse=not ascending)

        top_label, top_number = ranked[0]
        rest = ranked[1:4]
        if rest:
            tail = ", ".join(f"{label} ({number})" for label, number in rest)
            lead = f"{top_label} has the highest count with {top_number}, followed by {tail}."
            if ascending:
                lead = f"{top_label} has the lowest count with {top_number}, ahead of {tail}."
        else:
            lead = f"{top_label} has the highest count with {top_number}."
            if ascending:
                lead = f"{top_label} has the lowest count with {top_number}."

        parts = [lead, ""]
        for label, number in ranked[:_MAX_RANKED_BULLETS]:
            parts.append(f"- {label}: {number}")
        parts += ["", _FOOTER_MESSAGE]
        return "\n".join(parts)

    @staticmethod
    def _format_line(line: str) -> str:
        """Renders one record as a single plain-text entry (no markdown)."""
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                normalized = []
                for part in parts:
                    if ":" in part:
                        key, val = part.split(":", 1)
                        normalized.append(f"{key.strip()}: {val.strip()}")
                    else:
                        normalized.append(part)
                return " | ".join(normalized)
            return parts[0] if parts else line
        if line.startswith("- ") or line.startswith("* "):
            return line[2:].strip()
        if ":" in line:
            key, val = line.split(":", 1)
            return f"{key.strip()}: {val.strip()}"
        return line


