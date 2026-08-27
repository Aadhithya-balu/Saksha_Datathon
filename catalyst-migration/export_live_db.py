"""Live database export: dump current Supabase data to Catalyst-ready CSVs.

Produces data_live/<table>.csv for every registry table that exists in the
live database, using the same column order and formatting as the seed kit so
the Catalyst import + verification steps are identical for live and demo data.

Usage:
  py -3.12 export_live_db.py                 # default -> data_live/
  py -3.12 export_live_db.py --out out/      # custom output dir

Reads credentials from backend/.env via backend/scripts/_db_config.py
(reuses the same env vars as db_export_full.py). Never hardcode credentials.
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BACKEND_SCRIPTS = Path(__file__).resolve().parents[1] / "backend" / "scripts"
sys.path.insert(0, str(BACKEND_SCRIPTS))

import schema_registry as R  # noqa: E402

PROVENANCE_NAMES = {c[0] for c in R.PROVENANCE_COLUMNS}
PROVENANCE = "live"
SOURCE_FILE = "live_export"

TS_FMT = "%Y-%m-%d %H:%M:%S"
DATE_FMT = "%Y-%m-%d"


def fmt_value(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, dt.datetime):
        return v.astimezone(dt.timezone.utc).replace(tzinfo=None).strftime(TS_FMT)
    if isinstance(v, dt.date):
        return v.strftime(DATE_FMT)
    if isinstance(v, (list, dict)):
        return json.dumps(v)
    return str(v)


def csv_quote(v: str) -> str:
    if any(ch in v for ch in ',"\r\n'):
        return f'"{v.replace(chr(34), chr(34) * 2)}"'
    return v


def live_columns(cur, table: str) -> list[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return [r[0] for r in cur.fetchall()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data_live")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from _db_config import CONN
    except Exception as e:  # pragma: no cover
        sys.exit(f"Missing dependency or credentials: {e}")

    conn = psycopg2.connect(**CONN)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    exported = 0
    for table in R.TABLE_ORDER:
        try:
            live_cols = live_columns(cur, table)
        except Exception as e:
            sys.exit(f"Column introspection failed for {table}: {e}")

        headers = [c for c in (c[0] for c in R.full_columns(table)) if c in live_cols]
        if not headers:
            print(f"  skipping {table}: no matching live columns")
            continue

        cur.execute(f'SELECT * FROM "{table}" ORDER BY "id"')
        rows = cur.fetchall()
        if not rows:
            print(f"  {table:24s} 0 rows -> {out_dir / f'{table}.csv'}")
            continue

        path = out_dir / f"{table}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            fh.write(",".join(headers) + "\r\n")
            for idx, row in enumerate(rows, start=1):
                record = {h: fmt_value(row.get(h)) for h in headers if h not in PROVENANCE_NAMES}
                record["dataset_provenance"] = PROVENANCE
                record["source_file"] = SOURCE_FILE
                record["source_row_ref"] = str(idx)
                line = ",".join(csv_quote(record.get(h, "")) for h in headers)
                fh.write(line + "\r\n")
        exported += len(rows)
        print(f"  {table:24s} {len(rows)} rows -> {out_dir / f'{table}.csv'}")

    cur.close()
    conn.close()
    print(f"\nTotal live rows exported: {exported}")


if __name__ == "__main__":
    main()