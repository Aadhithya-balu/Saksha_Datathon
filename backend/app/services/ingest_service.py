"""Legacy data ingestion service — bulk CSV/XLSX import with column mapping and validation.

Closes gap M1 (legacy Excel/CSV records migration) and M2 (CCTNS interoperability)
of the Saksha gap-closure issue. Supports:

- ``standard`` profile  : Saksha-native column templates (downloadable).
- ``cctns`` profile     : maps Crime and Criminal Tracking Network & Systems
                          (CCTNS) extract column headers onto Saksha entities,
                          so state CCTNS dumps can be ingested without manual
                          re-keying. See CCTNS_ICJS_INTEROP.md at the repo root.

Pipeline: parse file -> auto-map headers (profile-aware) -> validate every row
-> report errors/warnings -> optionally persist valid rows.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Column templates per entity (standard Saksha profile).
# Each field spec: column name -> {required, type, choices}
# ---------------------------------------------------------------------------

def _spec(required: bool = False, ftype: str = "string", choices: list[str] | None = None) -> dict[str, Any]:
    return {"required": required, "type": ftype, "choices": choices}


ENTITY_SPECS: dict[str, dict[str, dict[str, Any]]] = {
    "victims": {
        "full_name": _spec(required=True),
        "gender": _spec(choices=["Male", "Female", "Other"]),
        "age": _spec(ftype="integer"),
        "contact_number": _spec(),
        "address": _spec(),
        "statement": _spec(),
    },
    "criminals": {
        "full_name": _spec(required=True),
        "aliases": _spec(),
        "date_of_birth": _spec(ftype="date"),
        "gender": _spec(choices=["Male", "Female", "Other"]),
        "address": _spec(),
        "identifying_marks": _spec(),
        "mo_summary": _spec(),
        "status": _spec(choices=["at_large", "arrested", "convicted", "deceased"]),
    },
    "crime_cases": {
        "case_number": _spec(required=True),
        "category_name": _spec(required=True),
        "district": _spec(required=True),
        "station": _spec(),
        "occurred_at": _spec(required=True, ftype="datetime"),
        "description": _spec(),
        "mo_tags": _spec(),
        "status": _spec(choices=["open", "under_investigation", "closed", "convicted"]),
        "priority": _spec(choices=["low", "medium", "high", "critical"]),
        "progress": _spec(ftype="integer"),
    },
}

# ---------------------------------------------------------------------------
# M2: CCTNS extract header mapping. Keys are common CCTNS/ICJS column names
# (upper-snake, as produced by CCTNS "Search Arrested Person" / "Crime Details"
# exports); values map to the standard Saksha columns above. Unmapped CCTNS
# headers are reported as ignored so nothing is silently dropped.
# ---------------------------------------------------------------------------

CCTNS_COLUMN_MAPS: dict[str, dict[str, str]] = {
    "victims": {
        "NAME_OF_VICTIM": "full_name",
        "VICTIM_NAME": "full_name",
        "GENDER": "gender",
        "AGE": "age",
        "MOBILE_NUMBER": "contact_number",
        "CONTACT_NO": "contact_number",
        "ADDRESS": "address",
        "STATEMENT_DETAILS": "statement",
        "STATEMENT": "statement",
    },
    "criminals": {
        "ARRESTED_PERSON_NAME": "full_name",
        "PERSON_NAME": "full_name",
        "ACCUSED_NAME": "full_name",
        "ALIAS_NAME": "aliases",
        "ALIASES": "aliases",
        "DATE_OF_BIRTH": "date_of_birth",
        "DOB": "date_of_birth",
        "GENDER": "gender",
        "ADDRESS": "address",
        "IDENTIFICATION_MARKS": "identifying_marks",
        "MODUS_OPERANDI": "mo_summary",
        "MO_DETAILS": "mo_summary",
        "ARREST_STATUS": "status",
        "PERSON_STATUS": "status",
    },
    "crime_cases": {
        "REGISTRATION_NO": "case_number",
        "FIR_NO": "case_number",
        "CRIME_HEAD": "category_name",
        "IPC_SECTIONS": "category_name",
        "BNS_SECTIONS": "category_name",
        "DISTRICT_NAME": "district",
        "DISTRICT_CD": "district",
        "POLICE_STATION": "station",
        "PS_NAME": "station",
        "DATE_OF_REGISTRATION": "occurred_at",
        "INCIDENT_DATE": "occurred_at",
        "COMPLAINT_DETAILS": "description",
        "GENERAL_REMARKS": "description",
        "FIR_STATUS": "status",
        "CASE_STATUS": "status",
    },
}

VALID_IMPORT_ENTITIES = sorted(ENTITY_SPECS.keys())
VALID_PROFILES = ("standard", "cctns")

MAX_ROWS = 5000


class IngestError(Exception):
    """Raised when a file cannot be parsed at all."""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_tabular_file(content: bytes, filename: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Parse an uploaded CSV or XLSX file into (headers, row dicts).

    Rows are returned keyed by their original (stripped) header names; empty
    fully-blank rows are skipped.
    """
    lower = filename.lower()
    if lower.endswith((".xlsx", ".xls")):
        return _parse_xlsx(content)
    return _parse_csv(content)


def _parse_csv(content: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows_raw = [row for row in reader if any((cell or "").strip() for cell in row)]
    if not rows_raw:
        raise IngestError("File contains no data rows")
    headers = [h.strip() for h in rows_raw[0]]
    parsed: list[dict[str, Any]] = []
    for raw in rows_raw[1:]:
        row: dict[str, Any] = {}
        for idx, header in enumerate(headers):
            if not header:
                continue
            row[header] = (raw[idx].strip() if idx < len(raw) else "")
        parsed.append(row)
    return headers, parsed


def _parse_xlsx(content: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - openpyxl is in requirements
        raise IngestError("Excel support is not installed (openpyxl missing)") from exc
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise IngestError(f"Could not read Excel file: {exc}") from exc
    sheet = workbook.active
    if sheet is None:
        raise IngestError("Excel workbook has no active sheet")
    matrix = [list(row) for row in sheet.iter_rows(values_only=True)]
    workbook.close()
    # Trim to contiguous non-empty region and normalize cells to strings.
    matrix = [row for row in matrix if any(cell is not None and str(cell).strip() for cell in row)]
    if not matrix:
        raise IngestError("Excel sheet contains no data rows")
    headers = [str(c).strip() if c is not None else "" for c in matrix[0]]
    parsed: list[dict[str, Any]] = []
    for raw in matrix[1:]:
        row = {}
        for idx, header in enumerate(headers):
            if not header:
                continue
            cell = raw[idx] if idx < len(raw) else None
            row[header] = "" if cell is None else str(cell).strip()
        parsed.append(row)
    return headers, parsed


# ---------------------------------------------------------------------------
# Header mapping (profile-aware, with fuzzy fallback)
# ---------------------------------------------------------------------------

def _normalize_header(header: str) -> str:
    return "".join(ch for ch in header.lower().replace(" ", "_") if ch.isalnum() or ch == "_").strip("_")


def build_column_mapping(headers: list[str], entity_type: str, profile: str) -> tuple[dict[str, str], list[str]]:
    """Map uploaded headers -> standard entity columns.

    Returns ``(mapping, unmapped_headers)`` where *mapping* keys are uploaded
    headers and values are standard column names. Unknown headers are listed
    in *unmapped_headers* so operators see what was skipped.
    """
    spec_columns = set(ENTITY_SPECS[entity_type].keys())
    normalized_targets = {_normalize_header(col): col for col in spec_columns}
    profile_map = {}
    if profile == "cctns":
        profile_map = {k.upper(): v for k, v in CCTNS_COLUMN_MAPS.get(entity_type, {}).items()}

    mapping: dict[str, str] = {}
    unmapped: list[str] = []
    for header in headers:
        if not header:
            continue
        if header in profile_map and profile_map[header] in spec_columns:
            mapping[header] = profile_map[header]
            continue
        normalized = _normalize_header(header)
        upper = header.upper()
        if upper in profile_map and profile_map[upper] in spec_columns:
            mapping[header] = profile_map[upper]
            continue
        if normalized in normalized_targets:
            mapping[header] = normalized_targets[normalized]
        else:
            unmapped.append(header)
    return mapping, unmapped


# ---------------------------------------------------------------------------
# Validation + coercion
# ---------------------------------------------------------------------------

def _coerce_value(raw: Any, ftype: str) -> tuple[Any, str | None]:
    value = ("" if raw is None else str(raw)).strip()
    if not value:
        return None, None
    if ftype == "integer":
        try:
            return int(float(value)), None
        except ValueError:
            return None, f"'{value}' is not a valid integer"
    if ftype == "date":
        parsed = _parse_date(value)
        if parsed is None:
            return None, f"'{value}' is not a recognizable date (use YYYY-MM-DD)"
        return parsed, None
    if ftype == "datetime":
        parsed = _parse_datetime(value)
        if parsed is None:
            return None, f"'{value}' is not a recognizable datetime (use YYYY-MM-DD HH:MM)"
        return parsed, None
    return value, None


def _parse_date(value: str) -> date | None:
    candidates = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d")
    for fmt in candidates:
        try:
            return datetime.strptime(value.split(" ")[0], fmt).date()
        except ValueError:
            continue
    return None


def _parse_datetime(value: str) -> datetime | None:
    candidates = (
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
        "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d",
    )
    for fmt in candidates:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    parsed_date = _parse_date(value)
    if parsed_date:
        return datetime(parsed_date.year, parsed_date.month, parsed_date.day)
    return None


def validate_row(
    db: Session,
    entity_type: str,
    standard_row: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Validate one mapped row. Returns (clean_values, errors, warnings)."""
    spec = ENTITY_SPECS[entity_type]
    clean: dict[str, Any] = {}
    errors: list[str] = []
    warnings: list[str] = []

    for column, rules in spec.items():
        raw = standard_row.get(column)
        coerced, err = _coerce_value(raw, rules["type"])
        if err:
            errors.append(f"{column}: {err}")
            continue
        if coerced is None and rules["required"]:
            errors.append(f"{column}: required field is missing")
            continue
        if coerced is not None and rules.get("choices"):
            normalized = str(coerced).strip().lower()
            if normalized in rules["choices"]:
                coerced = normalized
            elif str(coerced) in rules["choices"]:
                pass
            else:
                errors.append(f"{column}: '{coerced}' must be one of {', '.join(rules['choices'])}")
                continue
        clean[column] = coerced

    # Entity-specific relational validation. Always runs so reports surface
    # every problem per row, not just the first failure class.
    if entity_type == "crime_cases":
        category_name = clean.get("category_name")
        district = clean.get("district")
        station = clean.get("station")
        if category_name:
            from app.models.crime_category import CrimeCategory
            found = _match_category(db, CrimeCategory, category_name)
            if found:
                clean["category_id"] = found
            else:
                known = ", ".join(r[0] for r in db.query(CrimeCategory.name).limit(12).all())
                errors.append(f"category_name: '{category_name}' not found (known: {known})")
        if district:
            from app.services.sociological_service import KARNATAKA_DISTRICTS
            matched = _match_district(district)
            if matched:
                clean["district"] = matched
            elif district not in KARNATAKA_DISTRICTS:
                warnings.append(f"district '{district}' is not a recognised Karnataka reference district")
        if station and district:
            from app.models.location import Location
            query = db.query(Location).filter(Location.district == clean.get("district", district))
            location = query.filter(Location.station.ilike(station.strip())).first() or query.first()
            if location:
                clean["location_id"] = location.id
                clean.pop("station", None)
                clean.pop("district", None)
            else:
                errors.append(f"station: no location found for '{station}' in district '{district}'")

    # Duplicate detection (warnings only — do not block legacy re-registrations).
    if entity_type == "crime_cases" and clean.get("case_number"):
        from app.models.crime import CrimeCase
        exists = db.query(CrimeCase.id).filter(CrimeCase.case_number == clean["case_number"]).first()
        if exists:
            errors.append(f"case_number: '{clean['case_number']}' already exists (duplicate)")
    if entity_type == "criminals" and clean.get("full_name"):
        from app.models.criminal import Criminal
        exists = db.query(Criminal.id).filter(Criminal.full_name.ilike(clean["full_name"])).first()
        if exists:
            warnings.append(f"a criminal named '{clean['full_name']}' already exists; review for duplicates")

    return clean, errors, warnings


def _match_category(db: Session, CrimeCategory, raw: str) -> Any | None:
    """Resolve a category name tolerantly (case, '&' vs 'and', spacing)."""
    normalized = " ".join(raw.lower().replace("&", "and").split())
    for category in db.query(CrimeCategory).all():
        if category.name.strip().lower() == raw.strip().lower():
            return category.id
        candidate_norm = " ".join(category.name.lower().replace("&", "and").split())
        if candidate_norm == normalized:
            return category.id
    return None


_DISTRICT_ALIASES = {
    "bengaluru": "Bengaluru Urban",
    "bangalore": "Bengaluru Urban",
    "bengaluru urban": "Bengaluru Urban",
    "bangalore urban": "Bengaluru Urban",
    "mangalore": "Mangaluru",
    "dakshina kannada": "Mangaluru",
    "bellary": "Ballari",
    "gulbarga": "Kalaburagi",
    "kalaburagi": "Kalaburagi",
    "tumkur": "Tumkuru",
    "tumakuru": "Tumkuru",
    "hubli-dharwad": "Dharwad",
    "dharwad": "Dharwad",
}


def _match_district(raw: str) -> str | None:
    """Resolve a district string against known Karnataka districts + aliases."""
    from app.services.sociological_service import KARNATAKA_DISTRICTS
    needle = raw.strip().lower()
    if needle in _DISTRICT_ALIASES:
        candidate = _DISTRICT_ALIASES[needle]
        return candidate if candidate in KARNATAKA_DISTRICTS else None
    for name in KARNATAKA_DISTRICTS:
        if name.lower() == needle:
            return name
    return None


# ---------------------------------------------------------------------------
# High-level operations used by routes
# ---------------------------------------------------------------------------

def analyze_upload(
    db: Session,
    content: bytes,
    filename: str,
    entity_type: str,
    profile: str = "standard",
    limit_report_rows: int = 50,
) -> dict[str, Any]:
    """Parse + map + validate an upload WITHOUT writing anything.

    Returns the full preview payload: detected headers, proposed mapping,
    unmapped headers, sample mapped rows, and the validation report.
    """
    if entity_type not in ENTITY_SPECS:
        raise IngestError(f"Unsupported entity type '{entity_type}'")
    if profile not in VALID_PROFILES:
        raise IngestError(f"Unsupported mapping profile '{profile}'")

    headers, parsed_rows = parse_tabular_file(content, filename)
    if len(parsed_rows) > MAX_ROWS:
        raise IngestError(f"File has {len(parsed_rows)} rows; maximum supported is {MAX_ROWS}")

    mapping, unmapped = build_column_mapping(headers, entity_type, profile)
    missing_required = [
        col for col, rules in ENTITY_SPECS[entity_type].items() if rules["required"] and col not in mapping.values()
    ]

    report: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    valid_count = 0
    for index, raw_row in enumerate(parsed_rows, start=2):  # +1 header line, +1 for 1-based
        standard_row = {mapping[h]: v for h, v in raw_row.items() if h in mapping}
        _, errors, warnings = validate_row(db, entity_type, standard_row)
        if not errors:
            valid_count += 1
        if len(report) < limit_report_rows and (errors or warnings):
            report.append({"row_number": index, "errors": errors, "warnings": warnings})
        if len(samples) < 5:
            samples.append(standard_row)

    error_count = sum(1 for item in report for e in item["errors"])  # only counted within sampled slice
    return {
        "entity_type": entity_type,
        "profile": profile,
        "filename": filename,
        "detected_headers": headers,
        "column_mapping": mapping,
        "unmapped_headers": unmapped,
        "missing_required_columns": missing_required,
        "total_rows": len(parsed_rows),
        "sample_mapped_rows": samples,
        "validation_report": report,
        "truncated_report": max(0, len(parsed_rows) - len(report)) > 0,
        "estimated_valid_rows": valid_count,
        "estimated_invalid_rows": len(parsed_rows) - valid_count,
        "_diagnostic_error_sample_count": error_count,
    }


def commit_import(
    db: Session,
    content: bytes,
    filename: str,
    entity_type: str,
    profile: str,
    created_by_id,
) -> dict[str, Any]:
    """Validate then persist all valid rows. Returns the final import report."""
    preview = analyze_upload(db, content, filename, entity_type, profile, limit_report_rows=10**9)

    if entity_type == "victims":
        from app.models.victim import Victim as model
    elif entity_type == "criminals":
        from app.models.criminal import Criminal as model
    else:
        from app.models.crime import CrimeCase as model

    headers, parsed_rows = parse_tabular_file(content, filename)
    mapping, _unmapped = build_column_mapping(headers, entity_type, profile)

    # Virtual columns used for lookup/validation; never passed to the ORM.
    _VIRTUAL_COLUMNS = {"category_name", "district", "station"}

    imported = 0
    full_report: list[dict[str, Any]] = []
    for index, raw_row in enumerate(parsed_rows, start=2):
        standard_row = {mapping[h]: v for h, v in raw_row.items() if h in mapping}
        clean, errors, warnings = validate_row(db, entity_type, standard_row)
        if errors:
            full_report.append({"row_number": index, "errors": errors, "warnings": warnings})
            continue
        if entity_type == "crime_cases":
            clean.setdefault("status", "open")
            clean.setdefault("priority", "medium")
            clean.setdefault("progress", 10)
            clean = {k: v for k, v in clean.items() if k not in _VIRTUAL_COLUMNS}
        obj = model(**{k: v for k, v in clean.items()})
        db.add(obj)
        imported += 1
        if warnings:
            full_report.append({"row_number": index, "errors": [], "warnings": warnings})

    failed = len(parsed_rows) - imported
    status = "completed" if failed == 0 else ("partial" if imported > 0 else "failed")

    job_record = {
        "entity_type": entity_type,
        "source_format": "xlsx" if filename.lower().endswith((".xlsx", ".xls")) else "csv",
        "mapping_profile": profile,
        "filename": filename,
        "total_rows": len(parsed_rows),
        "imported_rows": imported,
        "failed_rows": failed,
        "status": status,
        "validation_report": json.dumps(full_report[:200]),
        "created_by_id": created_by_id,
    }
    return {"job": job_record, "report": full_report, "preview": preview}


def build_template(entity_type: str, export_format: str = "csv") -> tuple[bytes, str, str]:
    """Build a downloadable import template. Returns (bytes, media_type, extension)."""
    columns = list(ENTITY_SPECS[entity_type].keys())
    example_rows = _TEMPLATE_EXAMPLES.get(entity_type, [])
    if export_format == "xlsx":
        from openpyxl import Workbook
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(columns)
        for row in example_rows:
            sheet.append([row.get(c, "") for c in columns])
        buffer = io.BytesIO()
        workbook.save(buffer)
        return (
            buffer.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xlsx",
        )
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for row in example_rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    return buffer.getvalue().encode("utf-8"), "text/csv; charset=utf-8", "csv"


_TEMPLATE_EXAMPLES: dict[str, list[dict[str, str]]] = {
    "victims": [
        {
            "full_name": "Suresh Gowda",
            "gender": "Male",
            "age": "34",
            "contact_number": "9880012345",
            "address": "12, 4th Cross, KR Puram, Bengaluru Urban",
            "statement": "Two men snatched his bag near the bus stand at 21:30.",
        },
        {
            "full_name": "Lakshmi Rao",
            "gender": "Female",
            "age": "67",
            "contact_number": "",
            "address": "Hassan town",
            "statement": "",
        },
    ],
    "criminals": [
        {
            "full_name": "Ravi alias Kulla",
            "aliases": "Kulla, Ravi M",
            "date_of_birth": "1992-05-14",
            "gender": "Male",
            "address": "Ballari",
            "identifying_marks": "Scar over left eyebrow",
            "mo_summary": "Targets unlocked two-wheelers at night; uses stolen vehicles KA-35-AB-1234.",
            "status": "at_large",
        },
    ],
    "crime_cases": [
        {
            "case_number": "CR-2026-9001",
            "category_name": "Theft & Burglaries",
            "district": "Bengaluru Urban",
            "station": "KR Puram",
            "occurred_at": "2026-07-14 22:30",
            "description": "Housebreak at night; gold ornaments stolen.",
            "mo_tags": "night_entry,locked_house",
            "status": "open",
            "priority": "high",
            "progress": "25",
        },
    ],
}
