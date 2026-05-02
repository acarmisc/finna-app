# Finna — FinOps Backend

FastAPI backend for the FinOps platform — multi-cloud cost extraction, aggregation, and API.

> The frontend lives in the [`ui/`](./ui) subdirectory of this monorepo.

## Repository layout

```
finna-app/
├── backend/        # FastAPI app (Python 3.12, uv)
├── extractors/     # GCP/Azure/AWS/LLM cost extractors
├── models/         # shared Python data models
├── alembic/        # DB migrations
├── sql/            # init + seed SQL
├── ui/             # React/Vite/Tailwind frontend (was finna-app-ui)
├── k8s/            # kustomize manifests (base + overlays)
├── docs/           # architecture and integration docs
├── Dockerfile.api  # backend image
├── Dockerfile.extractor  # extractor cronjob image
└── ui/Dockerfile   # nginx-served UI image
```

Run the full stack locally with `docker compose up --build`.

## Quick Start

```bash
./startup.sh
```

→ http://localhost:8000 (API) · http://localhost:8000/docs (Swagger)

Or manually:

```bash
docker compose up -d
```

### Load Demo Data (Optional)

To populate the dashboard with realistic sample data for dev/demo without needing cloud credentials:

```bash
psql $PG_DSN -f sql/seed_demo.sql
```

This loads 60+ cost records spanning 30 days (Azure VMs, Storage, AKS; GCP Compute, BigQuery, Cloud Storage; LLM API costs), 5 alerts, and extractor run history.

## Project Structure

```
finna-app/
├── backend/app/api/          # FastAPI app
│   ├── main.py               # Entry point
│   ├── auth.py               # JWT authentication
│   ├── runner.py             # Extractor subprocess management
│   └── routes/               # API route handlers
├── extractors/               # Cloud cost extractors
│   ├── azure_cost.py         # Azure Cost Management
│   └── gcp_billing.py        # GCP BigQuery billing
├── models/                   # Shared Pydantic models
├── sql/                      # DB schema (init_docker.sql)
├── config/                   # Auth helpers
├── utils/                    # Shared utilities
├── Dockerfile.api            # API container
└── docker-compose.yml        # Local dev stack
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/token` | No | Login → JWT |
| GET | `/healthz` | No | Health check |
| GET | `/api/v1/costs` | Yes | Cost records |
| GET | `/api/v1/costs/totals` | Yes | Aggregated totals |
| GET | `/api/v1/costs/daily` | Yes | Daily breakdown |
| GET | `/api/v1/costs/by-sku` | Yes | SKU-level breakdown |
| GET | `/api/v1/config` | Yes | List connections |
| POST | `/api/v1/config` | Yes | Create connection |
| GET | `/api/v1/config/{id}` | Yes | Get connection |
| PUT | `/api/v1/config/{id}` | Yes | Update connection |
| DELETE | `/api/v1/config/{id}` | Yes | Delete connection |
| POST | `/api/v1/config/{id}/test` | Yes | Test credentials |
| GET | `/api/v1/config/projects` | Yes | List projects |
| GET | `/api/v1/alerts` | Yes | All alerts |
| GET | `/api/v1/alerts/active` | Yes | Firing alerts |
| GET | `/api/v1/extractors/status` | Yes | Run history |
| POST | `/api/v1/extractors/run` | Yes | Trigger extractor |
| GET | `/api/v1/extractors/run/{id}` | Yes | Run status + logs |
| POST | `/api/v1/extractors/run/{id}/cancel` | Yes | Cancel run |

## Authentication

Default credentials: `admin` / `admin`

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
```

## Azure Extractor Setup

### Prerequisites

Service principal with **Cost Management Reader** on each target resource group:

```bash
az role assignment create \
  --assignee <CLIENT_ID> \
  --role "Cost Management Reader" \
  --scope "/subscriptions/<SUB_ID>/resourceGroups/<RG_NAME>"

# Verify roles
az role assignment list --assignee <CLIENT_ID> --all --output table
```

### 1. Register credentials

```bash
curl -s -X POST http://localhost:8000/api/v1/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure",
    "name": "My Azure Config",
    "credential_type": "service_principal",
    "config": {
      "tenant_id":       "<TENANT_ID>",
      "client_id":       "<CLIENT_ID>",
      "client_secret":   "<CLIENT_SECRET>",
      "subscription_id": "<SUBSCRIPTION_ID>",
      "scope":           "resourceGroups",
      "resource_groups": ["RG-ONE", "RG-TWO"]
    }
  }'
# → copy the "id" as CONFIG_ID
```

### 2. Test credentials

```bash
curl -s -X POST http://localhost:8000/api/v1/config/<CONFIG_ID>/test \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# → {"ok": true, "checks": {"auth": "ok", "cost_management_api": "ok", ...}}
```

### 3. Trigger extraction

```bash
curl -s -X POST http://localhost:8000/api/v1/extractors/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"azure","extractor_type":"azure","config_id":"<CONFIG_ID>"}' \
  | python3 -m json.tool
# → {"run_id": "...", "status": "started"}
```

### 4. Poll status

```bash
curl -s "http://localhost:8000/api/v1/extractors/run/<RUN_ID>" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOKBACK_DAYS` | `30` | Days of history to fetch |
| `DATE_FROM` / `DATE_TO` | — | Override date range (YYYY-MM-DD) |
| `RG_API_DELAY_SECS` | `max(15, n_rgs)` | Delay between per-RG API calls |
| `RATE_LIMIT_WAIT_1/2/3` | `20/40/60` | 429 retry waits in seconds |
| `BATCH_SIZE` | `500` | DB insert batch size |

### Troubleshooting

| Symptom | Cause |
|---------|-------|
| `401` on token | Token expired — re-auth |
| `RBACAccessDenied` | SP missing Cost Management Reader on RG |
| `429` exhausted | Azure rate limit — run retry waits apply automatically |
| `0` records | No billing data in date range, or wrong scope |
| Run stuck `running` | Check logs via `GET /api/v1/extractors/run/{id}` |

## Data Model

Cost records normalized across providers:

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | text PK | Deterministic SHA-256 hash |
| `provider` | text | `azure` / `gcp` |
| `usage_start/end` | timestamptz | Billing period |
| `account_id` | text | Subscription / project ID |
| `project_id` | text | Cost center / project label |
| `service_category` | text | `compute` / `storage` / `network` / `database` / `ml` |
| `service_name` | text | Meter sub-category or SKU |
| `resource_id` | text | Resource group (Azure) / resource name (GCP) |
| `resource_type` | text | e.g. `microsoft.compute/virtualmachines` |
| `region` | text | e.g. `eu west`, `us-central1` |
| `charge_type` | text | `Usage` / `Tax` / `Credit` |
| `cost_usd` | numeric | Cost in USD |
| `cost_original` | numeric | Cost in billing currency |
| `currency_original` | text | Billing currency |
| `discount_usd` | numeric | Credits / discounts (GCP) |
| `net_cost_usd` | numeric | After discounts |
| `usage_quantity` | numeric | e.g. hours, GB, requests |
| `usage_unit` | text | Unit label |
| `tags` | jsonb | Labels / tags including `location`, `resource_type` |

## Database Migrations

Migrations are managed with [Alembic](https://alembic.sqlalchemy.org/). Auto-migrations run on startup if `AUTO_MIGRATE=true` (default in Docker).

```bash
# Run all pending migrations
alembic upgrade head

# Create a new migration (generates migration file in alembic/versions/)
alembic revision -m "description"

# Rollback one step
alembic downgrade -1

# Check current revision
alembic current

# Show migration history
alembic history
```

Migrations are idempotent (use `IF NOT EXISTS` / `IF EXISTS` guards). The baseline (`001_baseline`) creates core tables and extensions; follow-up migrations add/modify columns and tables.

## Development

```bash
pytest                        # run tests
ruff check .                  # lint
mypy backend/ extractors/     # type check
```

## CI/CD

- **CI**: pytest + ruff + mypy on every push/PR to `main`
- **Docker**: builds and pushes on `v*` tags
