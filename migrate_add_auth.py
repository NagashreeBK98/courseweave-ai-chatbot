"""
Run this once to add password_hash to your existing students table.
Usage: python migrate_add_auth.py
"""
import psycopg2
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "34.23.27.68"),
    port=int(os.getenv("DB_PORT", 5432)),
    dbname=os.getenv("DB_NAME", "courseweave"),
    user=os.getenv("DB_USER", "courseweave_user"),
    password=os.getenv("DB_PASSWORD", ""),
)
conn.autocommit = True
cur = conn.cursor()

print("Adding password_hash column...")
cur.execute("""
    ALTER TABLE students
    ADD COLUMN IF NOT EXISTS password_hash TEXT;
""")

DEFAULT_PASSWORD = "demo1234"
hashed = bcrypt.hashpw(DEFAULT_PASSWORD.encode(), bcrypt.gensalt()).decode()

print(f"Setting default password '{DEFAULT_PASSWORD}' for all existing students...")
cur.execute("UPDATE students SET password_hash = %s WHERE password_hash IS NULL", (hashed,))
print(f"Updated {cur.rowcount} students.")

conn.close()
print("Migration complete. All existing students can log in with password: demo1234")
