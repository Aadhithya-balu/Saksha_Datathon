import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _db_config import CONN
import psycopg2

for attempt in range(3):
    try:
        conn = psycopg2.connect(**CONN, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        print("CONNECTED")
        cur.execute("SELECT pg_size_pretty(pg_database_size('postgres'))")
        print("DB size:", cur.fetchone()[0])
        tables = ['InvestigationNotes','InvestigationTasks','CaseStatusHistory','AIRecommendations','CaseProgress','CaseAssignments','PriorityHistory','CrimeCase','CaseMaster','CaseFIRLink','Accused','ComplainantDetails','ChargesheetDetails','users','crime_cases','notifications']
        for t in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            print(f'  {t}: {cur.fetchone()[0]}')
        cur.close(); conn.close()
        sys.exit(0)
    except Exception as e:
        print(f"Attempt {attempt+1}: {e}")
        time.sleep(10)
print("STILL DOWN")
