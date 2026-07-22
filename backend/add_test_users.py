import os
from dotenv import load_dotenv
import psycopg2
import sys
import uuid
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

# Insert missing roles
insp_role_id = str(uuid.uuid4())
for_role_id = str(uuid.uuid4())
cursor.execute("INSERT INTO roles (id, name, description) VALUES (%s, 'inspector', 'Inspector'), (%s, 'forensic', 'Forensic') ON CONFLICT (name) DO NOTHING;", (insp_role_id, for_role_id))
conn.commit()

# Get role IDs
cursor.execute("SELECT id, name FROM roles;")
roles = {name: role_id for role_id, name in cursor.fetchall()}

# Create Inspector
insp_id = str(uuid.uuid4())
cursor.execute(
    "INSERT INTO users (id, username, email, hashed_password, full_name, role_id, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (username) DO NOTHING;",
    (insp_id, "INSP-1111", "insp@example.com", new_hash, "Test Inspector", roles.get('inspector'), True)
)

# Create Forensic
for_id = str(uuid.uuid4())
cursor.execute(
    "INSERT INTO users (id, username, email, hashed_password, full_name, role_id, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (username) DO NOTHING;",
    (for_id, "FOR-2222", "for@example.com", new_hash, "Test Forensic", roles.get('forensic'), True)
)

conn.commit()
print("Added test users")
cursor.close()
conn.close()
