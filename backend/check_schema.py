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
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'evidence';")
print("Evidence columns:", [r[0] for r in cursor.fetchall()])

cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'officers';")
print("Officers columns:", [r[0] for r in cursor.fetchall()])

cursor.close()
conn.close()
