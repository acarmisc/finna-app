# finna-app

Multi-cloud FinOps platform — normalize, aggregate, and visualize cost data from GCP, Azure, and LLM gateways (via OTel Collector).

## Architecture

```mermaid
graph TD
    GCP["GCP Billing<br/>BigQuery"]
    AZURE["Azure Cost<br/>Management"]
    OTEL["OTel Collector<br/>LLM Gateway"]
    ECB["Exchange Rates<br/>ECB"]

    GCP --> E
    AZURE --> E
    OTEL --> E
    ECB --> E

    subgraph E ["Extractors"]
        E1[gcp_billing]
        E2[azure_cost]
        E3[otel_llm]
        E4[exchange_rates]
    end

    E -->|"normalize + write"| PG

    subgraph PG ["PostgreSQL"]
        T1[cost_records]
        T2[daily_costs]
        T3[exchange_rates]
        T4[extractor_health]
    end

    PG --> SUP

    SUP["Superset<br/>Dashboards"]
```

## Quick Start

```bash
# 0. Install dependencies (requires uv — https://docs.astral.sh/uv/)
uv sync

# 1. Start Postgres
docker compose up -d postgres

# 2. Authenticate with your cloud provider (no service account needed!)
uv run python -m config.auth azure   # Azure: browser-based device code login
uv run python -m config.auth gcp     # GCP: delegates to gcloud auth login

# 3. Run an extractor (credentials are auto-discovered)
EXTRACTOR_TYPE=exchange_rates docker compose --profile extractors up extractor

# 4. Provision dashboards on an existing Superset instance
export SUPERSET_BASE_URL=http://your-superset:8088
export SUPERSET_ADMIN_USERNAME=admin
export ADMIN_PASSWORD=your-password
export FINOPS_PG_URI=postgresql://finops:finops_dev@postgres:5432/finops
uv run python superset/bootstrap.py
```

## Extractors

| Type | Source | Auth methods | Env vars needed |
|------|--------|-------------|-----------------|
| `gcp_billing` | BigQuery billing export | ADC (`gcloud auth login`), service account key | `GCP_PROJECT`, `BQ_DATASET`, `BQ_TABLE`, `PG_DSN` |
| `azure_cost` | Cost Management API | OAuth device code (browser), service principal, Azure CLI | `AZURE_SUBSCRIPTION_ID`, `PG_DSN` |
| `otel_llm` | OTel Collector (planned) | — | `PG_DSN` + OTel pipeline config |
| `exchange_rates` | ECB daily feed | — | `PG_DSN` only |

All extractors write normalized rows into `cost_records` via `PG_DSN`. Run via `EXTRACTOR_TYPE` env var or the TUI wizard.

### Authentication

**No service account required for local development!** Use OAuth device-code flow:

```bash
# Azure: authenticates via browser, caches token in OS keyring
python -m config.auth azure --tenant-id <your-tenant>

# GCP: delegates to gcloud CLI, sets up ADC
python -m config.auth gcp
```

Credential resolution order for extractors:
- **Azure**: explicit env vars → keyring cached token → Azure CLI (`az login`) → `DefaultAzureCredential`
- **GCP**: `GOOGLE_APPLICATION_CREDENTIALS` → `gcloud auth login` ADC → compute metadata

## Superset Dashboards

Dashboards are provisioned via the REST API using `superset/bootstrap.py` — an idempotent script that creates the database connection, datasets, charts, and dashboards. Configuration is in `superset/superset_config.py`.

### Required Environment Variables

| Variable | Description | Required |
|----------|------------|----------|
| `SUPERSET_SECRET_KEY` | Secret key for session encryption (min 32 chars) | Yes |
| `SUPERSET_BASE_URL` | Superset instance URL | For bootstrap |
| `SUPERSET_ADMIN_USERNAME` | Admin username | For bootstrap |
| `ADMIN_PASSWORD` | Admin password (min 12 chars, not common) | For bootstrap |
| `FINOPS_PG_URI` | PostgreSQL connection string | For bootstrap |
| `SUPERSET_DATABASE_URI` | Superset metadata DB | No (default provided) |
| `REDIS_URL` | Redis cache URL | No (default provided) |

Generate a secure secret key:
```bash
python -c 'import secrets; print(secrets.token_hex(32))'
```

Three dashboards are created:
- **FinOps Overview** — total cost, cost per provider, daily trends, top projects
- **LLM Costs** — model cost efficiency, daily LLM spend, LLM share of total
- **Project Drill-down** — per-project service categories, MTD vs. previous month

Alert queries for cost spikes and budget thresholds are in `sql/alert_queries.sql`.

## Configuration

### Authentication (TUI or CLI)

```bash
# Interactive TUI with OAuth device code
python -m config.auth azure
python -m config.auth gcp

# Or use the full TUI wizard
python -m config.wizard
```

Walks you through: authentication → client ID → PostgreSQL → cloud providers (GCP/Azure) → aggregation. OAuth tokens are cached in OS keyring; extractors auto-discover them. Outputs `clients/{id}/config.yaml` + `.env`.

### Multi-subscription YAML

The wizard and schema support multiple GCP projects and Azure subscriptions per client. See `config/schema.py` for the full Pydantic model.

## Database Schema

`sql/init.sql` creates:

- **`cost_records`** — partitioned by month, holds all normalized cost rows (cloud + LLM)
- **`daily_costs`** — materialized view for dashboard queries, auto-refreshed every 15 min
- **`exchange_rates`** — ECB daily rates for multi-currency normalization
- **`extractor_health`** — tracks last run status per extractor
- **`infra_metrics_agg`** — pre-aggregated infra metrics (partitioned by month)

90 days of seed data (GCP + Azure + LLM) is inserted on first init.

## Service Accounts

This platform uses **dedicated service accounts** with least-privilege IAM — never use personal credentials.

| Provider | Account Type | Minimum Roles | Configured via |
|----------|-------------|---------------|----------------|
| **GCP** | Service Account (JSON key) | `roles/bigquery.dataViewer`, `roles/cloudsql.client`, `roles/secretmanager.secretAccessor` | TUI wizard → `service_account_key_path`, or `GOOGLE_APPLICATION_CREDENTIALS` |
| **Azure** | Service Principal (App Registration) | `Cost Management Reader` on target subscription | TUI wizard → `tenant_id`, `client_id`, `client_secret` per subscription |
| **AWS** | IAM User / Role | `ce:GetCostAndUsage` | TUI wizard (planned — see #2) |

> The TUI wizard (`python -m config.wizard`) walks you through credential setup for each provider with masked input for secrets.

## Docker Images (CI/CD)

GitHub Actions builds and pushes to **ghcr.io** on every `v*` tag:

```bash
git tag v1.0.0 && git push origin v1.0.0
```

Image: `ghcr.io/acarmisc/finops-extractor`

## LLM Data Sources

LLM cost data is ingested via an **OTel Collector extractor** (planned). This provides a vendor-neutral approach that can ingest LLM telemetry from any OpenTelemetry-compatible source via the OTLP protocol, leveraging the existing `trace_id`, `model_name`, `latency_ms` fields in `cost_records`. See the data model in `models/__init__.py` for the LLM-specific columns already supported.

## Project Structure

```
├── aggregation/          # Aggregation pipeline config + models
├── config/               # Schema, wizard (TUI), key mappings
├── docs/                 # Operational guide, runbook, alert queries
├── extractors/           # One Python module per cloud source
├── models/               # Shared Pydantic models
├── onboarding/           # Client setup script
├── sql/                  # DDL + seed data + alert queries
├── superset/             # Dashboard bootstrap scripts (assumes existing Superset)
├── tests/                # Test suite
├── Dockerfile.extractor  # Multi-stage Python image
└── docker-compose.yml   # Local dev stack
```

## Contributing

This README doubles as LLM context. When contributing:

- **Extractors** follow the pattern in `extractors/gcp_billing.py` — read env vars, normalize to `cost_records` columns, batch-insert via psycopg.
- **Schema changes** go in `config/schema.py` (Pydantic) and `sql/init.sql` (DDL). New fields must be nullable or have defaults.
- **TUI** lives in `config/wizard.py` — use `questionary` for prompts, `rich` for output.
- **No secrets in code** — all credentials via env vars or `${VAR}` placeholders in YAML. The `.gitignore` blocks `*credentials*`, `*service-account*`, `*.pem`, `*.key`, `.env*`.
- **Terraform** was removed from the repo — see [issue #1](https://github.com/acarmisc/finna-app/issues/1) for restoration guidance.

## Security Notes

- Docker images run as non-root (`appuser`)
- Dev defaults (`finops_dev`, `admin`) in `docker-compose.yml` are for local dev only — override via env vars in production
- GCP uses Application Default Credentials; Azure uses `ClientSecretCredential`
- Superset secret key must be overridden via `SUPERSET_SECRET_KEY` env var

## License

[Apache License 2.0](LICENSE) — see [NOTICE](NOTICE) for third-party attributions.