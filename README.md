# Finna — Multi-Cloud FinOps Platform

Finna is a FinOps platform that extracts, normalizes, and visualizes cloud costs across **Azure, GCP, AWS, and LLM providers**.

## Quick Start

```bash
./startup.sh
```

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173

Default credentials: `admin` / `admin`

## Architecture

```
finna-app/
├── backend/         # FastAPI API (Python 3.12)
├── extractors/      # Cloud cost extractors
├── models/          # Shared data models
├── ui/              # React/Vite frontend
├── sql/             # Database schema + seed data
└── docker-compose.yml
```

## Core Features

### Cost Extraction
- **Azure**: Cost Management API via service principal or OAuth device flow
- **GCP**: BigQuery billing export
- **AWS**: Cost Explorer API (coming soon)
- **LLM**: OpenTelemetry collector integration

### Resource Wastage Detection
Rule-based, deterministic detection of unused and orphaned cloud resources — no AI required.
- 10 built-in Azure rules (orphaned disks, unattached IPs, idle NICs, old snapshots, stopped VMs with disks, idle AKS node pools, oversized App Service Plans, legacy storage kinds, and more)
- Extensible rule registry via `@rule` decorator — see [`docs/wastage.md`](docs/wastage.md) for the rule catalog and how to add rules
- Estimated monthly savings based on public list prices (EUR/USD); disclaimer shown in UI
- Full lifecycle per finding: open → ack → resolved / ignored
- REST API: `GET /api/v1/wastage`, `POST /api/v1/wastage/{id}/ack|resolve|ignore`, `POST /api/v1/wastage/scan`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/token` | Get JWT token |
| GET | `/api/v1/costs` | Cost records |
| GET | `/api/v1/costs/totals` | Aggregated totals |
| GET | `/api/v1/costs/daily` | Daily breakdown |
| GET | `/api/v1/costs/by-sku` | SKU-level costs |
| GET | `/api/v1/alerts` | Alert rules |
| GET | `/api/v1/alerts/active` | Firing alerts |
| GET | `/api/v1/config` | Cloud connections |
| POST | `/api/v1/extractors/run` | Trigger extraction |
| GET | `/api/v1/extractors/status` | Run history |

### Data Model

All costs are normalized to a common schema:

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | text | Unique hash |
| `provider` | text | `azure`, `gcp`, `aws`, `llm` |
| `usage_start` / `usage_end` | timestamp | Billing period |
| `account_id` | text | Subscription/project ID |
| `project_id` | text | Logical project |
| `service_category` | text | `compute`, `storage`, `network`, `database`, `ml` |
| `service_name` | text | Meter/SKU name |
| `region` | text | Cloud region |
| `cost_usd` | numeric | Cost in USD |
| `cost_original` | numeric | Cost in billing currency |
| `currency_original` | text | Billing currency |
| `net_cost_usd` | numeric | After discounts |
| `usage_quantity` | numeric | Hours, GB, requests |
| `usage_unit` | text | Unit label |
| `tags` | jsonb | Resource labels |

## Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local development)
- uv (Python package manager)

### Local Development

```bash
# Install Python dependencies
uv sync

# Start the stack (PostgreSQL, API, Frontend)
docker compose up -d

# Load demo data (optional)
psql $PG_DSN -f sql/seed_demo.sql
```

### Azure Setup

1. Create a service principal with **Cost Management Reader** role:

```bash
az role assignment create \
  --assignee <CLIENT_ID> \
  --role "Cost Management Reader" \
  --scope "/subscriptions/<SUB_ID>/resourceGroups/<RG_NAME>"
```

2. Register the connection via API:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | jq -r '.token')

curl -X POST http://localhost:8000/api/v1/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "azure",
    "name": "My Azure",
    "credential_type": "service_principal",
    "config": {
      "tenant_id": "<TENANT_ID>",
      "client_id": "<CLIENT_ID>",
      "client_secret": "<CLIENT_SECRET>",
      "subscription_id": "<SUBSCRIPTION_ID>",
      "resource_groups": ["RG-ONE", "RG-TWO"]
    }
  }'
```

3. Test and trigger extraction:

```bash
# Test credentials
curl -X POST http://localhost:8000/api/v1/config/<CONFIG_ID>/test \
  -H "Authorization: Bearer $TOKEN"

# Trigger extraction
curl -X POST http://localhost:8000/api/v1/extractors/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"azure","config_id":"<CONFIG_ID>"}'
```

### GCP Setup

Use a service account with `roles/bigquery.dataViewer` on the billing dataset:

```bash
curl -X POST http://localhost:8000/api/v1/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gcp",
    "name": "My GCP",
    "credential_type": "service_account",
    "config": {
      "project_id": "<PROJECT_ID>",
      "dataset_id": "<BILLING_DATASET>"
    }
  }'
```

## Authentication

### Local Development

Default credentials (set via `docker-compose.yml`):
- Username: `admin`
- Password: `admin`

### OIDC / Single Sign-On

Finna supports OpenID Connect (OIDC) for enterprise single sign-on with:
- Keycloak, Okta, Auth0, Azure AD, Google, or any spec-compliant identity provider
- Claim-based role mapping for automatic admin access from IdP groups
- Email domain filtering to restrict access to organization domains
- Auto-provisioning of users on first login

**Setup:** See [docs/oidc-setup.md](docs/oidc-setup.md) for step-by-step provider configuration.

**Managing Providers:** Settings → Authentication → Add Provider (requires admin role)

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PG_DSN` | - | PostgreSQL connection string |
| `JWT_SECRET` | - | JWT signing secret |
| `JWT_EXPIRATION_MINUTES` | 60 | Token expiry |
| `LOOKBACK_DAYS` | 30 | History to fetch |
| `BATCH_SIZE` | 500 | DB insert batch size |

## Development

```bash
# Run tests
pytest

# Lint
ruff check .

# Type check
mypy backend/ extractors/
```

## Deployment

### Docker

```bash
# Build API image
docker build -f Dockerfile.api -t finna-api .

# Build extractor image
docker build -f Dockerfile.extractor -t finna-extractor .
```

## Documentation

- [Operational Guide](docs/operational-guide.md) — Deployment and maintenance
- [Troubleshooting](docs/troubleshooting-runbook.md) — Common issues and fixes
- [Tagging Strategy](docs/tagging-strategy.md) — Resource labeling conventions
- [API Reference](docs/openapi.yaml) — OpenAPI specification
