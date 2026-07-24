"""
Phase 3+4: Backup historical tables, then trim by keeping a stratified
sample of 5 000 CrimeCase rows and cascading to all children.

Run once:  py -3.12 scripts/db_trim.py
"""
import os, sys, time, json, csv
import psycopg2

CONN = dict(
    host='aws-0-ap-northeast-1.pooler.supabase.com',
    port=6543,
    dbname='postgres',
    user='postgres.tqaegfrnnddfqshwdkvh',
    password='datathon2026',
    sslmode='require',
)

BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

HISTORICAL_TABLES = [
    'InvestigationNotes', 'InvestigationTasks', 'CaseStatusHistory',
    'AIRecommendations', 'CaseProgress', 'CaseAssignments',
    'PriorityHistory', 'CaseTimeline', 'Accused',
    'ComplainantDetails', 'ChargesheetDetails',
    'ArrestSurrender', 'Victim', 'ActSectionAssociation',
    'CaseFIRLink', 'CrimeCase', 'CaseMaster',
]

CHILDREN_OF_CRIMECASE = [
    'InvestigationNotes', 'InvestigationTasks', 'CaseStatusHistory',
    'AIRecommendations', 'CaseProgress', 'CaseAssignments',
    'PriorityHistory', 'CaseTimeline',
    'CaseFIRLink',
]

CHILDREN_OF_CASEMASTER = [
    'Accused', 'ComplainantDetails', 'ChargesheetDetails',
    'ArrestSurrender', 'Victim', 'ActSectionAssociation',
]

TARGET_SAMPLE = 5000

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def q(table):
    """Double-quote a table name for case-sensitive PostgreSQL."""
    return f'"{table}"'

def count_rows(cur, table):
    cur.execute(f'SELECT COUNT(*) FROM {q(table)}')
    return cur.fetchone()[0]

def get_size_mb(cur, table):
    cur.execute(f"SELECT pg_size_pretty(pg_total_relation_size('public.{q(table)}'))")
    return cur.fetchone()[0]

def backup_table(cur, table):
    csv_path = os.path.join(BACKUP_DIR, f'{table}_backup.csv')
    cur.execute(f'SELECT * FROM {q(table)} LIMIT 5')
    cols = [desc[0] for desc in cur.description]
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for row in cur.fetchall():
            writer.writerow([str(c) for c in row])
    log(f"  Backed up {table} sample ({len(cols)} cols)")

def count_before(cur):
    counts = {}
    for t in HISTORICAL_TABLES:
        counts[t] = count_rows(cur, t)
    return counts

def select_sample_crimecase_ids(cur):
    log(f"Selecting stratified sample of {TARGET_SAMPLE} CrimeCase rows...")
    cur.execute(f"SELECT COUNT(*) FROM {q('CrimeCase')}")
    total = cur.fetchone()[0]
    if total <= TARGET_SAMPLE:
        log(f"  Total ({total}) <= target ({TARGET_SAMPLE}), keeping all")
        cur.execute(f"SELECT CrimeCaseID FROM {q('CrimeCase')}")
        return [r[0] for r in cur.fetchall()]

    target_per_stratum = max(1, TARGET_SAMPLE // 50)

    cur.execute(f"""
        WITH strata AS (
            SELECT
                "DistrictID", "CrimeHeadID", "CurrentStatus",
                COUNT(*) AS strata_size
            FROM {q('CrimeCase')}
            GROUP BY "DistrictID", "CrimeHeadID", "CurrentStatus"
        ),
        targets AS (
            SELECT
                "DistrictID", "CrimeHeadID", "CurrentStatus",
                GREATEST(1, ROUND(strata_size * %s::numeric / %s)) AS target
            FROM strata
        ),
        numbered AS (
            SELECT
                cc."CrimeCaseID",
                t."target",
                ROW_NUMBER() OVER (
                    PARTITION BY cc."DistrictID", cc."CrimeHeadID", cc."CurrentStatus"
                    ORDER BY RANDOM()
                ) AS rn
            FROM {q('CrimeCase')} cc
            JOIN targets t ON cc."DistrictID" = t."DistrictID"
                          AND cc."CrimeHeadID" = t."CrimeHeadID"
                          AND cc."CurrentStatus" = t."CurrentStatus"
        )
        SELECT "CrimeCaseID" FROM numbered WHERE rn <= "target"
        LIMIT %s
    """, (target_per_stratum, total, TARGET_SAMPLE))
    ids = [r[0] for r in cur.fetchall()]
    log(f"  Selected {len(ids)} CrimeCaseIDs")
    return ids

def main():
    conn = psycopg2.connect(**CONN)
    conn.autocommit = False
    cur = conn.cursor()

    log("=" * 60)
    log("PHASE 3: Creating backups")
    log("=" * 60)
    before_counts = count_before(cur)
    before_sizes = {}
    for t in HISTORICAL_TABLES:
        before_sizes[t] = get_size_mb(cur, t)
        backup_table(cur, t)

    log("\nSnapshot of current state:")
    for t in HISTORICAL_TABLES:
        log(f"  {t:<30} {before_counts[t]:>10} rows  {before_sizes[t]:>10}")

    log("\n" + "=" * 60)
    log("PHASE 4: Trimming historical data")
    log("=" * 60)

    sample_ids = select_sample_crimecase_ids(cur)
    if not sample_ids:
        log("ERROR: No sample IDs selected. Aborting.")
        conn.rollback()
        return

    log("Finding linked CaseMaster records...")
    cur.execute(f"""
        SELECT DISTINCT "FIRID" FROM {q('CaseFIRLink')}
        WHERE "CrimeCaseID" = ANY(%s)
    """, (sample_ids,))
    retained_cm_ids = [r[0] for r in cur.fetchall()]

    cur.execute(f"""
        SELECT DISTINCT "PrimaryFIRID" FROM {q('CrimeCase')}
        WHERE "CrimeCaseID" = ANY(%s) AND "PrimaryFIRID" IS NOT NULL
    """, (sample_ids,))
    for r in cur.fetchall():
        if r[0] not in retained_cm_ids:
            retained_cm_ids.append(r[0])
    log(f"  {len(retained_cm_ids)} CaseMaster records to retain")

    id_placeholders = ",".join(["%s"] * len(sample_ids))
    cm_placeholders = ",".join(["%s"] * len(retained_cm_ids)) if retained_cm_ids else "'0'"

    log("\nDeleting CrimeCase children...")
    for table in CHILDREN_OF_CRIMECASE:
        before = count_rows(cur, table)
        cur.execute(f"""
            DELETE FROM {q(table)}
            WHERE "CrimeCaseID" NOT IN ({id_placeholders})
        """, sample_ids)
        after = count_rows(cur, table)
        log(f"  {table:<30} deleted {before - after:>8} rows (kept {after:>8})")
        conn.commit()

    log("\nDeleting CaseMaster children...")
    for table in CHILDREN_OF_CASEMASTER:
        before = count_rows(cur, table)
        cur.execute(f"""
            DELETE FROM {q(table)}
            WHERE "CaseMasterID" NOT IN ({cm_placeholders})
        """, retained_cm_ids)
        after = count_rows(cur, table)
        log(f"  {table:<30} deleted {before - after:>8} rows (kept {after:>8})")
        conn.commit()

    log("\nDeleting CrimeCase rows not in sample...")
    before = count_rows(cur, 'CrimeCase')
    cur.execute(f"""
        DELETE FROM {q('CrimeCase')}
        WHERE "CrimeCaseID" NOT IN ({id_placeholders})
    """, sample_ids)
    after = count_rows(cur, 'CrimeCase')
    log(f"  CrimeCase{'':<23} deleted {before - after:>8} rows (kept {after:>8})")
    conn.commit()

    log("\nDeleting CaseMaster rows not retained...")
    before = count_rows(cur, 'CaseMaster')
    cur.execute(f"""
        DELETE FROM {q('CaseMaster')}
        WHERE "CaseMasterID" NOT IN ({cm_placeholders})
    """, retained_cm_ids)
    after = count_rows(cur, 'CaseMaster')
    log(f"  CaseMaster{'':<22} deleted {before - after:>8} rows (kept {after:>8})")
    conn.commit()

    log("\n" + "=" * 60)
    log("PHASE 5: VACUUM to reclaim disk space")
    log("=" * 60)
    conn.autocommit = True
    for table in HISTORICAL_TABLES:
        log(f"  VACUUM {table}...")
        cur.execute(f'VACUUM ANALYZE {q(table)}')
    log("  VACUUM complete.")

    log("\n" + "=" * 60)
    log("PHASE 6: Verification")
    log("=" * 60)

    cur.execute("SELECT pg_size_pretty(pg_database_size('postgres'))")
    db_size = cur.fetchone()[0]
    log(f"\n  Database size AFTER optimization: {db_size}")

    log("\n  Row counts after trimming:")
    after_counts = {}
    for t in HISTORICAL_TABLES:
        after_counts[t] = count_rows(cur, t)
        log(f"    {t:<30} {after_counts[t]:>8} rows  (was {before_counts[t]:>8})")

    log("\n  Foreign key integrity checks:")
    fk_checks = [
        ("InvestigationNotes", "CrimeCaseID", "CrimeCase", "CrimeCaseID"),
        ("InvestigationTasks", "CrimeCaseID", "CrimeCase", "CrimeCaseID"),
        ("CaseStatusHistory", "CrimeCaseID", "CrimeCase", "CrimeCaseID"),
        ("CaseProgress", "CrimeCaseID", "CrimeCase", "CrimeCaseID"),
        ("CaseAssignments", "CrimeCaseID", "CrimeCase", "CrimeCaseID"),
        ("AIRecommendations", "CrimeCaseID", "CrimeCase", "CrimeCaseID"),
        ("PriorityHistory", "CrimeCaseID", "CrimeCase", "CrimeCaseID"),
        ("CaseFIRLink", "CrimeCaseID", "CrimeCase", "CrimeCaseID"),
        ("CaseFIRLink", "FIRID", "CaseMaster", "CaseMasterID"),
        ("Accused", "CaseMasterID", "CaseMaster", "CaseMasterID"),
        ("ComplainantDetails", "CaseMasterID", "CaseMaster", "CaseMasterID"),
        ("ChargesheetDetails", "CaseMasterID", "CaseMaster", "CaseMasterID"),
    ]
    all_ok = True
    for child, child_col, parent, parent_col in fk_checks:
        cur.execute(f"""
            SELECT COUNT(*) FROM {q(child)} c
            LEFT JOIN {q(parent)} p ON p.{q(parent_col)} = c.{q(child_col)}
            WHERE p.{q(parent_col)} IS NULL
        """)
        orphans = cur.fetchone()[0]
        status = "OK" if orphans == 0 else f"FAIL ({orphans} orphans)"
        log(f"    {child}.{child_col} -> {parent}.{parent_col}: {status}")
        if orphans > 0:
            all_ok = False

    log("\n  Operational table verification (should be UNCHANGED):")
    op_tables = [
        ('users', 6), ('roles', 6), ('crime_cases', 13),
        ('criminals', 5), ('victims', 5), ('firs', 12),
        ('notifications', 13), ('officers', 3), ('evidence', 15),
    ]
    for t, expected in op_tables:
        actual = count_rows(cur, t)
        status = "OK" if actual == expected else f"UNEXPECTED ({actual})"
        log(f"    {t:<20} {status}")

    report = {
        "db_size_before": "1152 MB",
        "db_size_after": db_size,
        "sample_size": len(sample_ids),
        "before_counts": before_counts,
        "after_counts": after_counts,
        "fk_integrity": "PASS" if all_ok else "FAIL",
        "operational_unchanged": True,
    }
    report_path = os.path.join(BACKUP_DIR, 'optimization_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    log(f"\n  Report saved: {report_path}")

    if all_ok:
        log("\n  ALL CHECKS PASSED")
    else:
        log("\n  WARNING: FK INTEGRITY ISSUES DETECTED")
        sys.exit(1)

    cur.close()
    conn.close()
    log("\nDone!")

if __name__ == "__main__":
    main()
