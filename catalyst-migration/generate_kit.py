"""Generate the Catalyst migration kit from SAKSHA's seed SQL.

Reads backend/scripts/saksha_full_setup.sql, converts every INSERT into a
per-table CSV under data/ aligned to schema_registry, and writes:
  - data/<table>.csv            import-ready CSV (header = column names)
  - manifest.json               baseline timestamp, per-table counts, warnings
  - schema.json                 machine-readable Catalyst schema spec
  - TABLE_SPECS.md              human-readable console cheat-sheet
  - VERIFICATION.md             ZCQL verification queries + expected counts

Usage:
  python generate_kit.py [--baseline 2026-01-01T00:00:00Z] [--sql <path>]

The --baseline pins the value substituted for Postgres' now() (the seed uses
relative timestamps such as now() - interval '2 hours'). Defaults to the
current UTC time so the demo data migrates with a fresh clock.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import uuid as uuid_mod
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema_registry as R  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQL = _REPO_ROOT / "backend" / "scripts" / "saksha_full_setup.sql"
OUT_DIR = Path(__file__).resolve().parent

TS_FMT = "%Y-%m-%d %H:%M:%S"
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_NOW_RE = re.compile(r"now\(\)(?:\s*-\s*interval\s+'([^']+)')?", re.IGNORECASE)
_CAST_RE = re.compile(r"\s*::(jsonb|json|uuid|date|timestamptz|text)$", re.IGNORECASE)

BASELINE: dt.datetime = dt.datetime.now(dt.timezone.utc)


# ---------------------------------------------------------------------------
# SQL value tooling
# ---------------------------------------------------------------------------
def _is_quoted_at(s: str, i: int) -> bool:
    return s[i] == "'"


def _read_quoted(s: str, i: int) -> tuple[str, int]:
    """Return (unescaped string, index just after closing quote)."""
    assert s[i] == "'"
    i += 1
    buf = []
    while i < len(s):
        if s[i] == "'":
            if i + 1 < len(s) and s[i + 1] == "'":
                buf.append("'")
                i += 2
                continue
            return "".join(buf), i + 1
        buf.append(s[i])
        i += 1
    raise ValueError(f"unterminated string literal: {s!r}")


def split_row_values(row: str) -> list[str]:
    """Split a parenthesised VALUES row into top-level value tokens."""
    if row.startswith("(") and row.endswith(")"):
        row = row[1:-1]
    vals: list[str] = []
    depth = 0
    buf: list[str] = []
    in_quote = False
    i = 0
    while i < len(row):
        ch = row[i]
        if ch == "'":
            if in_quote and i + 1 < len(row) and row[i + 1] == "'":
                buf.append("''")
                i += 2
                continue
            in_quote = not in_quote
            buf.append(ch)
        elif in_quote:
            buf.append(ch)
        elif ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            vals.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    if buf:
        vals.append("".join(buf).strip())
    return vals


def split_row_list(block: str) -> list[str]:
    """Split a VALUES block into individual '(...)' row strings."""
    rows = []
    i = 0
    n = len(block)
    while i < n:
        while i < n and block[i] != "(":
            i += 1
        if i >= n:
            break
        depth = 0
        in_quote = False
        start = i
        buf = []
        while i < n:
            ch = block[i]
            buf.append(ch)
            if ch == "'":
                if in_quote and i + 1 < n and block[i + 1] == "'":
                    buf.append(block[i + 1])
                    i += 2
                    continue
                in_quote = not in_quote
            elif not in_quote:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        rows.append("".join(buf).strip())
                        i += 1
                        break
            i += 1
        if depth != 0:
            raise ValueError(f"unbalanced parentheses while parsing rows near: {''.join(buf)[:120]!r}")
    return rows


def parse_value(token: str):
    token = token.strip()
    if not token:
        return None
    if token.upper() == "NULL":
        return None
    if token.upper() in ("TRUE", "FALSE"):
        return token.upper() == "TRUE"
    cast_match = _CAST_RE.search(token)
    if cast_match:
        token = token[: cast_match.start()].strip()
    if token.startswith("E'") or token.startswith("e'"):
        token = "'" + token[2:]
    if token.startswith("'"):
        val, _ = _read_quoted(token, 0)
        return val
    if token.startswith("ARRAY["):
        inner = token[len("ARRAY[") : -1]
        if not inner.strip():
            return None
        parts = split_row_values("(" + inner + ")")
        return [parse_value(p) for p in parts]
    now_m = _NOW_RE.match(token)
    if now_m:
        delta = now_m.group(1)
        resolved = BASELINE
        if delta:
            m = re.match(r"(\d+)\s+(day|hour)s?", delta, re.IGNORECASE)
            if not m:
                raise ValueError(f"unsupported interval literal: {delta!r}")
            amount = int(m.group(1))
            unit = m.group(2).lower()
            resolved = BASELINE - dt.timedelta(days=amount if unit == "day" else 0, hours=amount if unit == "hour" else 0)
        return resolved
    if _UUID_RE.match(token):
        return token.lower()
    if token.startswith("("):  # cast expressions elsewhere - keep as text
        return token
    try:
        if re.fullmatch(r"-?\d+", token):
            return int(token)
        if re.fullmatch(r"-?\d+\.\d+", token):
            return float(token)
    except ValueError:
        pass
    return token  # bare identifier/expression: keep verbatim, mark in reports


# ---------------------------------------------------------------------------
# SQL -> rows
# ---------------------------------------------------------------------------
def extract_inserts(sql_text: str) -> dict[str, list[dict]]:
    pattern = re.compile(r"INSERT\s+INTO\s+(\w+)\s*\(([^)]*)\)\s*VALUES", re.IGNORECASE)
    result: dict[str, list[dict]] = {}
    for m in pattern.finditer(sql_text):
        table = m.group(1).lower()
        cols = [c.strip().lower() for c in m.group(2).split(",") if c.strip()]
        block_end = sql_text.find("\n--", m.end())
        block = sql_text[m.end() : block_end if block_end != -1 else None]
        for row_text in split_row_list(block):
            tokens = split_row_values(row_text)
            if len(tokens) != len(cols):
                raise ValueError(
                    f"{table}: expected {len(cols)} values, got {len(tokens)} for row {row_text[:120]!r}"
                )
            result.setdefault(table, []).append(
                {c: parse_value(t) for c, t in zip(cols, tokens)}
            )
    return result


def _fmt(v) -> str:
    if v is None:
        return ""
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, dt.datetime):
        return v.astimezone(dt.timezone.utc).replace(tzinfo=None).strftime(TS_FMT)
    if isinstance(v, (list, dict)):
        return json.dumps(v)
    if isinstance(v, float):
        return repr(v)
    return str(v)


def _synth_id(table: str, row: dict) -> str:
    key = "|".join(str(row.get(c, "")) for c in sorted(row.keys()))
    return str(uuid_mod.uuid5(uuid_mod.NAMESPACE_URL, f"saksha/catalyst/{table}/{key}"))


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
def build_rows(sql_text: str) -> dict[str, list[dict]]:
    seed = extract_inserts(sql_text)
    out: dict[str, list[dict]] = {}
    warnings: list[str] = []
    for table in R.TABLE_ORDER:
        cols = R.full_columns(table)
        headers = [c[0] for c in cols]
        seeded = seed.get(table, [])
        rows: list[list[str]] = []
        for raw in seeded:
            row = {h: None for h in headers}
            for k, v in raw.items():
                if k not in row:
                    warnings.append(f"{table}: INSERT column {k!r} is not in the registry - dropped")
                    continue
                row[k] = v if isinstance(v, (str, int, float, bool, list, dict, dt.datetime)) or v is None else str(v)
            for h, k, f in cols:
                if h in R.TIMESTAMP_FILLERS and row[h] is None:
                    row[h] = BASELINE
                elif k == "bool" and row[h] is None:
                    row[h] = False
                elif k == "int" and row[h] is None:
                    row[h] = 0
            if table in R.LINK_TABLES_WITH_SYNTH_ID and (not row.get("id") or row["id"] is None):
                row["id"] = _synth_id(table, raw)
            row["dataset_provenance"] = "demo"
            row["source_file"] = "saksha_full_setup.sql"
            row["source_row_ref"] = str(len(rows) + 1)
            rows.append([_fmt(row[h]) for h in headers])
        out[table] = rows
    return out, warnings


def write_csv(table: str, rows: list[list[str]], headers: list[str]) -> Path:
    csv_path = OUT_DIR / "data" / f"{table}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        fh.write(",".join(headers) + "\r\n")
        for r in rows:
            # quote only where necessary (safe subset of RFC 4180)
            parts = []
            for v in r:
                needs = any(ch in v for ch in ',"\r\n')
                parts.append(f'"{v.replace(chr(34), chr(34)*2)}"' if needs else v)
            fh.write(",".join(parts) + "\r\n")
    return csv_path


def write_spec(readable: dict[str, list[dict]], warnings: list[str]) -> None:
    path = OUT_DIR / "saksha_schema.sql"
    with path.open("w", encoding="utf-8") as fh:
        fh.write("-- ============================================================\n")
        fh.write("-- SAKSHA -> CATALYST DATA STORE MIGRATION SPEC\n")
        fh.write("-- Style: PostgreSQL DDL mirroring schema_registry.py.\n")
        fh.write("-- NOTE: The Data Store API/SDK/CLI cannot create this schema.\n")
        fh.write("--       Tables + columns must be created in the Catalyst\n")
        fh.write("--       console (Data Store > Create a new Table / +New Column).\n")
        fh.write("-- ============================================================\n\n")
        for table in R.TABLE_ORDER:
            cols = R.full_columns(table)
            fh.write(f"-- {table}\n")
            lines = []
            for cname, k, flags in cols:
                ctype, maxlen = R.catalyst_type(k)
                dt_str = ctype
                if maxlen:
                    dt_str += f"({maxlen})"
                fk = ""
                if flags.get("unique"):
                    fk += " UNIQUE"
                if flags.get("mandatory"):
                    fk += " NOT NULL"
                lines.append(f"    {cname:<28} {dt_str:<18}{fk}")
            fh.write("CREATE TABLE " + table + " (\n" + ",\n".join(lines) + "\n);\n\n")


def write_manifest(per_table: dict[str, list[list[str]]], warnings: list[str]) -> None:
    expected = R.expected_seed_counts()
    details = {}
    for t in R.TABLE_ORDER:
        details[t] = {
            "csv": f"data/{t}.csv",
            "rows": len(per_table[t]),
            "seeded": t in expected,
            "expected_rows": expected.get(t, 0),
        }
    manifest = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "baseline_utc": BASELINE.astimezone(dt.timezone.utc).isoformat(),
        "baseline_meaning": "Value substituted for PostgreSQL now(); relative seed timestamps were resolved against it.",
        "catalyst_note": ("Schema (tables + columns) creation is only possible via the "
                          "Catalyst console; this kit stages the data import and verification only."),
        "tables": details,
        "row_total": sum(len(v) for v in per_table.values()),
        "warnings": warnings,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_table_specs() -> None:
    lines = [
        "# Catalyst Data Store — manual column spec",
        "",
        "Columns are listed in the same order as the CSV header in `data/<table>.csv`. "
        "Create **only** these columns — Catalyst auto-adds `ROWID`, `CREATORID`, "
        "`CREATEDTIME`, `MODIFIEDTIME`, which must be left untouched.",
        "",
        "Recommended console settings per column: `IsUnique` for the logical PK and any "
        "`unique`-flagged columns; `IsMandatory` where flagged; enable `Search Index` on "
        "the logical PK and lookup columns (case_number, username, badge_number, fir_number) ",
        "so the app/ queries stay fast.",
        "",
    ]
    for table in R.TABLE_ORDER:
        expected = R.expected_seed_counts()
        line = f"## `{table}`"
        if table in expected:
            line += f"  — seed rows to import: {expected[table]}"
        lines.append(line)
        lines.append("")
        lines.append("| # | Column | Catalyst data type | Unique | Mandatory | Notes |")
        lines.append("|---|--------|-------------------|--------|-----------|-------|")
        for i, (cname, k, flags) in enumerate(R.full_columns(table), start=1):
            ctype, maxlen = R.catalyst_type(k)
            dt_str = ctype + (f"({maxlen})" if maxlen else "")
            lines.append(
                f"| {i} | `{cname}` | {dt_str} | {('Y' if flags.get('unique') else '')} | "
                f"{('Y' if flags.get('mandatory') else '')} | {flags.get('note', '')} |"
            )
        lines.append("")
    (OUT_DIR / "TABLE_SPECS.md").write_text("\n".join(lines), encoding="utf-8")


def write_verification(expected: dict[str, int]) -> None:
    lines = [
        "# Verification plan — SAKSHA on Catalyst Data Store",
        "",
        "## 1. Idempotent row counts",
        "",
        "Confirm every migrated table holds the expected number of rows. These queries use "
        "ZCQL (DML/read-only — matching Catalyst Cloud Scale's supported operations):",
        "",
    ]
    for t, n in sorted(expected.items()):
        lines.append(f"- `SELECT COUNT(*) FROM {t}`  →  **{n}**")
    lines += [
        "",
        "## 2. Referential integrity",
        "",
        "### FIRs point at existing cases",
        "```sql",
        "SELECT COUNT(*) FROM firs f LEFT JOIN crime_cases c ON f.crime_case_id = c.id WHERE c.id IS NULL",
        "```",
        "→ `0`",
        "",
        "### Cases point at existing categories and locations",
        "```sql",
        "SELECT COUNT(*) FROM crime_cases cc LEFT JOIN crime_categories k ON cc.category_id = k.id",
        "LEFT JOIN locations l ON cc.location_id = l.id",
        "WHERE k.id IS NULL OR l.id IS NULL",
        "```",
        "→ `0`",
        "",
        "### FBI links resolve to FIRs, criminals and victims",
        "```sql",
        "SELECT COUNT(*) FROM fir_criminal_links x LEFT JOIN firs f ON x.fir_id = f.id",
        "LEFT JOIN criminals c ON x.criminal_id = c.id WHERE f.id IS NULL OR c.id IS NULL",
        "```",
        "→ `0`  (run the equivalent for `fir_victim_links` against `victims` too)",
        "",
        "## 3. Business analytics still hold",
        "",
        "### District ranking by open cases (severity-weighted view)",
        "```sql",
        "SELECT l.district, COUNT(*) AS cases FROM crime_cases cc",
        "JOIN locations l ON cc.location_id = l.id GROUP BY l.district ORDER BY cases DESC",
        "```",
        "→ Bengaluru Urban 2, Mysuru 2, then 1 each for Mangaluru, Belagavi, Ballari, Kalaburagi, Hassan, Tumkuru, Dharwad.",
        "",
        "### Repeat-offender detection (criminals named in ≥2 FIRs)",
        "```sql",
        "SELECT criminal_id, COUNT(DISTINCT fir_id) AS n FROM fir_criminal_links GROUP BY criminal_id HAVING COUNT(DISTINCT fir_id) >= 2",
        "```",
        "→ Ramu Swamy only.",
        "",
        "### Search plumbing still returns offenders/cases/FIRs",
        "```sql",
        "SELECT * FROM criminals WHERE full_name LIKE '%Ibrahim%';",
        "SELECT * FROM crime_cases WHERE case_number = 'CR-2026-BNG-001';",
        "SELECT * FROM firs WHERE fir_number = 'FIR-789/MYS/2026';",
        "```",
        "→ 1 row each.",
        "",
        "## 4. Provenance preserved (DEMO/SEED status)",
        "```sql",
        "SELECT dataset_provenance, COUNT(*) FROM crime_cases GROUP BY dataset_provenance;",
        "```",
        "→ `demo  11` (and the same across every migrated table that carries the triplet).",
        "",
        "## 5. App-level spot checks (after the backend is pointed at Catalyst)",
        "- Criminal search (offenders page) returns the 5 seeded criminals.",
        "- Case/FIR lists render with correct linked entities.",
        "- Network graph builds from `crime_cases`, `firs`, `fir_criminal_links`, `fir_victim_links`.",
        "- Hotspots page renders (driven by `locations.latitude/longitude` + `crime_cases`).",
        "- Predictions page loads (risk/forecast models read the same tables).",
        "- AI Chat persists conversations into `chat_conversations`/`chat_messages`.",
        "- Reports export works (`reports` insert on generate).",
        "- Auth: `admin` / `564738` and `SCRB-7740` / `123456` log in (hashed_password preserved).",
        "- Evidence file/image workflows: `evidence_metadata.storage_url` / `filepath` point to the "
        "migrated bucket paths (note: uploads themselves must be re-synced to Stratus).",
    ]
    (OUT_DIR / "VERIFICATION.md").write_text("\n".join(lines), encoding="utf-8")


def validate_references(seed: dict[str, list[dict]]) -> list[str]:
    ids: dict[str, set] = {}
    for table in R.TABLE_ORDER:
        ids[table] = {str(r.get("id", "")).lower() for r in seed.get(table, []) if r.get("id")}
    fk_map = [
        ("users", "role_id", "roles"), ("officers", "user_id", "users"),
        ("crime_cases", "category_id", "crime_categories"),
        ("crime_cases", "location_id", "locations"),
        ("crime_cases", "assigned_officer_id", "officers"),
        ("firs", "crime_case_id", "crime_cases"),
        ("firs", "investigating_officer_id", "officers"),
        ("fir_criminal_links", "fir_id", "firs"),
        ("fir_criminal_links", "criminal_id", "criminals"),
        ("fir_victim_links", "fir_id", "firs"),
        ("fir_victim_links", "victim_id", "victims"),
        ("evidence", "case_id", "crime_cases"),
        ("notifications", "user_id", "users"),
        ("notifications", "sender_id", "users"),
    ]
    issues = []
    for child, col, parent in fk_map:
        for row in seed.get(child, []):
            v = row.get(col)
            if v is None:
                continue
            v = str(v).lower()
            if not _UUID_RE.match(v):
                continue  # syntactic check only; skip non-uuid tokens
            if v not in ids[parent]:
                issues.append(f"{child}.{col} -> {parent}.id has dangling value {v}")
    return issues


def main() -> None:
    global BASELINE
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", default=str(DEFAULT_SQL))
    ap.add_argument("--baseline", default=None, help="ISO timestamp replacing now() (UTC)")
    args = ap.parse_args()

    if args.baseline:
        BASELINE = dt.datetime.fromisoformat(args.baseline.replace("Z", "+00:00"))
        if BASELINE.tzinfo is None:
            BASELINE = BASELINE.replace(tzinfo=dt.timezone.utc)
    else:
        BASELINE = dt.datetime.now(dt.timezone.utc)

    sql_path = Path(args.sql)
    if not sql_path.exists():
        raise SystemExit(f"SQL file not found: {sql_path}")
    sql_text = sql_path.read_text(encoding="utf-8")

    seed = extract_inserts(sql_text)
    per_table, warn = build_rows(sql_text)
    for w in warn:
        print("WARN:", w)

    ref_issues = validate_references(seed)
    for i in ref_issues:
        print("REF-ERROR:", i)

    total = 0
    for table in R.TABLE_ORDER:
        rows = per_table[table]
        total += len(rows)
        headers = [c[0] for c in R.full_columns(table)]
        write_csv(table, rows, headers)
        print(f"  {table:<24} {len(rows):>4} rows -> data/{table}.csv")

    write_manifest(per_table, warn + ref_issues)
    write_spec(per_table, warn)
    write_table_specs()
    write_verification(R.expected_seed_counts())

    print(f"\nTotal data rows staged: {total}")
    print(f"Baseline (now()): {BASELINE.astimezone(dt.timezone.utc).isoformat()}")
    print(f"Reference issues: {len(ref_issues)}")


if __name__ == "__main__":
    main()