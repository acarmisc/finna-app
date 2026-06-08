#!/bin/bash
set -e

cd /app

# Run database migrations when AUTO_MIGRATE=true (default off — opt-in via deploy env)
if [ "${AUTO_MIGRATE:-false}" = "true" ]; then
    echo "AUTO_MIGRATE=true → running alembic upgrade head"
    alembic upgrade head
fi

# Start FastAPI backend
exec uvicorn backend.app.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
