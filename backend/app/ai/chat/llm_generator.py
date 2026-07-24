"""LLM generator — calls external LLM APIs or falls back to local template generation."""
from __future__ import annotations

import json
import re
from typing import Any, AsyncIterator

import httpx

from app.core.config import settings


class LLMGenerator:
    """Generates responses using an external LLM or a local template fallback."""

    def __init__(self) -> None:
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.gemini_key = settings.GEMINI_API_KEY
        self.openai_key = settings.OPENAI_API_KEY

    async def generate(
        self,
        message: str,
        context_block: str,
        system_prompt: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        if self.provider == "gemini" and self.gemini_key:
            async for chunk in self._generate_gemini(message, context_block, system_prompt, history):
                yield chunk
            return
        if self.provider == "openai" and self.openai_key:
            async for chunk in self._generate_openai(message, context_block, system_prompt, history):
                yield chunk
            return
        async for chunk in self._generate_local(message, context_block, system_prompt):
            yield chunk

    async def _generate_gemini(
        self, message: str, context: str, system: str, history: list[dict[str, str]] | None,
    ) -> AsyncIterator[str]:
        contents = []
        if history:
            for msg in history[-10:]:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
        full_user_msg = f"{system}\n\n--- RETRIEVED CONTEXT ---\n{context}\n--- END CONTEXT ---\n\nUser Question: {message}"
        contents.append({"role": "user", "parts": [{"text": full_user_msg}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:streamGenerateContent?alt=sse&key={self.gemini_key}"
        payload = {"contents": contents, "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload) as response:
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
        except Exception:
            async for chunk in self._generate_local(message, context, system):
                yield chunk

    async def _generate_openai(
        self, message: str, context: str, system: str, history: list[dict[str, str]] | None,
    ) -> AsyncIterator[str]:
        messages = [{"role": "system", "content": system + "\n\n--- RETRIEVED CONTEXT ---\n" + context + "\n--- END CONTEXT ---"}]
        if history:
            for msg in history[-10:]:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": message})

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages, "stream": True, "temperature": 0.3, "max_tokens": 2048}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
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
        except Exception:
            async for chunk in self._generate_local(message, context, system):
                yield chunk

    async def _generate_local(
        self, message: str, context: str, system: str,
    ) -> AsyncIterator[str]:
        if "No relevant data" in context or "not found" in context.lower():
            yield ("I could not find matching records in the Saksha database for that query. "
                   "Please try rephrasing your question or check the case/FIR number.")
            return

        response_parts: list[str] = []

        has_case = any(kw in context.lower() for kw in ["case:", "case number", "crime_cases"])
        has_criminal = any(kw in context.lower() for kw in ["criminal", "full_name", "aliases", "mo:", "offender"])
        has_fir = any(kw in context.lower() for kw in ["fir number", "complainant", "sections:"])
        has_officer = any(kw in context.lower() for kw in ["officer:", "badge:", "rank:"])
        has_stats = any(kw in context.lower() for kw in ["total crimes", "crimes.", "cases.", "resolution"])
        has_network = any(kw in context.lower() for kw in ["network", "nodes", "edges", "gang"])
        has_hotspot = any(kw in context.lower() for kw in ["hotspot", "score=", "zone"])

        if has_case:
            response_parts.append("# Case Intelligence Report\n")
        elif has_criminal:
            response_parts.append("# Suspect Profile Dossier\n")
        elif has_fir:
            response_parts.append("# FIR Intelligence Brief\n")
        elif has_officer:
            response_parts.append("# Officer Profile\n")
        elif has_network:
            response_parts.append("# Network Intelligence Report\n")
        elif has_stats:
            response_parts.append("# Crime Intelligence Summary\n")
        elif has_hotspot:
            response_parts.append("# Hotspot Analysis Report\n")
        else:
            response_parts.append("## Saksha Intelligence Response\n")

        raw_lines = context.split("\n")
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("### "):
                header = line[4:].strip()
                response_parts.append(f"## {header}\n")
                continue

            if "|" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    formatted_items = []
                    for p in parts:
                        if ":" in p and not p.startswith("**"):
                            key, val = p.split(":", 1)
                            formatted_items.append(f"**{key.strip()}**: {val.strip()}")
                        else:
                            formatted_items.append(p)
                    response_parts.append("- " + " · ".join(formatted_items))
                else:
                    response_parts.append(f"- {parts[0] if parts else line}")
            elif ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                if key.lower() in ("name", "case", "status", "priority", "category", "location",
                                    "fir number", "complainant", "sections", "narrative",
                                    "officer", "badge", "rank", "station", "district",
                                    "description", "mo tags", "mo", "aliases", "gender",
                                    "address", "marks", "progress", "risk", "gang"):
                    response_parts.append(f"- **{key}**: {val}")
                else:
                    response_parts.append(f"- **{key}**: {val}")
            elif line.startswith("- ") or line.startswith("* "):
                response_parts.append(line)
            elif line.startswith("Node:") or line.startswith("Link:"):
                response_parts.append(f"- `{line}`")
            else:
                response_parts.append(f"- {line}")

        if has_case or has_criminal or has_fir or has_officer:
            response_parts.append("")
            response_parts.append("---")
            response_parts.append("")
            response_parts.append("*Source: Saksha Database. Verify details against official records before taking action.*")

        full_response = "\n".join(response_parts).strip()

        words = full_response.split()
        chunk_size = max(5, len(words) // 30)
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            if i + chunk_size < len(words):
                chunk += " "
            yield chunk
