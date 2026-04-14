import psycopg2
from dotenv import load_dotenv
import os
import json

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

cur = conn.cursor()
cur.execute("SELECT * FROM interaction_logs ORDER BY timestamp DESC LIMIT 10;")
rows = cur.fetchall()
columns = [desc[0] for desc in cur.description]

if rows:
    print(f"Found {len(rows)} interaction logs:\n")
    for i, row in enumerate(rows, 1):
        print(f"{'='*60}")
        print(f"ROW {i}")
        print(f"{'='*60}")
        for col, val in zip(columns, row):
            if isinstance(val, (dict, list)):
                print(f"  {col}: {json.dumps(val, indent=4)[:500]}")
            elif isinstance(val, str) and len(val) > 200:
                print(f"  {col}: {val[:200]}...")
            else:
                print(f"  {col}: {val}")
        print()
else:
    print("No interaction logs found yet.")

cur.close()
conn.close()