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

echo "Applying lightweight migrations..."
python - <<'PY'
from sqlalchemy import text
from app.database import engine

# 存量库补列（create_all 不会修改已存在的表）
statements = [
    "ALTER TABLE fastness_checks ADD COLUMN IF NOT EXISTS retest_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE fastness_checks ADD COLUMN IF NOT EXISTS last_retest_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE dye_lots ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP WITH TIME ZONE",
]
with engine.begin() as conn:
    for sql in statements:
        conn.execute(text(sql))
print("Migrations applied.")
PY

echo "Seeding data..."
python -c "from app.seed import seed; seed()"

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8600
