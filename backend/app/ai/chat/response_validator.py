"""Response validator — ensures LLM output is grounded in retrieved backend data."""
from __future__ import annotations

import re

from app.ai.chat.backend_fetcher import BackendResult


class ResponseValidator:
    """Validates that factual claims in the response originate from backend data."""

    _ID_PATTERNS = [
        re.compile(r"CR-\d{4}-[A-Z]{2,4}-\d+"),
        re.compile(r"FIR\s*\d{4}/\d+"),
        re.compile(r"\d{4}/\d{3,}"),
    ]

    def validate(self, response: str, results: list[BackendResult]) -> str:
        if not results:
            return response

        successful = [r for r in results if r.success and r.content.strip()]
        if not successful:
            return response

        known_ids = self._collect_known_ids(successful)
        response_ids = self._extract_response_ids(response)

        unverified_ids = [rid for rid in response_ids if not self._id_in_known(rid, known_ids)]

        if unverified_ids and known_ids:
            disclaimer = (
                "\n\n> Note: Some identifiers in this response could not be verified "
                "against current Saksha database records."
            )
            response = response.rstrip() + disclaimer

        return response

    def _collect_known_names(self, results: list[BackendResult]) -> set[str]:
        names: set[str] = set()
        for r in results:
            if not r.raw_data:
                continue
            raw = r.raw_data
            if isinstance(raw, dict):
                for key in ("name", "full_name", "complainant_name", "leader_name"):
                    val = raw.get(key)
                    if isinstance(val, str):
                        names.add(val.lower())
                for key in ("names", "members"):
                    val = raw.get(key)
                    if isinstance(val, list):
                        for item in val:
                            if isinstance(item, str):
                                names.add(item.lower())
                            elif isinstance(item, dict):
                                for sub in ("name", "full_name"):
                                    if sub in item:
                                        names.add(str(item[sub]).lower())
            elif isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict):
                        for key in ("name", "full_name"):
                            if key in item:
                                names.add(str(item[key]).lower())
        return names

    def _collect_known_ids(self, results: list[BackendResult]) -> set[str]:
        ids: set[str] = set()
        for r in results:
            if not r.raw_data:
                continue
            raw = r.raw_data
            if isinstance(raw, dict):
                for key in ("case_number", "fir_number", "id"):
                    val = raw.get(key)
                    if isinstance(val, str):
                        ids.add(val)
                for val in raw.values():
                    if isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict):
                                for sub_key in ("case_number", "fir_number", "id"):
                                    if sub_key in item:
                                        ids.add(str(item[sub_key]))
            elif isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict):
                        for key in ("case_number", "fir_number", "id"):
                            if key in item:
                                ids.add(str(item[key]))
        return ids

    def _extract_response_ids(self, response: str) -> list[str]:
        found: list[str] = []
        for pattern in self._ID_PATTERNS:
            for match in pattern.finditer(response):
                found.append(match.group(0))
        return found

    def _id_in_known(self, response_id: str, known_ids: set[str]) -> bool:
        clean = response_id.replace(" ", "").lower()
        for kid in known_ids:
            if clean in kid.lower() or kid.lower() in clean:
                return True
        return False

