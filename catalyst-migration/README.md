# SAKSHA → Zoho Catalyst Data Store — Migration Kit

Moves the complete SAKSHA PostgreSQL/Supabase database (32 tables) into a Zoho
Catalyst **Data Store**, preserving `id` values, relationships, timestamps and
the `demo`/`live` provenance marker (Issue #164).

The kit automates **data staging, import and verification**. Table/column
creation in catalyst-cloud-scale Data Store is **console-only**, so that step
is done by hand from the two generated specs and is the only manual work.

> **Why is creation manual?** Verified against the official Zoho Catalyst docs:
> - The CLI supports only `ds:import`, `ds:export`, `ds:status` (bulk *data*,
>   no schema commands).
> - ZCQL is DML-only (SELECT/INSERT/UPDATE/DELETE, JOIN/GROUP BY/HAVING) —
>   there is no DDL.
> - The Data Store API exposes only `tables.READ`, `tables.rows.*`,
>   `tables.columns.READ` scopes — there is **no** `tables.CREATE`.
> - Quote from the docs: *"Data Store APIs enable you to insert and manage
>   records … **However, you can create a table and its schema only from the
>   Catalyst console.**"*
>
> References: [CLI reference](https://docs.catalyst.zoho.com/en/cli/v1/cli-command-reference/)
> · [Import/export](https://docs.catalyst.zoho.com/en/cli/v1/data-store-import-and-export/introduction/)
> · [Tables](https://docs.catalyst.zoho.com/en/cloud-scale/help/data-store/tables/)
> · [Columns](https://docs.catalyst.zoho.com/en/cloud-scale/help/data-store/columns/)
> · [ZCQL](https://docs.catalyst.zoho.com/en/cloud-scale/help/zcql/introduction/)

---

## Layout

| File | Purpose |
|---|---|
| `schema_registry.py` | Single source of truth: 32 tables, column list, pg type → Catalyst mapping, provenance columns. |
| `generate_kit.py` | Parses `backend/scripts/saksha_full_setup.sql` → CSVs + manifest + specs. |
| `data/*.csv` | 32 tables. 13 are seeded (99 demo rows); the rest are header-only templates. |
| `manifest.json` | Row counts + generation info for the kit. |
| `saksha_schema.sql` | DDL-style spec of the Catalyst schema to create (console only). |
| `TABLE_SPECS.md` | Human-readable console cheat-sheet (type + Unique/Mandatory per column). |
| `VERIFICATION.md` | Read-only ZCQL checks and expected results. |
| `import_all.ps1` | Runs `catalyst ds:import` for the 13 seeded tables. |
| `export_live_db.py` | Exports the *live* Supabase DB to the same CSV layout (`data_live/`). |
| `verify_catalyst.py` | Phase A: validates seed CSVs. Phase B: `catalyst ds:export` diff. |

## Type mapping (PostgreSQL → Catalyst Cloud Scale)

Catalyst columns are limited to Text (≤10 000), Var Char (≤255), Date
(`YYYY-MM-DD`), DateTime (`YYYY-MM-DD HH:MM:SS`), Int, Double, Boolean, BigInt,
Foreign Key, Encrypted text. SAKSHA types are mapped as:

| Postgres | Catalyst |
|---|---|
| `uuid` (all `id` / `*_id` FKs) | Var Char(50), plain text, `Unique` set on logical PKs |
| `varchar(≤255)` | Var Char(n) |
| `varchar(>255)` / `text` / `jsonb`(serialized JSON) | Text |
| `timestamp(tz)` | DateTime (UTC, tz-offset dropped) |
| `date` | Date |
| `boolean` | Boolean |
| `integer` / `bigint` | Int / BigInt |
| `double precision` | Double |

- Catalyst auto-adds `ROWID`, `CREATORID`, `CREATEDTIME`, `MODIFIEDTIME` — these are reserved and left untouched.
- SAKSHA `id` is re-created as a plain unique text column (the "logical PK"); FKs are joined by value in ZCQL.
- In **dev**, Catalyst caps tables at 100 columns / 5 000 rows, projects at 25 000 rows → use a **production** Data Store (`import_all.ps1 -Production`) for the full corpus.

---

## Workflow

### 1. Stage the seed data (already generated, but re-runnable)

```powershell
C:\Users\aadhi\AppData\Local\Programs\Python\Python312\python.exe generate_kit.py
# optional: --baseline 2026-08-01T12:00:00Z  (value substituted for PostgreSQL now())
```

Creates/re-creates `data/*.csv`, `manifest.json`, `saksha_schema.sql`,
`TABLE_SPECS.md`, `VERIFICATION.md`. Relative seed timestamps (`now() - interval …`)
are resolved against the baseline; provenance triplet
(`dataset_provenance`, `source_file`, `source_row_ref`) is appended to every row.

### 2. Create the schema — manual, console-only (the only manual step)

In the Catalyst console **Data Store** section:
1. Create the 32 tables **in the order of `TABLE_ORDER`** in `schema_registry.py`
   (= the order of sections in `TABLE_SPECS.md`):
   roles, users, officers, locations, crime_categories, crime_cases, criminals,
   victims, firs, fir_criminal_links, fir_victim_links, evidence,
   evidence_metadata, evidence_timeline, evidence_assignments,
   evidence_ai_summary, chain_of_custody, audit_logs, notifications, reports,
   investigation_notes, mo_tags, case_mo_tags, criminal_mo_tags,
   chat_conversations, chat_messages, import_jobs, import_staging_records,
   interventions, revoked_tokens, system_settings, role_permissions.
2. For each table add exactly the columns listed in `TABLE_SPECS.md`, in that
   order (== CSV header order). Set `IsUnique`/`IsMandatory`/`Search Index` per
   the table, and leave the four Catalyst system columns untouched.

> Selective at this step is allowed: skipping a table only drops its data.

### 3. Import the data

```powershell
cd catalyst-migration
.\import_all.ps1 -Production     # production project (no dev row caps)
catalyst ds:status               # watch import jobs
```

### 4. Verify

```powershell
py -3.12 verify_catalyst.py              # Phase A: local seed validation
py -3.12 verify_catalyst.py --catalyst   # Phase B: ds:export diff against live Catalyst
```

Then run the read-only ZCQL checks in `VERIFICATION.md` (row counts → 99 across
13 tables; referential integrity → 0 orphans; district ranking Bengaluru Urban 2 /
Mysuru 2; repeat offender Ramu Swamy only; `demo  11` provenance).

### 5. Live data (optional)

Dump the current Supabase DB instead of / in addition to the seed bundle:

```powershell
py -3.12 export_live_db.py        # -> data_live/*.csv, provenance = 'live'
# import those CSVs with catalyst ds:import as in step 3
```

Credentials come from `backend/.env` via `backend/scripts/_db_config.py`
(the same env vars used by `db_export_full.py`).

---

## STOP point (per migration rules)

The Catalyst Data Store **requires** manual table/column creation in the
console (step 2). Because of that requirement, **no application code has been
changed** as part of this migration. The follow-on phase — rewriting the
backend's SQLAlchemy queries onto the Catalyst Data Store SDK and pointing the
React app at the new backend — is intentionally **not** in this kit.

## Repo state notes

- Everything under `catalyst-migration/` is new/untracked; it stays out of the
  current `validated-newly` branch unless you decide to include it.
- The `full.sql` bundle (9-table subset, Postgres COPY format) at the repo root
  is unrelated to this kit (that export uses COPY, not Catalyst CSV).