"""
Persistent reconnect script. Keeps trying every 30s.
When connected, runs export, then trim, then verifies.
Run with: py -3.12 scripts/db_auto_resume.py
"""
import psycopg2, time, sys, os

BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def connect():
    return psycopg2.connect(
        host='aws-0-ap-northeast-1.pooler.supabase.com',
        port=6543, dbname='postgres',
        user='postgres.tqaegfrnnddfqshwdkvh',
        password='datathon2026', sslmode='require',
        connect_timeout=10
    )

def q(t):
    return f'"{t}"'

def count_rows(cur, t):
    cur.execute(f'SELECT COUNT(*) FROM {q(t)}')
    return cur.fetchone()[0]

def safe_exec(cur, conn, sql, params=None):
    try:
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        log(f"  ERROR: {e}")
        return False

log("Waiting 2 min for Supabase recovery...")
time.sleep(120)

# STEP 1: Connect
conn = None
for attempt in range(180):
    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        log(f"CONNECTED on attempt {attempt+1}!")
        break
    except Exception as e:
        if attempt % 10 == 0:
            log(f"[{attempt+1}] {str(e)[:60]}")
        time.sleep(30)
        conn = None

if not conn:
    log("FAILED after 90 minutes. Please check Supabase dashboard.")
    sys.exit(1)

cur = conn.cursor()

# STEP 2: Check current state
log("Checking current state...")
cur.execute("SELECT pg_size_pretty(pg_database_size('postgres'))")
log(f"DB size: {cur.fetchone()[0]}")

HIST = ['InvestigationNotes','InvestigationTasks','CaseStatusHistory','AIRecommendations',
        'CaseProgress','CaseAssignments','PriorityHistory','CaseTimeline',
        'Accused','ComplainantDetails','ChargesheetDetails',
        'ArrestSurrender','Victim','ActSectionAssociation',
        'CaseFIRLink','CrimeCase','CaseMaster']

states = {}
for t in HIST:
    try:
        states[t] = count_rows(cur, t)
        log(f"  {t}: {states[t]}")
    except Exception as e:
        states[t] = -1
        log(f"  {t}: ERROR - {e}")

# STEP 3: Full dump for backup
log("\nCreating full SQL dump backup...")
try:
    import db_export_full
    db_export_full.main()
    log("Full dump complete!")
except Exception as e:
    log(f"Dump failed: {e}. Continuing with trim...")

# STEP 4: Determine what still needs trimming
needs_trim = False
for t in HIST:
    if states[t] > 10000:
        needs_trim = True
        break

if not needs_trim:
    log("All historical tables already trimmed!")
else:
    log("Trimming remaining tables...")

    # Get CrimeCase count
    cc_count = count_rows(cur, 'CrimeCase')
    log(f"CrimeCase: {cc_count} rows")

    if cc_count > 5000:
        # Select sample
        ratio = 5000 / cc_count
        cur.execute(f"""
            WITH strata AS (
                SELECT "DistrictID","CrimeHeadID","CurrentStatus", COUNT(*) AS sz
                FROM {q('CrimeCase')} GROUP BY "DistrictID","CrimeHeadID","CurrentStatus"
            ), targets AS (
                SELECT "DistrictID","CrimeHeadID","CurrentStatus",
                       GREATEST(1, ROUND(sz * %s::numeric)) AS tgt FROM strata
            ), numbered AS (
                SELECT cc."CrimeCaseID",
                       ROW_NUMBER() OVER (PARTITION BY cc."DistrictID",cc."CrimeHeadID",cc."CurrentStatus" ORDER BY RANDOM()) AS rn,
                       t.tgt
                FROM {q('CrimeCase')} cc JOIN targets t ON cc."DistrictID"=t."DistrictID" AND cc."CrimeHeadID"=t."CrimeHeadID" AND cc."CurrentStatus"=t."CurrentStatus"
            )
            SELECT "CrimeCaseID" FROM numbered WHERE rn <= tgt LIMIT 5000
        """, (ratio,))
        sample_ids = [r[0] for r in cur.fetchall()]
        log(f"Sample: {len(sample_ids)} CrimeCaseIDs")
    else:
        cur.execute(f'SELECT "CrimeCaseID" FROM {q("CrimeCase")}')
        sample_ids = [r[0] for r in cur.fetchall()]
        log(f"Keeping all {len(sample_ids)} CrimeCaseIDs")

    if not sample_ids:
        log("ERROR: No sample IDs!")
        sys.exit(1)

    id_ph = ",".join(["%s"]*len(sample_ids))

    # Linked CaseMaster
    cur.execute(f'SELECT DISTINCT "FIRID" FROM {q("CaseFIRLink")} WHERE "CrimeCaseID" IN ({id_ph})', sample_ids)
    cm_ids = [r[0] for r in cur.fetchall()]
    cur.execute(f'SELECT DISTINCT "PrimaryFIRID" FROM {q("CrimeCase")} WHERE "CrimeCaseID" IN ({id_ph}) AND "PrimaryFIRID" IS NOT NULL', sample_ids)
    for r in cur.fetchall():
        if r[0] not in cm_ids:
            cm_ids.append(r[0])
    cm_ph = ",".join(["%s"]*len(cm_ids)) if cm_ids else "'0'"
    log(f"CaseMaster to retain: {len(cm_ids)}")

    # Delete CrimeCase children (one table at a time, commit each)
    CC_CHILDREN = ['InvestigationNotes','InvestigationTasks','CaseStatusHistory',
                   'AIRecommendations','CaseProgress','CaseAssignments',
                   'PriorityHistory','CaseTimeline','CaseFIRLink']

    conn.autocommit = False
    for t in CC_CHILDREN:
        if states.get(t, 0) <= 10000:
            log(f"  {t}: already trimmed, skipping")
            continue
        before = count_rows(cur, t)
        if safe_exec(cur, conn, f'DELETE FROM {q(t)} WHERE "CrimeCaseID" NOT IN ({id_ph})', sample_ids):
            after = count_rows(cur, t)
            log(f"  {t}: {before} -> {after}")
        else:
            log(f"  {t}: FAILED, retrying with smaller batches...")
            conn.autocommit = True
            time.sleep(5)
            conn.autocommit = False
            try:
                cur.execute(f'SELECT "CrimeCaseID" FROM {q(t)} WHERE "CrimeCaseID" NOT IN ({id_ph}) LIMIT 10000', sample_ids)
                batch_ids = [r[0] for r in cur.fetchall()]
                while batch_ids:
                    bph = ",".join(["%s"]*len(batch_ids))
                    cur.execute(f'DELETE FROM {q(t)} WHERE "CrimeCaseID" IN ({bph})', batch_ids)
                    conn.commit()
                    cur.execute(f'SELECT "CrimeCaseID" FROM {q(t)} WHERE "CrimeCaseID" NOT IN ({id_ph}) LIMIT 10000', sample_ids)
                    batch_ids = [r[0] for r in cur.fetchall()]
                log(f"  {t}: retry complete, now {count_rows(cur, t)} rows")
            except Exception as e:
                conn.rollback()
                log(f"  {t}: retry also failed: {e}")

    # Delete CaseMaster children
    CM_CHILDREN = ['Accused','ComplainantDetails','ChargesheetDetails',
                   'ArrestSurrender','Victim','ActSectionAssociation']
    for t in CM_CHILDREN:
        if states.get(t, 0) == 0:
            log(f"  {t}: already empty, skipping")
            continue
        before = count_rows(cur, t)
        if safe_exec(cur, conn, f'DELETE FROM {q(t)} WHERE "CaseMasterID" NOT IN ({cm_ph})', cm_ids):
            after = count_rows(cur, t)
            log(f"  {t}: {before} -> {after}")

    # Delete CrimeCase
    before = count_rows(cur, 'CrimeCase')
    safe_exec(cur, conn, f'DELETE FROM {q("CrimeCase")} WHERE "CrimeCaseID" NOT IN ({id_ph})', sample_ids)
    after = count_rows(cur, 'CrimeCase')
    log(f"CrimeCase: {before} -> {after}")

    # Delete CaseMaster
    before = count_rows(cur, 'CaseMaster')
    safe_exec(cur, conn, f'DELETE FROM {q("CaseMaster")} WHERE "CaseMasterID" NOT IN ({cm_ph})', cm_ids)
    after = count_rows(cur, 'CaseMaster')
    log(f"CaseMaster: {before} -> {after}")

# STEP 5: VACUUM
log("\nVACUUMing...")
conn.autocommit = True
for t in HIST:
    try:
        cur.execute(f'VACUUM ANALYZE {q(t)}')
        log(f"  {t} OK")
    except Exception as e:
        log(f"  {t}: {e}")

# STEP 6: Verify
cur.execute("SELECT pg_size_pretty(pg_database_size('postgres'))")
log(f"\nFINAL DB SIZE: {cur.fetchone()[0]}")

log("\nFinal row counts:")
for t in HIST:
    try:
        log(f"  {t}: {count_rows(cur, t)}")
    except:
        pass

log("\nOperational tables:")
for t in ['users','roles','crime_cases','criminals','victims','firs','notifications','officers','evidence']:
    try:
        log(f"  {t}: {count_rows(cur, t)}")
    except:
        pass

# FK integrity
log("\nFK integrity:")
fks = [
    ("InvestigationNotes","CrimeCaseID","CrimeCase","CrimeCaseID"),
    ("InvestigationTasks","CrimeCaseID","CrimeCase","CrimeCaseID"),
    ("CaseStatusHistory","CrimeCaseID","CrimeCase","CrimeCaseID"),
    ("CaseProgress","CrimeCaseID","CrimeCase","CrimeCaseID"),
    ("CaseAssignments","CrimeCaseID","CrimeCase","CrimeCaseID"),
    ("AIRecommendations","CrimeCaseID","CrimeCase","CrimeCaseID"),
    ("PriorityHistory","CrimeCaseID","CrimeCase","CrimeCaseID"),
    ("CaseFIRLink","CrimeCaseID","CrimeCase","CrimeCaseID"),
    ("CaseFIRLink","FIRID","CaseMaster","CaseMasterID"),
    ("Accused","CaseMasterID","CaseMaster","CaseMasterID"),
    ("ComplainantDetails","CaseMasterID","CaseMaster","CaseMasterID"),
    ("ChargesheetDetails","CaseMasterID","CaseMaster","CaseMasterID"),
]
for child, cc, parent, pc in fks:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {q(child)} c LEFT JOIN {q(parent)} p ON p.{q(pc)}=c.{q(cc)} WHERE p.{q(pc)} IS NULL')
        orphans = cur.fetchone()[0]
        status = "OK" if orphans == 0 else f"FAIL ({orphans})"
        log(f"  {child}.{cc} -> {parent}.{pc}: {status}")
    except Exception as e:
        log(f"  {child}.{cc} -> {parent}.{pc}: ERROR - {e}")

cur.close()
conn.close()
log("\nALL DONE!")
