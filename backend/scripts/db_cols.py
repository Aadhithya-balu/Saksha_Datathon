import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _db_config import CONN
import psycopg2
conn = psycopg2.connect(**CONN)
cur = conn.cursor()
for t in ['CrimeCase', 'CaseMaster', 'CaseFIRLink', 'CaseStatusHistory']:
    cur.execute(f"""SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = '{t}' AND table_schema = 'public' ORDER BY ordinal_position""")
    print(f"\n=== {t} ===")
    for r in cur.fetchall():
        print(f"  {r[0]:<35} {r[1]}")
conn.close()
