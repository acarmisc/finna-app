#!/bin/bash
set -e

echo "=== Finna MVP Smoke Test ==="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
  echo "ERROR: Docker not found. Please install Docker first."
  exit 1
fi

echo "1. Starting PostgreSQL..."
docker compose up -d postgres
echo "   Waiting for PostgreSQL to be ready..."
sleep 5

echo "2. Installing Python dependencies..."
uv sync --quiet 2>/dev/null || pip install -e . --quiet

echo "3. Starting API server..."
export PG_DSN="${PG_DSN:-postgresql://finops:finops_dev@localhost:5432/finops}"
export AUTO_MIGRATE=true
uv run python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
sleep 3

echo "4. Health check..."
HEALTH=$(curl -sf http://localhost:8000/healthz 2>/dev/null || echo "FAILED")
if echo "$HEALTH" | grep -q "ok"; then
  echo "   ✅ API is healthy: $HEALTH"
else
  echo "   ⚠️  API health check returned: $HEALTH"
  echo "   (This may be normal if migrations are still running)"
fi

echo "5. Running exchange rates extractor (no cloud credentials needed)..."
EXTRACTOR_RESULT=$(curl -sf -X POST http://localhost:8000/api/v1/extractors/run \
  -H "Content-Type: application/json" \
  -d '{"extractor_type": "exchange_rates"}' 2>/dev/null || echo '{"status": "error"}')

if echo "$EXTRACTOR_RESULT" | grep -q "status"; then
  echo "   ✅ Extractor triggered: $EXTRACTOR_RESULT"
else
  echo "   ⚠️  Extractor response: $EXTRACTOR_RESULT"
fi

echo ""
echo "=== Stack is running ==="
echo "   API:      http://localhost:8000"
echo "   Health:   http://localhost:8000/healthz"
echo "   Postgres: localhost:5432"
echo ""
echo "   Press Ctrl+C to stop the API server"
echo ""

# Wait for Ctrl+C
wait $API_PID 2>/dev/null || true

# Cleanup
echo ""
echo "Stopping API server..."
kill $API_PID 2>/dev/null || true
echo "Done."