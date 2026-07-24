"""One-time migration: add new columns to notifications table."""
from sqlalchemy import text
from app.database.postgres import engine

MIGRATIONS = [
    ("sender_id", "UUID REFERENCES users(id)"),
    ("subject", "VARCHAR(500) NOT NULL DEFAULT ''"),
    ("category", "VARCHAR(50) NOT NULL DEFAULT 'system_notification'"),
    ("priority", "VARCHAR(20) NOT NULL DEFAULT 'medium'"),
    ("status", "VARCHAR(20) NOT NULL DEFAULT 'unread'"),
    ("related_case_number", "VARCHAR(50)"),
    ("related_fir_number", "VARCHAR(50)"),
    ("is_broadcast", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("parent_id", "UUID"),
    ("attachment_url", "VARCHAR(500)"),
    ("acknowledged_at", "TIMESTAMPTZ"),
    ("resolved_at", "TIMESTAMPTZ"),
]

with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'notifications'"
    ))
    existing = {row[0] for row in result}
    print(f"Existing columns: {sorted(existing)}")

    for col_name, col_def in MIGRATIONS:
        if col_name not in existing:
            try:
                conn.execute(text(f"ALTER TABLE notifications ADD COLUMN {col_name} {col_def}"))
                print(f"  Added: {col_name}")
            except Exception as e:
                print(f"  Failed {col_name}: {e}")
        else:
            print(f"  Already exists: {col_name}")

    conn.commit()
    print("Migration complete")
