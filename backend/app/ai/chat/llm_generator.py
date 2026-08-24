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
_MAX_CONTEXT_LINES = 40
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

_NO_DIRECT_MATCH_PREFIX = (
    "I could not find records directly matching your question in the Saksha database.\n"
    "Here is what is currently on file for reference:"
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

        payload = {"model": model, "messages": messages, "stream": True, "temperature": 0.3, "max_tokens": 2048}

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
        payload = {"contents": contents, "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}}

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
        if self._is_smalltalk(message):
            yield _GREETING_MESSAGE
            return

        tokens = self._query_tokens(message)
        if not tokens:
            yield _GREETING_MESSAGE
            return

        sections = self._useful_sections(context)
        if not sections:
            yield _REFUSAL_MESSAGE
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
            yield _REFUSAL_MESSAGE
            return

        positive = [item for item in scored if item[0] > 0]

        if not positive:
            # Nothing matches lexically, but the database DID return records —
            # stay honest about the miss while showing what is on file instead
            # of claiming there is no information (issue: "Bengaluru criminal
            # lists" was refused although dossiers existed).
            response_parts: list[str] = [_NO_DIRECT_MATCH_PREFIX, ""]
            emitted = 0
            seen_signatures: set[str] = set()
            for _total, _max_score, _header, lines, _line_scores in scored:
                if emitted >= _MAX_OVERVIEW_LINES:
                    break
                for line in lines:
                    if emitted >= _MAX_OVERVIEW_LINES:
                        break
                    clean = _strip_markdown(line)
                    signature = _record_signature(clean)
                    if signature:
                        if signature in seen_signatures:
                            continue
                        seen_signatures.add(signature)
                    emitted += 1
                    response_parts.append(f"{emitted}. {self._format_line(clean)}")
            response_parts += ["", _FOOTER_MESSAGE]
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

        ranked_answer = self._build_ranked_answer(message, kept)
        if ranked_answer:
            yield ranked_answer
            return

        response_parts: list[str] = ["Here are the matching Saksha database records:", ""]

        emitted = 0
        seen_signatures: set[str] = set()
        for _, _, _header, lines, line_scores in kept:
            if emitted >= _MAX_CONTEXT_LINES:
                break
            ranked = sorted(zip(lines, line_scores), key=lambda pair: -pair[1])
            for line, _score in ranked:
                if emitted >= _MAX_CONTEXT_LINES:
                    break
                clean = _strip_markdown(line)
                signature = _record_signature(clean)
                if signature:
                    if signature in seen_signatures:
                        continue  # same record already listed from another source
                    seen_signatures.add(signature)
                emitted += 1
                response_parts.append(f"{emitted}. {self._format_line(clean)}")

        response_parts.append("")
        response_parts.append(_FOOTER_MESSAGE)

        full_response = "\n".join(response_parts).strip()

        for chunk in self._stream_text(full_response):
            yield chunk

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


