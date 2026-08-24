# CCTNS / ICJS Interoperability Specification

**Saksha — Crime Intelligence & Analytical Platform**
Deliverable for issue #139 (M2): legacy data ingestion and CCTNS/ICJS interop.

This document specifies how Saksha ingests bulk legacy records and maps
CCTNS/ICJS extract headers onto its internal schema, so state-level data can be
brought into the platform without manual re-keying.

---

## 1. Scope

| Capability | Status |
|---|---|
| CSV upload (RFC-4180, comma/semicolon sniffing) | Implemented |
| XLSX upload (openpyxl, first worksheet) | Implemented |
| Header auto-mapping: exact → normalized → fuzzy (difflib ≥ 0.72) | Implemented |
| CCTNS/ICJS header profile (`cctns`) | Implemented |
| Per-row validation with typed coercion + row report | Implemented |
| Duplicate detection against existing rows | Implemented |
| Dry-run commit | Implemented |
| Import job audit trail (`import_jobs` table) | Implemented |
| Template download (CSV/XLSX) per entity/profile | Implemented |

Out of scope (future work): live ICJS web-service sync, delta/CDC feeds,
encrypted transfer, state-level identity resolution across agencies.

## 2. Ingestion pipeline

```
upload ──► parse (csv/xlsx) ──► header mapping (profile-aware)
      ──► row validation/coercion ──► preview report  (POST /data-import/preview)
      ──► commit valid rows          (POST /data-import/commit, dry_run supported)
      ──► audit job row              (import_jobs)
```

Constraints: max **5 000 rows** per file; validation report capped at the first
**200 problem rows**. Nothing is partially committed — a row either imports or
is reported in `report[]`.

## 3. Entities and canonical columns

Canonical schemas live in `backend/app/services/ingest_service.py`
(`ENTITY_SPECS`). Summary:

### victims
| Column | Required | Type | Notes |
|---|---|---|---|
| full_name | yes | string | |
| gender | no | enum | Male / Female / Other |
| age | no | integer | |
| contact_number | no | string | |
| address | no | string | |
| statement | no | string | |

### criminals
| Column | Required | Type | Notes |
|---|---|---|---|
| full_name | yes | string | |
| aliases | no | string | |
| date_of_birth | no | date | ISO `YYYY-MM-DD`; also accepts DD-MM-YYYY, DD/MM/YYYY |
| gender | no | enum | Male / Female / Other |
| address, identifying_marks, mo_summary | no | string | |
| status | no | enum | at_large / arrested / convicted / deceased |

### crime_cases
| Column | Required | Type | Notes |
|---|---|---|---|
| case_number | yes | string | uniqueness enforced vs existing DB rows |
| category_name | yes | string | matched tolerantly to `crime_categories.name` (case, `&`↔`and`) |
| district | yes | string | alias-normalized (e.g. `bangalore` → `Bengaluru Urban`) |
| station | no | string | resolved to `locations.id` when found |
| occurred_at | yes | datetime | ISO preferred |
| description, mo_tags | no | string | |
| status | no | enum | open / under_investigation / closed / convicted (default open) |
| priority | no | enum | low / medium / high / critical (default medium) |
| progress | no | integer | default 10 |

## 4. CCTNS / ICJS header profile

Selected with `profile=cctns`. Keys are common headers from CCTNS exports such
as *Search Arrested Person*, *Crime Details FIR* and victim registries.
Mapping is defined in `CCTNS_COLUMN_MAPS` (`ingest_service.py`):

| Entity | CCTNS header(s) | → Canonical column |
|---|---|---|
| victims | NAME_OF_VICTIM, VICTIM_NAME | full_name |
| victims | GENDER / AGE | gender / age |
| victims | MOBILE_NUMBER, CONTACT_NO | contact_number |
| victims | STATEMENT_DETAILS, STATEMENT | statement |
| criminals | ARRESTED_PERSON_NAME, PERSON_NAME, ACCUSED_NAME | full_name |
| criminals | ALIAS_NAME, ALIASES | aliases |
| criminals | DATE_OF_BIRTH, DOB | date_of_birth |
| criminals | IDENTIFICATION_MARKS | identifying_marks |
| criminals | MODUS_OPERANDI, MO_DETAILS | mo_summary |
| criminals | ARREST_STATUS, PERSON_STATUS | status |
| crime_cases | REGISTRATION_NO, FIR_NO | case_number |
| crime_cases | CRIME_HEAD, IPC_SECTIONS, BNS_SECTIONS | category_name |
| crime_cases | DISTRICT_NAME, DISTRICT_CD | district |
| crime_cases | POLICE_STATION, PS_NAME | station |
| crime_cases | DATE_OF_REGISTRATION, INCIDENT_DATE | occurred_at |
| crime_cases | COMPLAINT_DETAILS, GENERAL_REMARKS | description |
| crime_cases | FIR_STATUS, CASE_STATUS | status |

Rules:
1. Profile aliases are matched **case-insensitively** after uppercasing.
2. Headers not covered by the profile fall through to the standard fuzzy mapper.
3. Unmapped headers are listed in `unmapped_headers` — never silently dropped.
4. Missing required canonical columns abort commit via `missing_required`.
5. `ARREST_STATUS` values are normalized to the criminal status enum
   (`arrested`, `at_large`, …) by the shared choice validation.

Extending: add entries to `CCTNS_COLUMN_MAPS` (and optionally `ENTITY_SPECS`)
— no route changes needed. The `/data-import/entities` endpoint exposes the
active specs so integrators can self-discover.

## 5. Validation & error reporting

Per row, `validate_row()` emits:
- `errors[]` — block import of that row (type mismatches, enum violations,
  unknown category/district-station resolution failures, duplicates);
- `warnings[]` — non-blocking notes (unknown-but-plausible district names).

The preview response contains `column_mapping`, `missing_required`,
`total_rows`, `estimated_valid_rows`, `estimated_invalid_rows`,
`validation_report[{row_number, errors[], warnings[]}]`, `truncated`.

## 6. API surface (`/api/v2/data-import`, RBAC: admin/crime_analyst/investigator)

| Method & path | Purpose |
|---|---|
| `GET /entities` | Entity specs + profiles + column lists |
| `GET /template/{entity_type}?export_format=csv\|xlsx&profile=` | Downloadable ingest template |
| `POST /preview` (multipart: file, entity_type, profile) | Parse + validate, no writes |
| `POST /commit` (multipart; optional `dry_run=true`) | Persist valid rows, audit job |
| `GET /jobs?limit=` / `GET /jobs/{id}` | Import audit trail |

Every commit writes an `import_jobs` row (status `completed|partial|failed`,
row counts, JSON row report) attributed to the acting user.

## 7. Front-end entry point

Admin panel → **Import** tab (`DataImportPanel`): pick entity + profile,
upload, run *Validate & Preview Mapping* / *Dry Run* / *Commit Import*, and
inspect the recent-jobs table.

## 8. Reference data dependency

`crime_cases` imports resolve `category_name`/`district`/`station` against the
seeded reference tables. District socio-economic indicators used elsewhere are
maintained separately via `backend/scripts/socioeconomic_indicators.sql`
(Supabase) with a bundled CSV fallback.
