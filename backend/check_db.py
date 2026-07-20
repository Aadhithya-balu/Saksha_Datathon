import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('SUPABASE_DB_HOST'),
    port=os.getenv('SUPABASE_DB_PORT'),
    dbname=os.getenv('SUPABASE_DB_NAME'),
    user=os.getenv('SUPABASE_DB_USER'),
    password=os.getenv('SUPABASE_DB_PASSWORD'),
    sslmode=os.getenv('SUPABASE_DB_SSLMODE', 'require')
)
cursor = conn.cursor()

print("--- EVIDENCE METADATA ---")
cursor.execute("SELECT filename, mime_type, extracted_data FROM evidence_metadata LIMIT 1;")
print(cursor.fetchall())

print("\n--- TIMELINE ---")
cursor.execute("SELECT action FROM evidence_timeline;")
print([r[0] for r in cursor.fetchall()])

print("\n--- CHAIN OF CUSTODY ---")
cursor.execute("SELECT action FROM chain_of_custody;")
print([r[0] for r in cursor.fetchall()])

print("\n--- AI SUMMARY ---")
cursor.execute("SELECT summary, model FROM evidence_ai_summary;")
print(cursor.fetchall())

cursor.close()
conn.close()
