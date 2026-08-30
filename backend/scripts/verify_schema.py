"""Verify schema was applied correctly."""
from app.core.database import engine
from sqlalchemy import inspect, text

insp = inspect(engine)
tables = sorted(insp.get_table_names(schema="public"))
tables = [t for t in tables if t != "alembic_version"]

print("[OK] Tables in recovr DB:")
for t in tables:
    cols = [c["name"] for c in insp.get_columns(t)]
    idxs = [i["name"] for i in insp.get_indexes(t)]
    print(f"  {t}")
    print(f"    cols  : {cols}")
    print(f"    indexes: {idxs}")

with engine.connect() as conn:
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    rev = result.scalar()
    print(f"\n[OK] Alembic revision: {rev}")

expected = {"transactions", "classifications", "decisions", "actions_log", "recovery_receipts", "baseline_results"}
found = set(tables)
missing = expected - found
if missing:
    print(f"[FAIL] Missing tables: {missing}")
else:
    print(f"[OK] All {len(expected)} expected tables present.")
