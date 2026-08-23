import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _db_config import CONN
import psycopg2

BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', 'backups')

def connect():
    return psycopg2.connect(**CONN, keepalives=1, keepalives_idle=5, keepalives_interval=5, keepalives_count=3)

def q(t):
    return f'"{t}"'

def count_rows(cur, t):
    cur.execute(f'SELECT COUNT(*) FROM {q(t)}')
    return cur.fetchone()[0]

# Keep trying to connect
print("Attempting to connect to Supabase...", flush=True)
conn = None
for attempt in range(120):
    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        print(f"\nCONNECTED on attempt {attempt+1}!", flush=True)
        break
    except Exception as e:
        err = str(e)[:60]
        print(f"[{attempt+1}] {err}", flush=True)
        time.sleep(15)
        conn = None

if not conn:
    print("\nCould not connect after 30 minutes. Supabase may need manual restart.", flush=True)
    sys.exit(1)

cur = conn.cursor()
cur.execute("SELECT pg_size_pretty(pg_database_size('postgres'))")
print(f"\nDB size: {cur.fetchone()[0]}", flush=True)

# Check current state
HIST = ['InvestigationNotes','InvestigationTasks','CaseStatusHistory','AIRecommendations',
        'CaseProgress','CaseAssignments','PriorityHistory','CaseTimeline',
        'Accused','ComplainantDetails','ChargesheetDetails',
        'ArrestSurrender','Victim','ActSectionAssociation',
        'CaseFIRLink','CrimeCase','CaseMaster']
print("\nCurrent state:", flush=True)
for t in HIST:
    try:
        print(f"  {t}: {count_rows(cur, t)} rows", flush=True)
    except Exception as e:
        print(f"  {t}: ERROR - {e}", flush=True)

# Check what's done vs what remains
cc = count_rows(cur, 'CrimeCase')
print(f"\nCrimeCase: {cc} rows (target: ~5000)", flush=True)

if cc <= 10000:
    print("CrimeCase already trimmed. Checking remaining tables...", flush=True)
else:
    print("CrimeCase NOT yet trimmed. Running full trim now...", flush=True)
    # Resume the trim from where we left off
    # First check what CrimeCase children still need trimming
    CHILDREN = ['InvestigationNotes','InvestigationTasks','CaseStatusHistory',
                'AIRecommendations','CaseProgress','CaseAssignments',
                'PriorityHistory','CaseTimeline','CaseFIRLink']
    CM_CHILDREN = ['Accused','ComplainantDetails','ChargesheetDetails',
                   'ArrestSurrender','Victim','ActSectionAssociation']

    # Check which CrimeCase children are already small (trimmed)
    needs_trim = []
    for t in CHILDREN:
        cnt = count_rows(cur, t)
        if cnt > 10000:
            needs_trim.append(t)
            print(f"  NEEDS TRIM: {t} ({cnt} rows)", flush=True)
        else:
            print(f"  OK: {t} ({cnt} rows)", flush=True)

    if needs_trim:
        # Select sample
        cur.execute(f"SELECT COUNT(*) FROM {q('CrimeCase')}")
        total = cur.fetchone()[0]
        target_ratio = 5000 / total if total > 5000 else 1

        print(f"\nSelecting stratified sample ({total} total, ratio={target_ratio:.4f})...", flush=True)
        cur.execute(f"""
            WITH strata AS (
                SELECT "DistrictID","CrimeHeadID","CurrentStatus", COUNT(*) AS sz
                FROM {q('CrimeCase')} GROUP BY "DistrictID","CrimeHeadID","CurrentStatus"
            ), targets AS (
                SELECT "DistrictID","CrimeHeadID","CurrentStatus",
                       GREATEST(1, ROUND(sz * %s::numeric)) AS tgt
                FROM strata
            ), numbered AS (
                SELECT cc."CrimeCaseID",
                       ROW_NUMBER() OVER (PARTITION BY cc."DistrictID",cc."CrimeHeadID",cc."CurrentStatus" ORDER BY RANDOM()) AS rn,
                       t.tgt
                FROM {q('CrimeCase')} cc JOIN targets t ON cc."DistrictID"=t."DistrictID" AND cc."CrimeHeadID"=t."CrimeHeadID" AND cc."CurrentStatus"=t."CurrentStatus"
            )
            SELECT "CrimeCaseID" FROM numbered WHERE rn <= tgt LIMIT 5000
        """, (target_ratio,))
        sample_ids = [r[0] for r in cur.fetchall()]
        print(f"Selected {len(sample_ids)} CrimeCaseIDs", flush=True)

        # Get linked CaseMaster IDs
        id_ph = ",".join(["%s"]*len(sample_ids))
        cur.execute(f'SELECT DISTINCT "FIRID" FROM {q("CaseFIRLink")} WHERE "CrimeCaseID" IN ({id_ph})', sample_ids)
        cm_ids = [r[0] for r in cur.fetchall()]
        cur.execute(f'SELECT DISTINCT "PrimaryFIRID" FROM {q("CrimeCase")} WHERE "CrimeCaseID" IN ({id_ph}) AND "PrimaryFIRID" IS NOT NULL', sample_ids)
        for r in cur.fetchall():
            if r[0] not in cm_ids:
                cm_ids.append(r[0])
        print(f"Linked CaseMaster: {len(cm_ids)}", flush=True)
        cm_ph = ",".join(["%s"]*len(cm_ids)) if cm_ids else "'0'"

        # Delete children one by one with commits
        conn.autocommit = False
        for t in needs_trim:
            before = count_rows(cur, t)
            cur.execute(f'DELETE FROM {q(t)} WHERE "CrimeCaseID" NOT IN ({id_ph})', sample_ids)
            after = count_rows(cur, t)
            conn.commit()
            print(f"  {t}: {before} -> {after} (deleted {before-after})", flush=True)

        # Delete CaseMaster children
        for t in CM_CHILDREN:
            try:
                before = count_rows(cur, t)
                cur.execute(f'DELETE FROM {q(t)} WHERE "CaseMasterID" NOT IN ({cm_ph})', cm_ids)
                after = count_rows(cur, t)
                conn.commit()
                print(f"  {t}: {before} -> {after} (deleted {before-after})", flush=True)
            except Exception as e:
                conn.rollback()
                print(f"  {t}: SKIP - {e}", flush=True)

        # Delete CrimeCase
        before = count_rows(cur, 'CrimeCase')
        cur.execute(f'DELETE FROM {q("CrimeCase")} WHERE "CrimeCaseID" NOT IN ({id_ph})', sample_ids)
        after = count_rows(cur, 'CrimeCase')
        conn.commit()
        print(f"  CrimeCase: {before} -> {after}", flush=True)

        # Delete CaseMaster
        before = count_rows(cur, 'CaseMaster')
        cur.execute(f'DELETE FROM {q("CaseMaster")} WHERE "CaseMasterID" NOT IN ({cm_ph})', cm_ids)
        after = count_rows(cur, 'CaseMaster')
        conn.commit()
        print(f"  CaseMaster: {before} -> {after}", flush=True)

    # Delete PriorityHistory if still large
    ph = count_rows(cur, 'PriorityHistory')
    if ph > 10000:
        # Need sample_ids still
        if 'id_ph' not in dir():
            cur.execute(f"SELECT COUNT(*) FROM {q('CrimeCase')}")
            total = cur.fetchone()[0]
            target_ratio = 5000 / total if total > 5000 else 1
            cur.execute(f"""
                WITH strata AS (
                    SELECT "DistrictID","CrimeHeadID","CurrentStatus", COUNT(*) AS sz
                    FROM {q('CrimeCase')} GROUP BY "DistrictID","CrimeHeadID","CurrentStatus"
                ), targets AS (
                    SELECT "DistrictID","CrimeHeadID","CurrentStatus",
                           GREATEST(1, ROUND(sz * %s::numeric)) AS tgt FROM strata
                ), numbered AS (
                    SELECT cc."CrimeCaseID",
                           ROW_NUMBER() OVER (PARTITION BY cc."DistrictID",cc."CrimeHeadID",cc."CurrentStatus" ORDER BY RANDOM()) AS rn, t.tgt
                    FROM {q('CrimeCase')} cc JOIN targets t ON cc."DistrictID"=t."DistrictID" AND cc."CrimeHeadID"=t."CrimeHeadID" AND cc."CurrentStatus"=t."CurrentStatus"
                )
                SELECT "CrimeCaseID" FROM numbered WHERE rn <= tgt LIMIT 5000
            """, (target_ratio,))
            sample_ids = [r[0] for r in cur.fetchall()]
            id_ph = ",".join(["%s"]*len(sample_ids))
        before = ph
        cur.execute(f'DELETE FROM {q("PriorityHistory")} WHERE "CrimeCaseID" NOT IN ({id_ph})', sample_ids)
        after = count_rows(cur, 'PriorityHistory')
        conn.commit()
        print(f"  PriorityHistory: {before} -> {after}", flush=True)

# VACUUM
print("\nVACUUMing...", flush=True)
conn.autocommit = True
for t in HIST:
    try:
        cur.execute(f'VACUUM ANALYZE {q(t)}')
        print(f"  VACUUM {t} OK", flush=True)
    except Exception as e:
        print(f"  VACUUM {t}: {e}", flush=True)

# Final verification
cur.execute("SELECT pg_size_pretty(pg_database_size('postgres'))")
final_size = cur.fetchone()[0]
print(f"\nFINAL DB SIZE: {final_size}", flush=True)

print("\nFinal row counts:", flush=True)
for t in HIST:
    try:
        print(f"  {t}: {count_rows(cur, t)} rows", flush=True)
    except Exception:
        pass

print("\nOperational tables:", flush=True)
for t in ['users','crime_cases','criminals','victims','firs','notifications','officers','evidence','roles']:
    try:
        print(f"  {t}: {count_rows(cur, t)} rows", flush=True)
    except Exception:
        pass

cur.close()
conn.close()
print("\nDONE!", flush=True)
