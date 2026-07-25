"""Structured entity extraction from user queries using regex and heuristics."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


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


class EntityExtractor:
    """Extracts structured entities from natural language crime queries."""

    _CASE_RE = re.compile(r"CR-\d{4}-[A-Z]{2,4}-\d+", re.I)
    _FIR_RE = re.compile(r"(?:FIR[-\s]*)?(\d{3,4}/[A-Z]{0,4}/?\d{3,4})", re.I)
    _FIR_PREFIX_RE = re.compile(r"\bFIR\b", re.I)
    _VEHICLE_RE = re.compile(r"\b(KA[\s-]?\d{2}[\s-]?[A-Z]{1,2}[\s-]?\d{4})\b", re.I)
    _PHONE_RE = re.compile(r"(\+91\s*\d{5}[\s-]\d{5}|\+91\s*\d{10}|\b\d{10}\b)")
    _DATE_DMY_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
    _DATE_YMD_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
    _NAME_AFTER_RE = re.compile(
        r"(?:of|named|accused|suspect|victim|officer|connected\s+to|who\s+is|about|for)\s+"
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})",
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

        name_match = self._NAME_AFTER_RE.search(message)
        if name_match:
            entities.person_name = name_match.group(1)
        else:
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
        for keyword in ["who is ", "about ", "tell me about ", "details of "]:
            idx = lower.find(keyword)
            if idx != -1:
                after = message[idx + len(keyword):].strip()
                words = after.split()
                name_words = []
                for w in words:
                    if w and w[0].isupper() and len(w) > 1:
                        name_words.append(w)
                    elif name_words:
                        break
                if name_words:
                    candidate = " ".join(name_words[:4])
                    if re.match(r"CR-\d{4}-", candidate, re.I):
                        return None
                    if re.match(r"FIR\s*\d", candidate, re.I):
                        return None
                    return candidate
        return None
