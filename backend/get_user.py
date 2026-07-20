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
cursor.execute("SELECT id, username, hashed_password FROM users LIMIT 5;")
rows = cursor.fetchall()
for r in rows:
    print(r)

# Overwrite first user's password to password123
if rows:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_context.hash("password123")
    user_id = rows[0][0]
    cursor.execute("UPDATE users SET hashed_password = %s WHERE id = %s", (hashed, user_id))
    conn.commit()
    print("Updated password for", rows[0][1], "to password123")

cursor.close()
conn.close()
