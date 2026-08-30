# coding: utf-8
"""
Setup script: creates the recovr database and user if they don't exist.
Run with: .venv\\Scripts\\python setup_db.py <postgres_password>
"""
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

pg_pass = sys.argv[1] if len(sys.argv) > 1 else ""

try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password=pg_pass,
        host="localhost",
        port=5432,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Create user
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname='recovr'")
    if not cur.fetchone():
        cur.execute("CREATE USER recovr WITH PASSWORD 'recovr_dev'")
        print("[OK] User 'recovr' created")
    else:
        print("[--] User 'recovr' already exists")

    # Create database
    cur.execute("SELECT 1 FROM pg_database WHERE datname='recovr'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE recovr OWNER recovr")
        print("[OK] Database 'recovr' created")
    else:
        print("[--] Database 'recovr' already exists")

    cur.close()
    conn.close()
    print("\n[OK] PostgreSQL setup complete.")
    print("  DATABASE_URL = postgresql://recovr:recovr_dev@localhost:5432/recovr")

except psycopg2.OperationalError as e:
    print(f"\n[FAIL] Connection failed: {e}")
    print("\nUsage: .venv\\Scripts\\python setup_db.py <your_postgres_password>")
    sys.exit(1)
