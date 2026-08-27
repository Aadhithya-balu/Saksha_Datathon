"""Catalyst migration kit verifier.

Phase A (default, local): validates the generated seed CSVs against
manifest.json - row counts, id uniqueness/format, FK reference integrity,
timestamp readability and key spot-check values.

Phase B (--catalyst): requires the Catalyst CLI and an imported project.
Exports each seeded table via `catalyst ds:export` and diffs it against the
seed CSVs by logical id.

The full manual ZCQL check-list (referential integrity, district ranking,
repeat-offender detection, demo provenance, app spot checks) is in
VERIFICATION.md and is always printed for reference.

Usage:
  py -3.12 verify_catalyst.py                 # Phase A only
  py -3.12 verify_catalyst.py --catalyst      # Phase A + Phase B
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

os.chdir(os.path.dirname(os.path.abspath(__file__)))
import schema_registry as R  # noqa: E402

MANIFEST = Path("manifest.json")
DATA_DIR = Path("data")
TS_FMT = "%Y-%m-%d %H:%M:%S"
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

FK_MAP = [
    ("users", "role_id", "roles"),
    ("officers", "user_id", "users"),
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

SPOT_CHECKS = [
    ("users", "username", "admin"),
    ("users", "username", "SCRB-7740"),
    ("crime_cases", "case_number", "CR-2026-BNG-001"),
    ("firs", "fir_number", "FIR-045/BNG/2026"),
    ("criminals", "full_name", "Sayed Ibrahim"),
    ("victims", "full_name", "Dr. Vinay Murthy"),
]

_DATE_COL_SUFFIX = ("filed_at", "dob")

failures: list[str] = []


def read_csv(table: str) -> tuple[list[str], list[dict]]:
    path = DATA_DIR / f"{table}.csv"
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        return header, [dict(zip(header, row)) for row in reader]


def check(ok: bool, msg: str) -> None:
    tag = "ok  " if ok else "FAIL"
    print(f"  [{tag}] {msg}")
    if not ok:
        failures.append(msg)


def phase_a() -> None:
    print(f"Phase A: seed CSV validation (against {MANIFEST})")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest["tables"]

    # 1. row counts + header integrity
    print("  row counts:")
    for table, spec in expected.items():
        header, rows = read_csv(table)
        check(len(rows) == spec["rows"],
              f"{table}: {len(rows)} rows (manifest expects {spec['rows']})")
        check(header[:3] == [c[0] for c in R.full_columns(table)[:3]],
              f"{table}: header prefix matches registry")

    id_sets: dict[str, set] = {}
    for table, spec in expected.items():
        header, rows = read_csv(table)
        id_sets[table] = {r.get("id", "") for r in rows if r.get("id")}

    # 2. id uniqueness + format
    print("  id format/uniqueness:")
    for table, spec in expected.items():
        header, rows = read_csv(table)
        ids = [r.get("id", "") for r in rows]
        real = [i for i in ids if i]
        check(len(real) == len(set(real)), f"{table}: logical ids are unique")
        for i in real:
            if not UUID_RE.match(i):
                check(False, f"{table}: id {i!r} is not UUID-shaped")
                break

    # 3. FK reference integrity
    print("  FK reference integrity:")
    for child, col, parent in FK_MAP:
        _, rows = read_csv(child)
        missing = [r.get(col) for r in rows if r.get(col) and r.get(col) not in id_sets[parent]]
        check(not missing, f"{child}.{col} -> {parent}.id (all referenced ids exist)")

    # 4. timestamps / dates parse
    print("  datetime/date readability (empty is allowed):")
    for table, spec in expected.items():
        header, rows = read_csv(table)
        bad = 0
        for r in rows:
            for col in header:
                v = r.get(col, "")
                if not v:
                    continue
                if col in R.TIMESTAMP_FILLERS:
                    try:
                        dt.datetime.strptime(v, TS_FMT)
                    except ValueError:
                        bad += 1
                elif col.endswith(_DATE_COL_SUFFIX):
                    try:
                        dt.datetime.strptime(v, "%Y-%m-%d")
                    except ValueError:
                        bad += 1
        check(bad == 0, f"{table}: {bad} unparseable datetime/date cells")

    # 5. spot-check values
    print("  spot-check values:")
    for table, col, want in SPOT_CHECKS:
        _, rows = read_csv(table)
        check(any(r.get(col) == want for r in rows), f"{table}.{col} contains {want!r}")

    print()


def phase_b() -> None:
    print("Phase B: Catalyst CLI export diff (requires imported project)")
    if "--catalyst" not in sys.argv:
        return
    if not shutil_which("catalyst"):
        check(False, "catalyst CLI not found on PATH")
        return

    header_map: dict[str, list[str]] = {}
    seed_by_id: dict[str, dict] = {}
    for table in R.TABLE_ORDER:
        header, rows = read_csv(table)
        header_map[table] = header
        seed_by_id[table] = {r.get("id"): r for r in rows if r.get("id")}

    for table in R.TABLE_ORDER:
        if not seed_by_id[table]:
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8",
                                         newline="") as tmp:
            tmp_path = tmp.name
        try:
            proc = subprocess.run(
                ["catalyst", "ds:export", tmp_path, "--table", table],
                capture_output=True, text=True)
            if proc.returncode != 0:
                check(False, f"{table}: ds:export failed: {proc.stderr.strip()[:200]}")
                continue
            exported = set()
            with open(tmp_path, "r", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    rid = (row.get("id") or "").strip().lower()
                    if rid:
                        exported.add(rid)
            missing = [i for i in seed_by_id[table] if i not in exported]
            check(not missing,
                  f"{table}: {len(exported)} exported, {len(missing)} seed ids missing ({missing[:3]})")
        finally:
            os.unlink(tmp_path)
    print()


def shutil_which(cmd: str) -> str | None:
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = os.path.join(d, cmd + (".exe" if os.name == "nt" else ""))
        if os.path.isfile(p):
            return p
    return None


def print_manual_checks() -> None:
    vf = Path("VERIFICATION.md")
    print(f"Manual ZCQL checks (run in Catalyst console / ZCQL — see {vf}):")
    manual_markers = [
        "SELECT COUNT(*) FROM", "referential", "district ranking", "repeat offender",
        "provenance", "CR-2026-BNG-001", "Bengaluru Urban",
    ]
    for line in vf.read_text(encoding="utf-8").splitlines():
        if any(m in line.lower() for m in manual_markers):
            print("  " + line)


def main() -> None:
    phase_a()
    phase_b()
    print_manual_checks()
    if failures:
        print(f"\n{len(failures)} check(s) FAILED:")
        for f in failures:
            print("  - " + f)
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()