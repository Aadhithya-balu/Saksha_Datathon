"""
Full database import from SQL dump into a new Supabase project.

Usage:
  1. Create a new Supabase project
  2. Get your connection string from Settings > Database > Connection string > URI
  3. Update CONN below with your new credentials
  4. py -3.12 scripts/db_import_full.py

Input: backups/saksha_full_dump.sql
"""
import psycopg2
import os
import sys
import time

# ============================================================
# UPDATE THESE with your NEW Supabase project credentials
# Get from: Supabase Dashboard > Settings > Database > Connection string > URI
# ============================================================
CONN = dict(
    host='aws-0-ap-northeast-1.pooler.supabase.com',
    port=6543, dbname='postgres',
    user='postgres.tqaegfrnnddfqshwdkvh',
    password='datathon2026', sslmode='require',
    connect_timeout=15,
)

BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', 'backups')
DUMP_FILE = os.path.join(BACKUP_DIR, 'saksha_full_dump.sql')

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def connect_with_retry(max_attempts=30, delay=10):
    for i in range(max_attempts):
        try:
            c = psycopg2.connect(**CONN)
            cur = c.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            return c
        except Exception as e:
            log(f"Connect attempt {i+1}: {str(e)[:70]}")
            time.sleep(delay)
    return None

def main():
    if not os.path.exists(DUMP_FILE):
        log(f"ERROR: Dump file not found: {DUMP_FILE}")
        log("Run db_export_full.py first.")
        sys.exit(1)

    size_mb = os.path.getsize(DUMP_FILE) / (1024 * 1024)
    log(f"Dump file: {DUMP_FILE} ({size_mb:.1f} MB)")

    log("Connecting to target database...")
    conn = connect_with_retry()
    if not conn:
        log("FAILED to connect.")
        sys.exit(1)

    log("Connected! Importing...")
    cur = conn.cursor()

    # Read and execute the dump file
    with open(DUMP_FILE, 'r', encoding='utf-8') as f:
        sql = f.read()

    try:
        cur.execute(sql)
        conn.commit()
        log("Import completed successfully!")
    except Exception as e:
        conn.rollback()
        log(f"ERROR during import: {e}")
        log("Trying line-by-line import...")

        # Fallback: execute line by line
        lines = sql.split('\n')
        in_copy = False
        copy_buffer = []
        errors = 0
        for i, line in enumerate(lines):
            try:
                if line.startswith('COPY '):
                    in_copy = True
                    copy_buffer = [line]
                    continue
                if in_copy:
                    copy_buffer.append(line)
                    if line.strip() == '\\.':
                        in_copy = False
                        copy_sql = '\n'.join(copy_buffer)
                        cur.execute(copy_sql)
                        conn.commit()
                        copy_buffer = []
                    continue
                stripped = line.strip()
                if not stripped or stripped.startswith('--'):
                    continue
                if stripped.endswith(';'):
                    cur.execute(stripped.rstrip(';'))
                    conn.commit()
            except Exception as e2:
                errors += 1
                if errors <= 10:
                    log(f"  Line {i+1} error: {str(e2)[:80]}")
                conn.rollback()

        log(f"Import done with {errors} errors.")

    # Verify
    log("\nVerifying import...")
    cur.execute("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public' ORDER BY tablename
    """)
    tables = [r[0] for r in cur.fetchall()]
    log(f"Tables found: {len(tables)}")

    for t in tables:
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            cnt = cur.fetchone()[0]
            log(f"  {t}: {cnt} rows")
        except:
            log(f"  {t}: ERROR")

    cur.execute("SELECT pg_size_pretty(pg_database_size('postgres'))")
    log(f"\nFinal DB size: {cur.fetchone()[0]}")

    cur.close()
    conn.close()
    log("\nDone!")

if __name__ == "__main__":
    main()
