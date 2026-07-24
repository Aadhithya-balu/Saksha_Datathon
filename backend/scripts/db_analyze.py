"""Analyze PostgreSQL database storage for Saksha optimization."""
import psycopg2

CONN = dict(
    host='aws-0-ap-northeast-1.pooler.supabase.com',
    port=6543,
    dbname='postgres',
    user='postgres.tqaegfrnnddfqshwdkvh',
    password='datathon2026',
    sslmode='require',
)

def safe_count(cur, tname):
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{tname}"')
        return cur.fetchone()[0]
    except Exception:
        return -1

def safe_size(cur, tname):
    """Get size of a table, return (total_size_pretty, table_size_pretty, index_size_pretty, total_bytes)."""
    try:
        cur.execute(f"SELECT pg_size_pretty(pg_total_relation_size('public.\"{tname}\"'))")
        total = cur.fetchone()[0]
        cur.execute(f"SELECT pg_size_pretty(pg_relation_size('public.\"{tname}\"'))")
        table = cur.fetchone()[0]
        cur.execute(f"SELECT pg_size_pretty(pg_indexes_size('public.\"{tname}\"'))")
        idx = cur.fetchone()[0]
        cur.execute(f"SELECT pg_total_relation_size('public.\"{tname}\"')")
        total_bytes = cur.fetchone()[0]
        return total, table, idx, total_bytes or 0
    except Exception as e:
        return f"ERR", "ERR", "ERR", 0

def main():
    conn = psycopg2.connect(**CONN)
    cur = conn.cursor()

    cur.execute("SELECT pg_size_pretty(pg_database_size('postgres'))")
    db_size = cur.fetchone()[0]
    print(f"=== TOTAL DATABASE SIZE: {db_size} ===\n")

    # Get table names from pg_tables first
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
    table_names = [r[0] for r in cur.fetchall()]

    # Get sizes one by one to handle errors
    tables = []
    for tname in table_names:
        total, table_s, idx_s, total_bytes = safe_size(cur, tname)
        tables.append((tname, total, table_s, idx_s, total_bytes))

    # Sort by total_bytes descending
    tables.sort(key=lambda x: x[4], reverse=True)

    print(f"{'Table':<40} {'Total':>10} {'Data':>10} {'Index':>10} {'Bytes':>12}")
    print("-" * 85)
    total_bytes = 0
    for t in tables:
        total_bytes += t[4]
        print(f"{t[0]:<40} {t[1]:>10} {t[2]:>10} {t[3]:>10} {t[4]:>12}")
    print("-" * 85)
    print(f"{'TOTAL':<40} {'':>10} {'':>10} {'':>10} {total_bytes:>12}\n")

    print("=== EXACT ROW COUNTS ===")
    rows_data = []
    for t in tables:
        tname = t[0]
        count = safe_count(cur, tname)
        pct = (t[4] / total_bytes * 100) if total_bytes > 0 and t[4] > 0 else 0
        rows_data.append({"table": tname, "rows": count, "total_size": t[1], "total_bytes": t[4], "pct": pct})
        status = f"{count:>8} rows" if count >= 0 else "   ERROR"
        print(f"  {tname:<40} {status}  ({pct:.1f}%)")

    print("\n=== FOREIGN KEY RELATIONSHIPS ===")
    cur.execute("""
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table,
            ccu.column_name AS foreign_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
        ORDER BY tc.table_name
    """)
    fks = cur.fetchall()
    for fk in fks:
        print(f"  {fk[0]}.{fk[1]} -> {fk[2]}.{fk[3]}")

    print("\n=== DATE RANGES (created_at) ===")
    for t in tables:
        tname = t[0]
        try:
            cur.execute(f'SELECT MIN(created_at), MAX(created_at), COUNT(*) FROM "{tname}" WHERE created_at IS NOT NULL')
            r = cur.fetchone()
            if r and r[0]:
                print(f"  {tname:<40} {r[0]} to {r[1]}  ({r[2]} rows)")
        except Exception:
            pass

    print("\n=== CANDIDATES FOR TRIMMING (>100 rows, >1% of DB) ===")
    for rd in rows_data:
        if rd["rows"] > 100 and rd["pct"] > 1.0:
            print(f"  {rd['table']:<40} {rd['rows']:>8} rows  {rd['total_size']:>10} ({rd['pct']:.1f}%)")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
