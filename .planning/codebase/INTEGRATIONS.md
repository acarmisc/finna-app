# External Integrations

**Analysis Date:** 2026-04-17

## APIs & External Services

**Google Cloud Platform (GCP):**
- BigQuery - Billing export data extraction
  - SDK/Client: `google-cloud-bigquery` >= 3.11
  - Auth: Application Default Credentials (ADC), service account key, or `gcloud auth login`
  - Entry: `extractors/gcp_billing.py` (BigQuery queries), `extractors/gcp_csv.py` (CSV import)
  - Config env vars: `GCP_PROJECT`, `BQ_DATASET`, `BQ_TABLE`

**Microsoft Azure:**
- Cost Management API - Cost data extraction with daily granularity
  - SDK/Client: `azure-mgmt-costmanagement` >= 4.0
  - Auth: `azure-identity` (ClientSecretCredential, DeviceCodeCredential, AzureCliCredential, DefaultAzureCredential)
  - Entry: `extractors/azure_cost.py`
  - Config env vars: `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_SCOPE`
- Resource Management API - Subscription and resource group discovery
  - SDK/Client: `azure-mgmt-resource` >= 23.0
  - Used in: `config/auth.py` (`_discover_azure_resource_groups()`)
- Azure AD / MSAL - OAuth device code flow and token caching
  - SDK/Client: `msal` >= 1.30, `msal-extensions` >= 1.3
  - Encrypted persistence: `build_encrypted_persistence("finna-app-azure-cache")`
  - Used in: `config/auth.py`, `api/routes/auth.py`

**European Central Bank (ECB):**
- Daily Exchange Rate XML Feed - Currency conversion rates
  - URL: `https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml`
  - Client: `urllib.request` (stdlib, no SDK needed)
  - Entry: `extractors/exchange_rates.py`
  - Converts EUR-based rates to USD-denominated rates

**AWS (Declared but not implemented):**
- `boto3` >= 1.28 is listed as a dependency
- No active AWS extractor exists yet
- `Provider.AWS` enum value exists in `models/__init__.py`

## Data Storage

**Databases:**
- PostgreSQL 16
  - Connection: `PG_DSN` env var (e.g., `postgres://finops:finops_dev@postgres:5432/finops`)
  - Client: `psycopg` >= 3.1 (sync `psycopg.Connection` and async `psycopg.AsyncConnection`)
  - Extensions: `pg_partman` (monthly table partitioning), `pg_cron` (scheduled materialized view refresh)
  - Tables: `cost_records` (partitioned), `infra_metrics_agg` (partitioned), `exchange_rates`, `extractor_health`, `cloud_config`, `extractor_runs`
  - Materialized views: `daily_costs` (aggregated daily cost summary)
  - Schema: `sql/init.sql` (full schema + seed data), `sql/migrations/` (incremental)

**File Storage:**
- Local filesystem only (CSV billing exports mounted via Docker volumes)
- GCP CSV path: `GCP_CSV_PATH` env var, mounted at `/app/csv:ro` in containers

**Caching:**
- None (no Redis or memcached)
- MSAL token cache uses encrypted local persistence via `msal-extensions`

## Authentication & Identity

**Azure Auth (multi-method):**
- Credential resolution chain in `config/auth.py` (`get_azure_credential()`):
  1. `AZURE_AUTH_METHOD=cli` env var -> `AzureCliCredential`
  2. Explicit `AZURE_TENANT_ID` + `AZURE_CLIENT_ID` + `AZURE_CLIENT_SECRET` -> `ClientSecretCredential`
  3. Keyring-stored device code token cache -> `DeviceCodeCredential`
  4. Azure CLI fallback -> `AzureCliCredential`
  5. Final fallback -> `DefaultAzureCredential`
- OS keyring: credential metadata stored under service `finna-app`, keys `azure-token-cache`, `gcp-adc-status`

**GCP Auth:**
- Application Default Credentials (ADC) chain via `google.auth.default()`
- `gcloud auth login --update-adc` for local dev
- `GOOGLE_APPLICATION_CREDENTIALS` env var for service accounts
- Entry: `config/auth.py` (`get_gcp_credentials()`)

**API Auth:**
- No authentication on the FastAPI API itself (open endpoints)
- Device code OAuth flow exposed via `/api/v1/auth/azure/device-code` endpoints

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Datadog, etc.)

**Logs:**
- Python `logging` module throughout
- Structured format: `%(asctime)s [%(levelname)s] %(name)s - %(message)s`
- Logger names match module paths: `extractors.gcp_billing`, `api.main`, `config.auth`, etc.
- Extractor subprocess stdout captured in `extractor_runs.log_output` column

**Health Tracking:**
- Custom `extractor_health` table tracks extractor lifecycle (running/success/failed)
- Health check utilities in `extractors/health_check.py`
- API endpoint: `GET /api/v1/extractors/health`
- API health: `GET /healthz` (checks DB connectivity)

## CI/CD & Deployment

**Hosting:**
- Docker containers, designed for Google Cloud Run Jobs (extractors) and Cloud Run (API)
- Local dev via `docker-compose.yml`

**CI Pipeline:**
- GitHub Actions (`.github/workflows/docker-build.yml`)
- Trigger: Git tags matching `v*`
- Builds and pushes extractor image to GitHub Container Registry (`ghcr.io/{owner}/finops-extractor`)
- Tags: semver (`{{version}}`, `{{major}}.{{minor}}`, `{{major}}`, `latest`)

**Container Registry:**
- GitHub Container Registry (`ghcr.io`)

## Environment Configuration

**Required env vars (extractor):**
- `PG_DSN` - PostgreSQL connection string
- `EXTRACTOR_TYPE` - Which extractor to run (`gcp_billing`, `gcp_csv`, `azure_cost`, `exchange_rates`)
- `DATE_FROM`, `DATE_TO` - Date range for extraction
- Provider-specific: `GCP_PROJECT`, `AZURE_SUBSCRIPTION_ID`, etc.

**Required env vars (API):**
- `PG_DSN` - PostgreSQL connection string
- `HOST` (default: `0.0.0.0`), `PORT` (default: `8000`)

**Secrets location:**
- OS keyring via `keyring` library (local dev)
- Environment variables (production containers)
- `.env` files generated per client by wizard (not committed)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Visualization

**Apache Superset:**
- Bootstrap script: `superset/bootstrap.py` - Creates DB connection, datasets, dashboards via Superset REST API
- Config: `superset/superset_config.py`
- Default port: 8088
- Connects to same PostgreSQL instance for `daily_costs` materialized view

---

*Integration audit: 2026-04-17*
