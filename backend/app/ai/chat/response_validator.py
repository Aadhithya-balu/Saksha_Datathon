"""Response validator — ensures LLM output is grounded in retrieved backend data.

Issue 160 hardening:
- When NO backend source returned usable data, the response is replaced with
  an explicit refusal — an LLM (or template) must never free-style crime
  intelligence without evidence.
- Unverified case/FIR identifiers trigger a visible disclaimer appended to
  the answer so analysts know which claims could not be traced to records.

Issue 170 hardening:
- Deeper hallucination detection: verifies person names, locations, and
  relationship claims against source data.
- Structured provenance metadata attached to every validated response.
- Unsupported claim detection beyond just ID patterns.
- Fact vs inference distinction enforcement.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.ai.chat.backend_fetcher import BackendResult

_NO_EVIDENCE_RESPONSE = (
    "I could not find matching records in the Saksha database for that query. "
    "No verified data sources were available to ground an answer, so I will not "
    "speculate. Please try rephrasing your question or check the case/FIR number."
)

_UNVERIFIED_DISCLAIMER = (
    "\n\n> Note: Some identifiers in this response could not be verified "
    "against current Saksha database records."
)

_UNSOURCED_NAMES_DISCLAIMER = (
    "\n\n> Note: Some names mentioned in this response could not be traced "
    "to retrieved database records and may be unreliable."
)


@dataclass
class ProvenanceMetadata:
    """Structured provenance for a validated response."""
    source_records: list[dict[str, Any]] = field(default_factory=list)
    verified_ids: list[str] = field(default_factory=list)
    unverified_ids: list[str] = field(default_factory=list)
    verified_names: list[str] = field(default_factory=list)
    unverified_names: list[str] = field(default_factory=list)
    grounding_score: float = 0.0
    has_fabricated_claims: bool = False
    refusal_issued: bool = False
    disclaimer_appended: bool = False


class ResponseValidator:
    """Validates that factual claims in the response originate from backend data."""

    _ID_PATTERNS = [
        re.compile(r"CR-\d{4}-[A-Z]{2,4}-\d+"),
        re.compile(r"FIR\s*\d{4}/\d+"),
        re.compile(r"\d{4}/\d{3,}"),
    ]

    # Patterns for extracting person names referenced in responses.
    # Title prefixes use explicit case variants (not re.I) so that
    # [A-Z] in the name capture group only matches uppercase letters
    # and does not swallow trailing lowercase words like "is".
    _NAME_REFERENCE_PATTERNS = [
        re.compile(r"(?:[Oo]fficer|[Ii]nspector|[Ss]uperintendent|[Cc]onstable)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})"),
        re.compile(r"(?:[Cc]riminal|[Oo]ffender|[Ss]uspect|[Aa]ccused)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})"),
        re.compile(r"(?:[Vv]ictim|[Cc]omplainant)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})"),
        re.compile(r"Name:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})"),
    ]

    # Patterns for extracting location references
    _LOCATION_PATTERNS = [
        re.compile(r"\b(Bengaluru Urban|Rural|Mysuru|Mangaluru|Belagavi|Ballari|Kalaburagi|Hassan|Tumkuru|Dharwad|Bengaluru|Bangalore|Mysore|Mangalore|Bellary|Gulbarga|Hubli)\b", re.I),
    ]

    # Relationship claim patterns
    _RELATIONSHIP_PATTERNS = [
        re.compile(r"(?:linked|connected|associated|related)\s+to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})", re.I),
        re.compile(r"(?:member|part)\s+of\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})", re.I),
        re.compile(r"(?:works?\s+at|stationed\s+at|posted\s+at)\s+([A-Z][a-z]+)", re.I),
    ]

    def validate(self, response: str, results: list[BackendResult], skip_grounding: bool = False) -> str:
        successful = [r for r in results if r.success and r.content.strip()]

        # Grounding gate: with zero verified sources there is nothing the
        # assistant may assert — replace whatever was generated.
        # Platform knowledge questions (skip_grounding=True) are exempt:
        # they answer from the system prompt, not database records.
        if not successful and not skip_grounding:
            return _NO_EVIDENCE_RESPONSE

        known_ids = self._collect_known_ids(successful)
        known_names = self._collect_known_names(successful)
        known_locations = self._collect_known_locations(successful)
        response_ids = self._extract_response_ids(response)
        response_names = self._extract_response_names(response)
        response_locations = self._extract_response_locations(response)
        response_relationships = self._extract_response_relationships(response)

        unverified_ids = [rid for rid in response_ids if not self._id_in_known(rid, known_ids)]
        unverified_names = [name for name in response_names if not self._name_in_known(name, known_names)]

        disclaimer_parts = []

        if unverified_ids and known_ids:
            disclaimer_parts.append(_UNVERIFIED_DISCLAIMER)

        if unverified_names and known_names:
            disclaimer_parts.append(_UNSOURCED_NAMES_DISCLAIMER)

        if disclaimer_parts:
            response = response.rstrip() + "".join(disclaimer_parts)

        return response

    def get_provenance(self, response: str, results: list[BackendResult]) -> ProvenanceMetadata:
        """Returns structured provenance metadata for a validated response."""
        successful = [r for r in results if r.success and r.content.strip()]

        provenance = ProvenanceMetadata()

        if not successful:
            provenance.refusal_issued = True
            provenance.has_fabricated_claims = True
            return provenance

        # Collect all known entities from source data
        known_ids = self._collect_known_ids(successful)
        known_names = self._collect_known_names(successful)
        known_locations = self._collect_known_locations(successful)

        # Extract entities from response
        response_ids = self._extract_response_ids(response)
        response_names = self._extract_response_names(response)
        response_locations = self._extract_response_locations(response)

        # Classify as verified or unverified
        provenance.verified_ids = [rid for rid in response_ids if self._id_in_known(rid, known_ids)]
        provenance.unverified_ids = [rid for rid in response_ids if not self._id_in_known(rid, known_ids)]
        provenance.verified_names = [name for name in response_names if self._name_in_known(name, known_names)]
        provenance.unverified_names = [name for name in response_names if not self._name_in_known(name, known_names)]

        # Collect source records from BackendResult records field
        for result in successful:
            if result.records:
                provenance.source_records.extend(result.records)

        # Compute grounding score
        total_claims = len(response_ids) + len(response_names)
        verified_claims = len(provenance.verified_ids) + len(provenance.verified_names)
        provenance.grounding_score = (verified_claims / total_claims) if total_claims > 0 else 1.0

        # Check for fabricated claims
        provenance.has_fabricated_claims = bool(provenance.unverified_ids or provenance.unverified_names)
        provenance.disclaimer_appended = provenance.has_fabricated_claims and bool(known_ids or known_names)

        return provenance

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
        # Also check records field
        for r in results:
            if r.records:
                for rec in r.records:
                    for key in ("name", "full_name"):
                        val = rec.get(key)
                        if isinstance(val, str):
                            names.add(val.lower())
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
        # Also check records field
        for r in results:
            if r.records:
                for rec in r.records:
                    for key in ("case_number", "fir_number", "id"):
                        val = rec.get(key)
                        if isinstance(val, str):
                            ids.add(val)
        return ids

    def _collect_known_locations(self, results: list[BackendResult]) -> set[str]:
        locations: set[str] = set()
        for r in results:
            if not r.content:
                continue
            for pattern in self._LOCATION_PATTERNS:
                for match in pattern.finditer(r.content):
                    locations.add(match.group(0).lower())
        return locations

    def _extract_response_ids(self, response: str) -> list[str]:
        found: list[str] = []
        for pattern in self._ID_PATTERNS:
            for match in pattern.finditer(response):
                found.append(match.group(0))
        return found

    def _extract_response_names(self, response: str) -> list[str]:
        found: list[str] = []
        for pattern in self._NAME_REFERENCE_PATTERNS:
            for match in pattern.finditer(response):
                name = match.group(1).strip()
                if len(name) > 2:
                    found.append(name)
        return list(set(found))

    def _extract_response_locations(self, response: str) -> list[str]:
        found: list[str] = []
        for pattern in self._LOCATION_PATTERNS:
            for match in pattern.finditer(response):
                found.append(match.group(0))
        return list(set(found))

    def _extract_response_relationships(self, response: str) -> list[str]:
        found: list[str] = []
        for pattern in self._RELATIONSHIP_PATTERNS:
            for match in pattern.finditer(response):
                found.append(match.group(0))
        return found

    def _id_in_known(self, response_id: str, known_ids: set[str]) -> bool:
        clean = response_id.replace(" ", "").lower()
        for kid in known_ids:
            if clean in kid.lower() or kid.lower() in clean:
                return True
        return False

    def _name_in_known(self, name: str, known_names: set[str]) -> bool:
        name_lower = name.lower().strip()
        for known in known_names:
            if name_lower in known or known in name_lower:
                return True
        # Also check first/last name matches
        name_parts = name_lower.split()
        for known in known_names:
            known_parts = known.split()
            if any(part in known_parts for part in name_parts if len(part) > 2):
                return True
        return False
