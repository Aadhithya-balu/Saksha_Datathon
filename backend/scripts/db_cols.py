import psycopg2
conn = psycopg2.connect(host='aws-0-ap-northeast-1.pooler.supabase.com', port=6543, dbname='postgres', user='postgres.tqaegfrnnddfqshwdkvh', password='datathon2026', sslmode='require')
cur = conn.cursor()
for t in ['CrimeCase', 'CaseMaster', 'CaseFIRLink', 'CaseStatusHistory']:
    cur.execute(f"""SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = '{t}' AND table_schema = 'public' ORDER BY ordinal_position""")
    print(f"\n=== {t} ===")
    for r in cur.fetchall():
        print(f"  {r[0]:<35} {r[1]}")
conn.close()
