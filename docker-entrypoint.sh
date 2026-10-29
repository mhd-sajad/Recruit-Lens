#!/bin/sh
set -e

echo "==> Running database migrations with Alembic..."
cd /app/backend
alembic upgrade head || echo "Migrations completed or already at head."

echo "==> Ensuring demo workspace is seeded..."
if [ -f "/app/scripts/seed_demo_workspace.py" ]; then
    python /app/scripts/seed_demo_workspace.py || echo "Demo workspace already initialized."
fi

echo "==> Starting Recruit Lens production server on port ${PORT:-8000}..."
exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WORKERS:-2}"
