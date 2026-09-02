"""Shared database configuration for backend scripts.
Reads credentials from environment variables or .env file.
NEVER hardcode credentials in script files.
"""
import os
from dotenv import load_dotenv

# Load .env from backend directory
_backend_dir = os.path.join(os.path.dirname(__file__), '..')
load_dotenv(os.path.join(_backend_dir, '.env'))
load_dotenv(os.path.join(os.path.dirname(_backend_dir), '.env'))

DB_HOST = os.getenv('SUPABASE_DB_HOST', os.getenv('POSTGRES_HOST', ''))
DB_PORT = int(os.getenv('SUPABASE_DB_PORT', os.getenv('POSTGRES_PORT', '5432')))
DB_NAME = os.getenv('SUPABASE_DB_NAME', os.getenv('POSTGRES_DB', 'postgres'))
DB_USER = os.getenv('SUPABASE_DB_USER', os.getenv('POSTGRES_USER', ''))
DB_PASSWORD = os.getenv('SUPABASE_DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', ''))
DB_SSLMODE = os.getenv('SUPABASE_DB_SSLMODE', os.getenv('POSTGRES_SSLMODE', 'require'))

if not all([DB_HOST, DB_USER, DB_PASSWORD]):
    raise RuntimeError(
        "Database credentials not found. Ensure .env file exists in backend/ with "
        "SUPABASE_DB_HOST, SUPABASE_DB_USER, SUPABASE_DB_PASSWORD set."
    )

CONN = dict(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    sslmode=DB_SSLMODE,
    connect_timeout=15,
)
