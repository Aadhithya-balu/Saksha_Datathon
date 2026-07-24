"""
Full database export: schema + data for every table in the Saksha database.
Produces a single SQL file that can be imported into a new Supabase project.

Usage:  py -3.12 scripts/db_export_full.py
Output: backups/saksha_full_dump.sql
"""
import psycopg2
import os
import sys
import time

CONN = dict(
    host='aws-0-ap-northeast-1.pooler.supabase.com',
    port=6543, dbname='postgres',
    user='postgres.tqaegfrnnddfqshwdkvh',
    password='datathon2026', sslmode='require',
    connect_timeout=15,
)
BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)
OUTPUT = os.path.join(BACKUP_DIR, 'saksha_full_dump.sql')

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def connect_with_retry(max_attempts=30, delay=20):
    for i in range(max_attempts):
        try:
            c = psycopg2.connect(**CONN)
            cur = c.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            return c
        except Exception as e:
            log(f"Connect attempt {i+1}: {str(e)[:70]}")
            time.sleep(delay)
    return None

def get_table_list(cur):
    cur.execute("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    return [r[0] for r in cur.fetchall()]

def get_columns(cur, table):
    cur.execute(f"""
        SELECT column_name, data_type, is_nullable, column_default,
               character_maximum_length, numeric_precision
        FROM information_schema.columns
        WHERE table_name = %s AND table_schema = 'public'
        ORDER BY ordinal_position
    """, (table,))
    return cur.fetchall()

def get_pk_columns(cur, table):
    cur.execute(f"""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = %s AND tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'public'
        ORDER BY kcu.ordinal_position
    """, (table,))
    return [r[0] for r in cur.fetchall()]

def get_fk_constraints(cur, table):
    cur.execute(f"""
        SELECT tc.constraint_name, kcu.column_name,
               ccu.table_name AS foreign_table, ccu.column_name AS foreign_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.table_name = %s AND tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
    """, (table,))
    return cur.fetchall()

def get_indexes(cur, table):
    cur.execute(f"""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = %s AND schemaname = 'public'
        AND indexname NOT LIKE '%_pkey'
    """, (table,))
    return cur.fetchall()

def pg_type_to_sql(col_name, data_type, nullable, default, max_len, num_prec):
    dt = data_type.lower()
    if dt in ('integer',):
        t = 'INTEGER'
    elif dt in ('bigint',):
        t = 'BIGINT'
    elif dt in ('smallint',):
        t = 'SMALLINT'
    elif dt in ('double precision',):
        t = 'DOUBLE PRECISION'
    elif dt in ('real',):
        t = 'REAL'
    elif dt in ('numeric', 'decimal'):
        t = f'NUMERIC({num_prec}, 6)' if num_prec else 'NUMERIC'
    elif dt in ('boolean',):
        t = 'BOOLEAN'
    elif dt in ('timestamp without time zone',):
        t = 'TIMESTAMP'
    elif dt in ('timestamp with time zone',):
        t = 'TIMESTAMPTZ'
    elif dt in ('date',):
        t = 'DATE'
    elif dt in ('time without time zone',):
        t = 'TIME'
    elif dt in ('uuid',):
        t = 'UUID'
    elif dt in ('json',):
        t = 'JSON'
    elif dt in ('jsonb',):
        t = 'JSONB'
    elif dt in ('text',):
        t = 'TEXT'
    elif dt in ('character varying', 'varchar'):
        t = f'VARCHAR({max_len})' if max_len else 'TEXT'
    elif dt in ('character', 'char'):
        t = f'CHAR({max_len})' if max_len else 'CHAR(1)'
    elif dt in ('bytea',):
        t = 'BYTEA'
    elif dt in ('array',):
        t = 'TEXT[]'
    else:
        t = dt.upper()
    if nullable == 'NO':
        t += ' NOT NULL'
    if default and default != 'NULL':
        if 'nextval' in str(default):
            pass
        elif 'uuid' in str(default).lower():
            pass
        elif 'now()' in str(default).lower():
            t += ' DEFAULT NOW()'
        elif 'true' in str(default).lower():
            t += ' DEFAULT TRUE'
        elif 'false' in str(default).lower():
            t += ' DEFAULT FALSE'
    return t

def escape_val(val):
    if val is None:
        return 'NULL'
    if isinstance(val, bool):
        return 'TRUE' if val else 'FALSE'
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val)
    s = s.replace('\\', '\\\\').replace("'", "''")
    return f"'{s}'"

def main():
    log("Connecting to database...")
    conn = connect_with_retry()
    if not conn:
        log("FAILED to connect after all retries.")
        sys.exit(1)

    log("Connected!")
    cur = conn.cursor()

    tables = get_table_list(cur)
    log(f"Found {len(tables)} tables")

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write("-- Saksha Database Full Dump\n")
        f.write(f"-- Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-- For import into a new Supabase project\n\n")
        f.write("SET client_encoding = 'UTF8';\n")
        f.write("SET standard_conforming_strings = on;\n")
        f.write("SET check_function_bodies = false;\n")
        f.write("SET xmloption = content;\n")
        f.write("SET client_min_messages = warning;\n")
        f.write("SET row_security = off;\n\n")
        f.write("DROP SCHEMA public CASCADE;\n")
        f.write("CREATE SCHEMA public;\n\n")

        for idx, table in enumerate(tables):
            log(f"[{idx+1}/{len(tables)}] Exporting {table}...")

            # Get column info
            columns = get_columns(cur, table)
            pk_cols = get_pk_columns(cur, table)
            fks = get_fk_constraints(cur, table)
            indexes = get_indexes(cur, table)

            # CREATE TABLE
            f.write(f'DROP TABLE IF EXISTS public."{table}" CASCADE;\n')
            col_defs = []
            for col in columns:
                col_name, data_type, nullable, default, max_len, num_prec = col
                sql_type = pg_type_to_sql(col_name, data_type, nullable, default, max_len, num_prec)
                col_defs.append(f'    "{col_name}" {sql_type}')
            f.write(f'CREATE TABLE public."{table}" (\n')
            f.write(',\n'.join(col_defs))
            f.write('\n);\n\n')

            # Primary key
            if pk_cols:
                pk_str = ', '.join(f'"{c}"' for c in pk_cols)
                f.write(f'ALTER TABLE ONLY public."{table}" ADD CONSTRAINT "{table}_pkey" PRIMARY KEY ({pk_str});\n\n')

            # Foreign keys
            for fk in fks:
                fk_name, fk_col, ref_table, ref_col = fk
                f.write(f'ALTER TABLE ONLY public."{table}" ADD CONSTRAINT "{fk_name}" ')
                f.write(f'FOREIGN KEY ("{fk_col}") REFERENCES public."{ref_table}"("{ref_col}");\n')
            if fks:
                f.write('\n')

            # Indexes
            for idx_name, idx_def in indexes:
                f.write(f'{idx_def};\n')
            if indexes:
                f.write('\n')

            # Data
            try:
                cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                total = cur.fetchone()[0]
            except:
                total = 0

            if total > 0:
                col_names = [c[0] for c in columns]
                cols_str = ', '.join(f'"{c}"' for c in col_names)
                f.write(f"COPY public.\"{table}\" ({cols_str}) FROM stdin;\n")

                BATCH = 5000
                offset = 0
                exported = 0
                while offset < total:
                    cur.execute(f'SELECT * FROM "{table}" ORDER BY 1 LIMIT {BATCH} OFFSET {offset}')
                    rows = cur.fetchall()
                    if not rows:
                        break
                    for row in rows:
                        vals = '\t'.join(escape_val(v) for v in row)
                        f.write(vals + '\n')
                    exported += len(rows)
                    offset += BATCH
                    if exported % 50000 == 0:
                        log(f"    {table}: exported {exported}/{total}")

                f.write("\\.\n\n")
                log(f"  {table}: {total} rows exported")
            else:
                log(f"  {table}: 0 rows (empty)")

        f.write("-- End of dump\n")

    cur.close()
    conn.close()

    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    log(f"\nDump saved: {OUTPUT}")
    log(f"File size: {size_mb:.1f} MB")

if __name__ == "__main__":
    main()
