import os
from dotenv import load_dotenv
import psycopg2
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.security import hash_password

load_dotenv()
new_hash = hash_password("123456")

conn = psycopg2.connect(
    host=os.getenv('SUPABASE_DB_HOST'),
    port=os.getenv('SUPABASE_DB_PORT'),
    dbname=os.getenv('SUPABASE_DB_NAME'),
    user=os.getenv('SUPABASE_DB_USER'),
    password=os.getenv('SUPABASE_DB_PASSWORD'),
    sslmode=os.getenv('SUPABASE_DB_SSLMODE', 'require')
)
cursor = conn.cursor()

cursor.execute("""
    SELECT u.username, r.name 
    FROM users u
    JOIN roles r ON u.role_id = r.id;
""")
users = cursor.fetchall()

# Reset passwords for all users to password123 so they can be easily tested
cursor.execute("UPDATE users SET hashed_password = %s;", (new_hash,))
conn.commit()

for u in users:
    print(f"Username: {u[0]} | Role: {u[1]}")

cursor.close()
conn.close()
