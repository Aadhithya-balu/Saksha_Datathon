import psycopg2, time, sys

ATTEMPTS = 300  # try for up to 75 min
DELAY = 15

# Try multiple connection methods
METHODS = [
    dict(host='aws-0-ap-northeast-1.pooler.supabase.com', port=6543, sslmode='require'),
    dict(host='aws-0-ap-northeast-1.pooler.supabase.com', port=6543, sslmode='prefer'),
    dict(host='aws-0-ap-northeast-1.pooler.supabase.com', port=6543, sslmode='disable'),
]

for attempt in range(ATTEMPTS):
    for mi, method in enumerate(METHODS):
        try:
            conn = psycopg2.connect(
                dbname='postgres',
                user='postgres.tqaegfrnnddfqshwdkvh',
                password='datathon2026',
                connect_timeout=10,
                **method
            )
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            print(f"\nCONNECTED (attempt {attempt+1}, method {mi+1})!", flush=True)
            cur.execute("SELECT pg_size_pretty(pg_database_size('postgres'))")
            print(f"DB size: {cur.fetchone()[0]}", flush=True)
            cur.close(); conn.close()
            print("READY", flush=True)
            sys.exit(0)
        except Exception as e:
            pass
    if attempt % 20 == 0:
        print(f"[{attempt+1}/{ATTEMPTS}] still trying...", flush=True)
    time.sleep(DELAY)

print("GAVE UP", flush=True)
sys.exit(1)
