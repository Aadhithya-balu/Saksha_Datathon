# Saksha Data Ingestion & Reconciliation Pipeline

**Issue 5 (P1) — bulk CCTNS/ICJS-style ingestion into trusted SAKSHA records.**

This document explains how an external CSV/XLSX dataset becomes **trusted
Saksha operational data**, and how to answer, for any record:

> Where did this record come from? · Which import created it? · Which source
> file and row produced it? · Was it validated? · Was it duplicated? · Did it
> conflict with an existing record? · What quality grade did the dataset get?
> · Is it trusted for analytics?

The core rule: **a successfully uploaded file is never treated as trusted
operational intelligence on its own.**

---

## 1. Supported source formats

| Format | Notes |
|---|---|
| `.csv` | UTF-8 (BOM tolerated). Max **10 MB**, max **5 000 data rows**. |
| `.xlsx` / `.xls` | Real OOXML workbook (magic bytes `PK\x03\x04` verified — extensions alone are not trusted). First worksheet. |

Files failing size/type/content validation are rejected with HTTP **415**
before parsing (`ImportSecurityError`). All cell contents are treated as
untrusted input; all persistence uses parameterized ORM operations.

## 2. Pipeline overview

```
Source file (CSV/XLSX)
  → POST /data-import/commit            [admin or crime_analyst]
      → ImportJob created               (status: processing → validated → reconciling)
      → File validation                 (size, magic bytes, encoding)
      → Parse                           (csv / openpyxl)
      → Schema mapping                  (standard or cctns profile + fuzzy fallback)
      → Normalization                   (deterministic, documented below)
      → Row validation                  (coded errors/warnings per field)
      → Staging                         (import_staging_records; production tables untouched)
      → Duplicate detection             (exact + fuzzy, batch and vs DB)
      → Reconciliation vs trusted data  (new / matched / conflict / duplicate / review)
      → Quality grading                 (A/B/C/D/REJECTED from real metrics)
      → Job finalized                   (completed | completed_with_warnings | failed)
  → Admin review                        (GET /jobs/{id}, /jobs/{id}/quality, /jobs/{id}/records)
  → POST /jobs/{id}/promote             [admin only]
      → Trusted Saksha records          (dataset_provenance='migrated', full lineage)
  → optional POST /jobs/{id}/rollback   [admin only; deletes ONLY this import's records]
```

`POST /preview` runs everything except staging/persistence (pure read-only
analysis); `dry_run=true` on commit behaves the same way.

## 3. Import job

Every import creates one row in `import_jobs` (UUID id, timestamps, acting
user) carrying:

- identity: entity type, source format, mapping profile, **source system**,
  filename;
- lifecycle status: `uploaded → processing → validated → reconciling →
  completed | completed_with_warnings | failed | cancelled`;
- metrics (§9 below): total/valid/invalid/warning rows, exact duplicates,
  potential duplicates, conflicts, new/matched records, rejected rows,
  review rows, error count, promoted rows;
- **quality grade** (`A/B/C/D/REJECTED`) and processing/promotion/rollback
  timestamps.

Failed pipelines persist the job with status `failed` for traceability.

## 4. Source provenance

Every promoted record carries lineage columns (`ImportProvenanceMixin`):

| Column | Meaning |
|---|---|
| `dataset_provenance` | `live` (operational entry) or `migrated` (bulk import). Never auto-set to live just because a row was inserted. |
| `source_import_job_id` | FK to the originating import job |
| `source_file` | Original upload filename |
| `source_row_ref` | Spreadsheet row number (header-inclusive) |

Verbatim source values — including headers that did **not** map to any Saksha
column — are preserved in `import_staging_records.raw_data`, so nothing is
silently discarded.

Analytics can distinguish migrated from live data via
`dataset_provenance`, and admins can trace any record back to its source via
`GET /data-import/lineage/{entity_type}/{record_id}`.

## 5. Schema mapping (field-level)

Canonical column specs live in `ENTITY_SPECS`
(`backend/app/services/ingest_service.py`) and are exposed by
`GET /data-import/entities`. Two profiles:

- **standard** — Saksha-native columns (downloadable templates via
  `GET /template/{entity_type}?export_format=csv|xlsx`);
- **cctns** — maps CCTNS/ICJS extract headers, e.g.
  `FIR_NO → case_number`, `DISTRICT_NAME → district`,
  `POLICE_STATION → station`, `INCIDENT_DATE → occurred_at`,
  `CRIME_HEAD → category_name`. Full table in `CCTNS_ICJS_INTEROP.md`.

Mapping resolution order: exact profile alias → upper-cased alias →
normalized header match. Unmapped headers are reported (`unmapped_headers`)
and their values kept in `raw_data`.

If a *required* canonical column has no mapped source header at all, the
whole import is rejected (`400`) before any row is staged.

Key mappings for `crime_cases`:

| Source Field | SAKSHA Field | Required | Transformation |
|---|---|---|---|
| REGISTRATION_NO / FIR_NO | case_number | Yes | Trim, collapse spaces, uppercase |
| DISTRICT_NAME / DISTRICT_CD | district | Yes | Alias standardization (`bangalore → Bengaluru Urban`) |
| POLICE_STATION / PS_NAME | station → location_id | No | Case-insensitive station lookup in that district |
| INCIDENT_DATE / DATE_OF_REGISTRATION | occurred_at | Yes | Multi-format date normalization |
| CRIME_HEAD / IPC_SECTIONS / BNS_SECTIONS | category_name | Yes | Tolerant category match (`&` ↔ `and`, case) |
| CASE_STATUS / FIR_STATUS | status | No | Lowercased enum check |

## 6. Normalization rules (deterministic)

Applied before validation, pure functions, no locale dependence:

- **Text**: trim + collapse internal whitespace. Case of names/statements is
  preserved (sensitive values are not reformatted).
- **Identifiers** (case/FIR numbers): trim, collapse, uppercase.
- **Phone numbers**: strip separators, keep leading `+`.
- **Dates/datetimes**: accept `YYYY-MM-DD`, `DD-MM-YYYY`, `DD/MM/YYYY`,
  `MM/DD/YYYY`, `DD.MM.YYYY`, `YYYY/MM/DD`, with optional `HH:MM[:SS]`.
- **Enum values**: lowercased before choice validation.
- **Nulls**: empty strings become SQL NULL.

Duplicate *matching* additionally uses a casefolded name key
(`normalize_person_key`) — used only for comparison, never stored.

## 7. Validation rules (§8/§9)

Every row is checked against schema + business rules; results are coded as
`CODE(field): message` strings plus structured `{code, field, message}`
objects:

| Code | Severity | Trigger |
|---|---|---|
| `REQUIRED_FIELD_MISSING` | error | Required column empty |
| `INVALID_TYPE` | error | Non-integer in integer field |
| `INVALID_DATE` / `INVALID_DATETIME` | error | Unparseable date |
| `INVALID_CHOICE` | error | Value outside enum |
| `UNKNOWN_CATEGORY` | error | Crime category not in reference table |
| `LOCATION_NOT_FOUND` | error | Station/district pair resolves to no location (no silent fallback) |
| `DISTRICT_UNRECOGNIZED` | warning | Not a known Karnataka reference district |
| `FUTURE_DATE` | warning | Incident timestamp in the future |
| `OUT_OF_RANGE` | warning | Age outside 0–120 |

Row states: `VALID`, `WARNING` (usable), `INVALID` (never promotable).

## 8. Duplicates, reconciliation, conflicts

**Exact duplicates (deterministic):**
- crime_cases: normalized `case_number` — strongest identifier first.
- persons (criminals/victims): same casefolded name **AND** same DOB or
  contact number. Names alone are never enough to call something a duplicate.

**Fuzzy detection:** identical casefolded person names (vs the batch or the
DB) are flagged `POTENTIAL_DUPLICATE`, trust `review_required`, held back
from promotion unless an admin explicitly passes `include_review=true`.
Nothing is ever merged automatically.

**Reconciliation outcomes** (per staged row):

| Status | Meaning | Promoted? |
|---|---|---|
| `new_record` | Unknown to Saksha, valid | Yes (default) |
| `matched` / `duplicate` | Identical to existing trusted record, or exact in-batch dup | No — skipped/rejected |
| `conflict` | Same key as a trusted record but differing fields | **Never automatically** |
| `review_required` | Potential duplicate | Only with explicit admin override |

**Conflict handling:** when an imported case disagrees with the trusted
record (e.g. trusted `status=open` vs imported `status=closed`), the system
records both values with sources in `reconciliation_details.field_conflicts`,
leaves the trusted record untouched, and flags the row `review_required`.
Resolution is a deliberate administrative act; history is never destroyed.

## 9. Quality metrics & grading (§16/§17)

All values are computed from actual staged rows — never hardcoded:
total, valid, invalid, warning, exact-duplicate, potential-duplicate,
conflict, new-record, matched, updated, rejected, review, error count,
promoted.

Grade thresholds (configurable constants `GRADE_THRESHOLDS` in
`ingest_service.py`; documented here):

Let `problem_ratio = (invalid_rows + conflict_rows) / total_rows`:

| Grade | Criteria |
|---|---|
| **A** | ≤ 2% problem rows and zero conflicts |
| **B** | ≤ 10% problem rows (or ≤ 2% with ≥ 1 conflict) |
| **C** | ≤ 25% problem rows |
| **D** | > 25% problems, or no fully valid rows |
| **REJECTED** | > 50% problems, or zero valid rows — do not promote |

The `/jobs/{id}/quality` endpoint returns the stored grade, an independently
recomputed grade (integrity cross-check), the ratio, thresholds, and a trust
summary (promotable-now / requires-review / rejected / promoted).

## 10. Promotion, rollback, transaction safety

- **Commit stages only.** Production tables receive nothing until an admin
  calls `POST /jobs/{id}/promote`.
- Promotion inserts eligible staged rows inside a single transaction; a
  failure rolls back the entire promotion (no partial state).
- Promoted rows are stamped `dataset_provenance='migrated'` + lineage.
- `POST /jobs/{id}/rollback` (admin) deletes **only** rows whose
  `source_import_job_id` matches the job, un-promotes their staged rows and
  cancels the job. Unrelated operational data can never be affected.
- Rolled-back jobs cannot be re-promoted.

## 11. Authorization

| Operation | Roles |
|---|---|
| Entities/templates/preview/jobs read | admin, crime_analyst, investigator |
| Commit (run pipeline) | admin, crime_analyst |
| Promote / rollback (incl. conflict resolution, review overrides) | **admin only** |

Enforced server-side via RBAC route dependencies; frontend visibility is
irrelevant to enforcement.

## 12. Audit trail

Reuses the existing `audit_logs` system: `IMPORT_PREVIEW`, `DATA_IMPORT`
(commit; includes grade + metric summary), `IMPORT_PROMOTED`,
`IMPORT_ROLLED_BACK`, each with user, timestamp, job id and result JSON.

## 13. API surface (`/api/v2/data-import`)

| Method & path | Purpose |
|---|---|
| `GET /entities` | Entity specs, profiles, pipeline description |
| `GET /template/{entity_type}` | Downloadable CSV/XLSX template |
| `POST /preview` | Read-only parse/map/validate report |
| `POST /commit` (`dry_run`, `source_system`) | Full pipeline → staging + grade |
| `GET /jobs`, `GET /jobs/{id}` | Job list/detail incl. metrics + grade |
| `GET /jobs/{id}/quality` | Quality report + recomputed grade |
| `GET /jobs/{id}/records` | Row-level staging detail (filterable) |
| `POST /jobs/{id}/promote` | **Admin** — promote staged rows |
| `POST /jobs/{id}/rollback` | **Admin** — undo this import's promotions |
| `GET /lineage/{entity_type}/{record_id}` | Trace a record to its source |

## 14. Database upgrade (existing deployments)

`create_all()` handles fresh databases. For an existing Supabase database run
once:

```
psql $DATABASE_URL -f backend/scripts/import_pipeline_upgrade.sql
```

It adds the `import_staging_records` table, the new `import_jobs` columns and
the provenance columns on `crime_cases` / `criminals` / `victims`
(idempotent; existing rows default to `dataset_provenance='live'`).

## 15. Example workflow

```bash
# 1. Analyst uploads a CCTNS extract (staged, graded — nothing promoted)
curl -F "file=cctns_june.csv" -F "entity_type=crime_cases" \
     -F "profile=cctns" -F "source_system=CCTNS-KA" \
     -H "Authorization: Bearer $ANALYST_TOKEN" \
     http://localhost:8000/api/v2/data-import/commit
# → {job_id, quality_grade:"B", new_record_rows:8900, invalid_rows:400,
#    conflict_rows:120, potential_duplicate_rows:55, status:"completed_with_warnings"}

# 2. Inspect quality and problematic rows
curl -H "..." .../data-import/jobs/$JOB/quality
curl -H "..." .../data-import/jobs/$JOB/records?reconciliation_status=conflict

# 3. Admin promotes eligible records (conflicts stay untouched)
curl -X POST -H "$ADMIN_TOKEN" .../data-import/jobs/$JOB/promote

# 4. Provenance query for any promoted case
curl -H "..." .../data-import/lineage/crime_cases/$CASE_ID
# → {dataset_provenance:"migrated", source_file:"cctns_june.csv",
#    source_row_ref:"1234", import_job:{...}}
```

## 16. Test coverage

`backend/tests/test_ingestion_pipeline.py` covers: file-type rejection,
schema rejection, malformed-row coding, exact/fuzzy/person duplicate
handling, existing-match skipping, conflict preservation of trusted records,
provenance + lineage round-trip, live-vs-migrated defaults, grade
thresholds, commit-stages-only behaviour, selective rollback, double-rollback
rejection, admin-only promotion (403 for analysts/viewers), partial-failure
reporting, and end-to-end CCTNS import with unknown-column preservation.
