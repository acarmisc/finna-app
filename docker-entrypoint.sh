#!/bin/bash
set -e

# Create nginx directories with proper permissions (nginx needs these even without root)
mkdir -p /var/lib/nginx/{cache,gaps}
chown -R appuser:appuser /var/lib/nginx

cd /app

# Run database migrations when AUTO_MIGRATE=true (default off — opt-in via deploy env)
if [ "${AUTO_MIGRATE:-false}" = "true" ]; then
    echo "AUTO_MIGRATE=true → running alembic upgrade head"
    alembic upgrade head
fi

# Start FastAPI backend in background
uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/healthz > /dev/null 2>&1; then
        echo "Backend is ready"
        break
    fi
    sleep 1
done

# Start nginx
exec nginx -g "daemon off;"
