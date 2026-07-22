import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def run_migration():
    conn = psycopg2.connect(
        host=os.getenv('SUPABASE_DB_HOST'),
        port=os.getenv('SUPABASE_DB_PORT'),
        dbname=os.getenv('SUPABASE_DB_NAME'),
        user=os.getenv('SUPABASE_DB_USER'),
        password=os.getenv('SUPABASE_DB_PASSWORD'),
        sslmode=os.getenv('SUPABASE_DB_SSLMODE', 'require')
    )
    cursor = conn.cursor()
    
    # Drop existing tables to recreate them with the correct schema
    print("Dropping existing tables...")
    cursor.execute("DROP TABLE IF EXISTS officers CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS evidence_ai_summary CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS chain_of_custody CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS evidence_assignments CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS evidence_timeline CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS evidence_metadata CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS evidence CASCADE;")
    
    print("Applying setup_officers_evidence.sql...")
    with open("scripts/setup_officers_evidence.sql", "r") as f:
        sql = f.read()
    
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    run_migration()
