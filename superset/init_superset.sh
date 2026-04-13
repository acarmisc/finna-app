#!/usr/bin/env bash
# =============================================================================
# FinOps Multi-Cloud Monitoring -- Superset Bootstrap Script
# =============================================================================
# Runs inside the superset-init one-shot container (or on first start).
# Idempotent: safe to run multiple times.
# =============================================================================

set -euo pipefail

ADMIN_USERNAME="${SUPERSET_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${SUPERSET_ADMIN_PASSWORD:-admin}"
ADMIN_EMAIL="${SUPERSET_ADMIN_EMAIL:-admin@finops.local}"
ADMIN_FIRST="${SUPERSET_ADMIN_FIRST:-FinOps}"
ADMIN_LAST="${SUPERSET_ADMIN_LAST:-Admin}"

FINOPS_PG_URI="${FINOPS_PG_URI:-postgresql://finops:finops_dev@postgres:5432/finops}"

echo "=== Superset Bootstrap ==="

# ---------------------------------------------------------------------------
# 1. Run database migrations
# ---------------------------------------------------------------------------
echo "[1/5] Running database migrations ..."
superset db upgrade

# ---------------------------------------------------------------------------
# 2. Initialise Superset (creates default roles: Admin, Alpha, Gamma, etc.)
# ---------------------------------------------------------------------------
echo "[2/5] Initialising Superset roles ..."
superset init

# ---------------------------------------------------------------------------
# 3. Create admin user (idempotent -- fab create-admin skips if user exists)
# ---------------------------------------------------------------------------
echo "[3/5] Creating admin user '${ADMIN_USERNAME}' ..."
if superset fab list-users 2>/dev/null | grep -q "^${ADMIN_USERNAME}"; then
    echo "  -> User '${ADMIN_USERNAME}' already exists, skipping."
else
    superset fab create-admin \
        --username "${ADMIN_USERNAME}" \
        --password "${ADMIN_PASSWORD}" \
        --firstname "${ADMIN_FIRST}" \
        --lastname "${ADMIN_LAST}" \
        --email "${ADMIN_EMAIL}"
    echo "  -> Admin user created."
fi

# ---------------------------------------------------------------------------
# 4. Create the FinOps PostgreSQL database connection
# ---------------------------------------------------------------------------
echo "[4/5] Creating FinOps database connection ..."
# Use the REST API via the bootstrap.py script which handles idempotency
# (checks by name before creating).
export SUPERSET_ADMIN_USERNAME ADMIN_PASSWORD FINOPS_PG_URI
python3 /app/bootstrap/bootstrap.py

# ---------------------------------------------------------------------------
# 5. Done
# ---------------------------------------------------------------------------
echo "[5/5] Bootstrap complete."
echo "=== Superset is ready ==="