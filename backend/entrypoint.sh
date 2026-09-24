#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python - <<'PY'
import os, time
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
for i in range(60):
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database is ready.")
        break
    except Exception as e:
        print(f"DB not ready ({i+1}/60): {e}")
        time.sleep(2)
else:
    raise SystemExit("Database not ready after retries")
PY

echo "Creating tables..."
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"

echo "Ensuring new columns exist (idempotent)..."
python - <<'PY'
from sqlalchemy import text
from app.database import engine

# 既有库 create_all 不会补列，这里幂等 ALTER，保证复测/关闭字段就位。
stmts = [
    "ALTER TABLE fastness_checks ADD COLUMN IF NOT EXISTS retest_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE fastness_checks ADD COLUMN IF NOT EXISTS last_retest_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE dye_lots ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP WITH TIME ZONE",
]
with engine.begin() as conn:
    for stmt in stmts:
        conn.execute(text(stmt))
PY

echo "Seeding data..."
python -c "from app.seed import seed; seed()"

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8600
