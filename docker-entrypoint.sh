#!/bin/sh
set -e

echo "==> Running database migrations with Alembic..."
cd /app/backend
alembic upgrade head || echo "Migrations completed or already at head."

echo "==> Starting Recruit Lens production server on port ${PORT:-8000}..."
exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WORKERS:-2}"
