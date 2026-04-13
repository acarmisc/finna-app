# finna-app

Multi-cloud FinOps platform — normalize, aggregate, and visualize cost data from GCP, Azure, and LLM gateways.

## Architecture

```mermaid
graph TD
    GCP["GCP Billing<br/>BigQuery"]
    AZURE["Azure Cost<br/>Management"]
    BIFROST["Bifrost LLM<br/>Gateway"]
    ECB["Exchange Rates<br/>ECB"]

    GCP --> E
    AZURE --> E
    BIFROST --> E
    ECB --> E

    subgraph E ["Extractors"]
        E1[gcp_billing]
        E2[azure_cost]
        E3[bifrost_llm]
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
# 1. Start Postgres + Bifrost
docker compose up -d postgres bifrost

# 2. Run an extractor
EXTRACTOR_TYPE=exchange_rates docker compose --profile extractors up extractor

# 3. Provision dashboards on an existing Superset instance
export SUPERSET_BASE_URL=http://your-superset:8088
export SUPERSET_ADMIN_USERNAME=admin
export ADMIN_PASSWORD=your-password
export FINOPS_PG_URI=postgresql://finops:finops_dev@postgres:5432/finops
python3 superset/bootstrap.py
```

## Extractors

| Type | Source | Env vars needed |
|------|--------|-----------------|
| `gcp_billing` | BigQuery billing export | `GCP_PROJECT`, `BQ_DATASET`, `BQ_TABLE`, `PG_DSN` + ADC credentials |
| `azure_cost` | Cost Management API | `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_SUBSCRIPTION_ID`, `PG_DSN` |
| `bifrost_llm` | Bifrost PostgreSQL | `BIFROST_PG_DSN`, `PG_DSN`, `BIFROST_KEY_MAPPING_PATH` |
| `exchange_rates` | ECB daily feed | `PG_DSN` only |

All extractors write normalized rows into `cost_records` via `PG_DSN`. Run via `EXTRACTOR_TYPE` env var or the TUI wizard.

## Superset Dashboards

Dashboards are provisioned via the REST API using `superset/bootstrap.py` — an idempotent script that creates the database connection, datasets, charts, and dashboards. Configuration is in `superset/superset_config.py`.

Three dashboards are created:
- **FinOps Overview** — total cost, cost per provider, daily trends, top projects
- **LLM Costs** — model cost efficiency, daily LLM spend, LLM share of total
- **Project Drill-down** — per-project service categories, MTD vs. previous month

Alert queries for cost spikes and budget thresholds are in `sql/alert_queries.sql`.

## Configuration

### TUI Wizard (interactive)

```bash
python -m config.wizard
```

Walks you through: client ID → PostgreSQL → cloud providers (GCP/Azure/Bifrost) → aggregation. Outputs `clients/{id}/config.yaml` + `.env`.

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

The `bifrost_llm` extractor reads from Bifrost's PostgreSQL `log` table. An **OTel Collector extractor** would be a more general alternative — it could ingest LLM telemetry from any OpenTelemetry-compatible source via the OTLP protocol, leveraging the existing `trace_id`, `model_name`, `latency_ms` fields in `cost_records`. See the data model in `models/__init__.py` for the LLM-specific columns already supported.

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