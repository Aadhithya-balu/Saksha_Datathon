"""Deep analysis of historical tables for trimming strategy."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _db_config import CONN
import psycopg2

def main():
    conn = psycopg2.connect(**CONN)
    cur = conn.cursor()

    # CrimeCase distribution (the root of the historical hierarchy)
    print("=== CrimeCase DISTRIBUTION ===")
    print("\nBy DistrictID:")
    cur.execute("""
        SELECT d.DistrictName, COUNT(*) as cnt
        FROM CrimeCase c
        LEFT JOIN District d ON c.DistrictID = d.DistrictID
        GROUP BY d.DistrictName ORDER BY cnt DESC
    """)
    for r in cur.fetchall():
        print(f"  {str(r[0]):<40} {r[1]:>8}")

    print("\nBy CrimeHeadID (crime type):")
    cur.execute("""
        SELECT h.CrimeHeadName, COUNT(*) as cnt
        FROM CrimeCase c
        LEFT JOIN CrimeHead h ON c.CrimeHeadID = h.CrimeHeadID
        GROUP BY h.CrimeHeadName ORDER BY cnt DESC
    """)
    for r in cur.fetchall():
        print(f"  {str(r[0]):<40} {r[1]:>8}")

    print("\nBy Status:")
    cur.execute("""
        SELECT s.CaseStatusName, COUNT(*) as cnt
        FROM CrimeCase c
        LEFT JOIN CaseStatusMaster s ON c.CaseStatusID = s.CaseStatusID
        GROUP BY s.CaseStatusName ORDER BY cnt DESC
    """)
    for r in cur.fetchall():
        print(f"  {str(r[0]):<40} {r[1]:>8}")

    # Check if CrimeCase has a date column
    print("\nCrimeCase columns:")
    cur.execute("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = 'CrimeCase' AND table_schema = 'public'
        ORDER BY ordinal_position
    """)
    for r in cur.fetchall():
        print(f"  {r[0]:<35} {r[1]}")

    # CaseMaster distribution
    print("\n=== CaseMaster DISTRIBUTION ===")
    print("\nCaseMaster columns:")
    cur.execute("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = 'CaseMaster' AND table_schema = 'public'
        ORDER BY ordinal_position
    """)
    for r in cur.fetchall():
        print(f"  {r[0]:<35} {r[1]}")

    # Check linkage: how many CrimeCase rows have corresponding CaseMaster via CaseFIRLink
    print("\n=== LINKAGE: CrimeCase <-> CaseMaster via CaseFIRLink ===")
    cur.execute("""
        SELECT COUNT(DISTINCT c.CrimeCaseID)
        FROM CrimeCase c
        JOIN CaseFIRLink f ON c.CrimeCaseID = f.CrimeCaseID
    """)
    print(f"  CrimeCase rows linked via CaseFIRLink: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(DISTINCT CrimeCaseID) FROM CrimeCase")
    total_cc = cur.fetchone()[0]
    print(f"  Total CrimeCase rows: {total_cc}")

    # Check for orphaned records
    print("\n=== ORPHAN CHECK ===")
    for child_table, fk_col in [
        ('InvestigationNotes', 'CrimeCaseID'),
        ('InvestigationTasks', 'CrimeCaseID'),
        ('CaseStatusHistory', 'CrimeCaseID'),
        ('CaseProgress', 'CrimeCaseID'),
        ('CaseAssignments', 'CrimeCaseID'),
        ('AIRecommendations', 'CrimeCaseID'),
        ('PriorityHistory', 'CrimeCaseID'),
    ]:
        cur.execute(f"""
            SELECT COUNT(*) FROM {child_table} c
            WHERE NOT EXISTS (SELECT 1 FROM CrimeCase cc WHERE cc.CrimeCaseID = c.{fk_col})
        """)
        orphans = cur.fetchone()[0]
        print(f"  {child_table:<30} orphans: {orphans}")

    # Sample size calculation
    # We want to keep ~5% of data but maintain diversity
    print("\n=== SAMPLE SIZE CALCULATION ===")
    cur.execute("SELECT COUNT(*) FROM CrimeCase")
    total = cur.fetchone()[0]
    target = max(5000, int(total * 0.05))
    print(f"  Total CrimeCase: {total}")
    print(f"  Target (~5%): {target}")

    # Estimate savings
    print("\n=== ESTIMATED SAVINGS (keeping 5%) ===")
    historical_tables = [
        ('InvestigationNotes', 2026164, 303),
        ('InvestigationTasks', 1205681, 176),
        ('CaseStatusHistory', 998404, 138),
        ('AIRecommendations', 519570, 113),
        ('CaseMaster', 250000, 103),
        ('CaseProgress', 740374, 74),
        ('CaseAssignments', 441095, 50),
        ('Accused', 482941, 48),
        ('CrimeCase', 150000, 37),
        ('PriorityHistory', 218405, 30),
        ('ComplainantDetails', 250000, 29),
        ('CaseFIRLink', 194657, 24),
        ('ChargesheetDetails', 105795, 11),
    ]
    total_current = sum(t[2] for t in historical_tables)
    # Keep 5% of each (ratio may vary by table due to FK relationships)
    total_after = int(total_current * 0.05)
    print(f"  Current historical: ~{total_current} MB")
    print(f"  After 5% trim: ~{total_after} MB")
    print(f"  Estimated DB size after: ~{total_after + 7} MB (historical + operational + master)")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
