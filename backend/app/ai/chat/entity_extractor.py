"""Structured entity extraction from user queries using regex and heuristics."""
from __future__ import annotations

import re
from dataclasses import dataclass


_KARNATAKA_DISTRICTS = [
    "Bengaluru Urban", "Bengaluru Rural", "Mysuru", "Mangaluru",
    "Belagavi", "Ballari", "Kalaburagi", "Hassan", "Tumkuru", "Dharwad",
    "Bengaluru", "Bangalore", "Mysore", "Mangalore", "Bellary",
    "Gulbarga", "Hubli",
]

_POLICE_STATIONS = [
    "Whitefield", "KR Puram", "Devaraja", "Mangaluru Harbor",
    "Belagavi City", "Ballari", "Kalaburagi", "Hassan", "Tumkuru",
    "Dharwad", "Indiranagar", "Jayanagar", "Koramangala", "HSR Layout",
    "Peenya", "Yelahanka", "Banashankari", "Vijayanagara",
]

_CRIME_CATEGORIES = [
    "Cyber Crime", "Theft", "Burglaries", "Narcotics", "Smuggling",
    "Assault", "Illegal Mining", "Domestic Violence", "Property Disputes",
    "Burglary", "Robbery", "Fraud", "Murder", "Kidnapping",
]

_DATE_RANGE_KEYWORDS = {
    "last week": 7, "past week": 7,
    "last month": 30, "past month": 30,
    "last year": 365, "past year": 365,
    "today": 0, "yesterday": 1,
    "this week": 7, "this month": 30, "this year": 365,
}


@dataclass
class ExtractedEntities:
    case_id: str | None = None
    fir_number: str | None = None
    person_name: str | None = None
    district: str | None = None
    station: str | None = None
    crime_category: str | None = None
    date: str | None = None
    date_range_days: int | None = None
    vehicle_number: str | None = None
    phone_number: str | None = None
    risk_level: str | None = None

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "case_id": self.case_id,
            "fir_number": self.fir_number,
            "person_name": self.person_name,
            "district": self.district,
            "station": self.station,
            "crime_category": self.crime_category,
            "date": self.date,
            "date_range_days": self.date_range_days,
            "vehicle_number": self.vehicle_number,
            "phone_number": self.phone_number,
            "risk_level": self.risk_level,
        }


def _fuzzy_match(text: str, candidates: list[str]) -> str | None:
    lower = text.lower()
    for candidate in candidates:
        if candidate.lower() in lower:
            return candidate
    return None


# Tokens that must never form part of an extracted person name.  Stopping at
# these prevents question tails ("What is his status?") or lead-in fillers
# ("the criminal") from polluting the captured name.
_NAME_STOP_WORDS = {
    "the", "a", "an", "of", "for", "on", "in", "at", "to", "with", "about",
    "who", "what", "when", "where", "how", "which", "why",
    "is", "are", "was", "were", "does", "do", "did", "has", "have", "had",
    "this", "that", "these", "those", "his", "her", "their", "its", "your", "our",
    "criminal", "criminals", "suspect", "suspects", "accused", "victim", "victims",
    "officer", "offender", "offenders", "case", "fir", "record", "records",
    "status", "detail", "details", "profile", "history", "background", "crime", "crimes",
    "connected", "linked", "involved", "involving", "regarding", "named", "called",
    "tell", "me", "show", "find", "search", "get", "list", "any", "all",
}


def _clean_candidate_name(raw: str) -> str | None:
    """Normalise a raw captured name fragment into a clean person name.

    Drops lead-in fillers, cuts at wh-question/verb tails and IDs, requires
    alphabetic name-like tokens, and caps the length at 3 words.
    """
    if not raw:
        return None
    kept: list[str] = []
    for token in re.split(r"\s+", raw.strip()):
        clean = token.rstrip(".,;:!?")
        if not clean:
            continue
        if re.match(r"CR-\d{4}-", clean, re.I) or clean.startswith("FIR"):
            continue
        if re.match(r"^\d", clean):
            continue
        if clean.lower() in _NAME_STOP_WORDS:
            if kept:
                break
            continue
        if not re.match(r"^[A-Za-z][A-Za-z.'\-]*$", clean):
            if kept:
                break
            continue
        if clean.endswith("'s") or clean.endswith("'S"):
            clean = clean[:-2]
        kept.append(clean)
        if len(kept) >= 3:
            break
    if not kept:
        return None
    return " ".join(kept)


class EntityExtractor:
    """Extracts structured entities from natural language crime queries."""

    _CASE_RE = re.compile(r"CR-\d{4}-[A-Z]{2,4}-\d+", re.I)
    # FIR identifiers come in several real formats in the Saksha database:
    #   FIR-045/BNG/2026    FIR-411/RANEBENNUR/2026   FIR-NXT-001/2026
    #   FIR 204/BLG/2026    FIR-789/MYS/2026         FIR 2026/104 (year/ordinal)
    _FIR_RE = re.compile(
        r"(?:FIR[-\s]*:?\s*)?"
        r"("
        r"[A-Z0-9]{1,16}(?:-[A-Z0-9]+)?"
        r"(?:/[A-Z0-9]{1,20}){1,2}"
        r")",
        re.I,
    )
    _FIR_PREFIX_RE = re.compile(r"\bFIR\b", re.I)
    _FIR_ORDINAL_RE = re.compile(
        r"\b(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\.?\s+fir\b", re.I,
    )
    _VEHICLE_RE = re.compile(r"\b(KA[\s-]?\d{2}[\s-]?[A-Z]{1,2}[\s-]?\d{4})\b", re.I)
    _PHONE_RE = re.compile(r"(\+91\s*\d{5}[\s-]\d{5}|\+91\s*\d{10}|\b\d{10}\b)")
    _DATE_DMY_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
    _DATE_YMD_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
    _NAME_AFTER_RE = re.compile(
        r"(?:of|named|accused|suspect|victim|officer|criminal|offender|"
        r"connected\s+to|who\s+is|about|for|regarding)\s+"
        r"([A-Z][A-Za-z.'-]*(?:\s+(?:[A-Z][A-Za-z.'-]*)){0,4})",
    )
    _RISK_RE = re.compile(
        r"\b(very\s+high|high\s+risk|medium\s+risk|low\s+risk|critical)\b", re.I,
    )

    def extract(self, message: str) -> ExtractedEntities:
        entities = ExtractedEntities()

        case_match = self._CASE_RE.search(message)
        if case_match:
            entities.case_id = case_match.group(0)

        fir_match = self._FIR_RE.search(message)
        if fir_match:
            entities.fir_number = fir_match.group(1)
        elif self._FIR_PREFIX_RE.search(message):
            bare_num = re.search(r"\bFIR\s+(\d+)\b", message, re.I)
            if bare_num:
                entities.fir_number = bare_num.group(1)
            else:
                ordinal = self._FIR_ORDINAL_RE.search(message)
                if ordinal:
                    entities.fir_number = f"ordinal:{ordinal.group(1)}"

        name_match = self._NAME_AFTER_RE.search(message)
        if name_match:
            entities.person_name = _clean_candidate_name(name_match.group(1))
        if not entities.person_name:
            entities.person_name = self._extract_name_heuristic(message)

        entities.district = _fuzzy_match(message, _KARNATAKA_DISTRICTS)
        entities.station = _fuzzy_match(message, _POLICE_STATIONS)
        entities.crime_category = _fuzzy_match(message, _CRIME_CATEGORIES)

        dmy = self._DATE_DMY_RE.search(message)
        if dmy:
            entities.date = dmy.group(1)
        ymd = self._DATE_YMD_RE.search(message)
        if ymd:
            entities.date = ymd.group(1)

        lower = message.lower()
        for keyword, days in _DATE_RANGE_KEYWORDS.items():
            if keyword in lower:
                entities.date_range_days = days
                break

        vehicle = self._VEHICLE_RE.search(message)
        if vehicle:
            entities.vehicle_number = vehicle.group(1).upper()

        phone = self._PHONE_RE.search(message)
        if phone:
            entities.phone_number = phone.group(1)

        risk = self._RISK_RE.search(message)
        if risk:
            entities.risk_level = risk.group(1).lower()

        return entities

    def _extract_name_heuristic(self, message: str) -> str | None:
        lower = message.lower()
        for keyword in [
            "who is ", "tell me about ", "details of ", "criminal ",
            "suspect ", "accused ", "victim ", "offender ", "named ",
            "regarding ", "about ", "of ",
        ]:
            idx = lower.find(keyword)
            if idx != -1:
                after = message[idx + len(keyword):].strip()
                candidate = _clean_candidate_name(after)
                if candidate:
                    return candidate
        return None
