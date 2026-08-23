import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _db_config import CONN
import psycopg2

ATTEMPTS = 300  # try for up to 75 min
DELAY = 15

# Try multiple SSL modes
SSL_MODES = ['require', 'prefer', 'disable']

for attempt in range(ATTEMPTS):
    for sslmode in SSL_MODES:
        try:
            cfg = {**CONN, 'sslmode': sslmode, 'connect_timeout': 10}
            conn = psycopg2.connect(**cfg)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            print(f"\nCONNECTED (attempt {attempt+1}, ssl={sslmode})!", flush=True)
            cur.execute("SELECT pg_size_pretty(pg_database_size('postgres'))")
            print(f"DB size: {cur.fetchone()[0]}", flush=True)
            cur.close()
            conn.close()
            print("READY", flush=True)
            sys.exit(0)
        except Exception:
            pass
    if attempt % 20 == 0:
        print(f"[{attempt+1}/{ATTEMPTS}] still trying...", flush=True)
    time.sleep(DELAY)

print("GAVE UP", flush=True)
sys.exit(1)
