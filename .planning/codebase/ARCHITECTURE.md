# Architecture

**Analysis Date:** 2026-04-17

## Pattern Overview

**Overall:** ETL Pipeline with REST API Orchestrator

The system follows an Extract-Transform-Load pattern where independent extractors pull cost data from cloud providers, normalize it into a unified schema, and batch-insert it into PostgreSQL. A FastAPI orchestrator manages cloud configurations and triggers extractor runs as subprocesses.

**Key Characteristics:**
- Multi-cloud cost normalization through a shared `NormalizedCostRecord` Pydantic model
- Extractors run as standalone processes (Cloud Run Jobs in production, subprocesses when triggered via API)
- Configuration-driven: clients configure providers through a TUI wizard or API endpoints
- Environment-variable-based multi-project/multi-subscription support via naming conventions (`GCP_{PREFIX}_PROJECT`, `AZURE_{PREFIX}_SUBSCRIPTION_ID`)

## Layers

**Models Layer:**
- Purpose: Define the shared data contract across all extractors and the API
- Location: `models/__init__.py`
- Contains: `NormalizedCostRecord` (Pydantic), `Provider` enum, `ServiceCategory` enum
- Depends on: Pydantic
- Used by: All extractors, API models

**Extractors Layer:**
- Purpose: Pull raw cost data from cloud APIs, normalize to `NormalizedCostRecord`, batch-insert into PostgreSQL
- Location: `extractors/`
- Contains: Provider-specific extractors (`gcp_billing.py`, `gcp_csv.py`, `azure_cost.py`, `exchange_rates.py`), shared utilities (`gcp_shared.py`, `health_check.py`), dispatcher (`entrypoint.py`)
- Depends on: `models/`, `config/auth.py`, cloud SDKs, `psycopg`, `tenacity`
- Used by: API runner (subprocess), Docker container entrypoint

**API Layer:**
- Purpose: REST API for managing cloud configurations, triggering extractor runs, and monitoring health
- Location: `api/`
- Contains: FastAPI app (`main.py`), database helpers (`db.py`), route modules (`routes/`), Pydantic schemas (`models.py`), subprocess runner (`runner.py`)
- Depends on: `models/`, `config/`, `extractors/` (subprocess invocation), `psycopg`, FastAPI
- Used by: CLI tools, web frontends

**Config Layer:**
- Purpose: Authentication flows, configuration schemas, and interactive TUI wizard
- Location: `config/`
- Contains: OAuth/auth flows (`auth.py`), Pydantic config models (`schema.py`), interactive wizard (`wizard.py`)
- Depends on: `keyring`, `questionary`, `rich`, Azure/GCP SDKs, `msal-extensions`
- Used by: Extractors (credential retrieval), API (auth endpoints), CLI users

**Aggregation Layer:**
- Purpose: Statistical aggregation of infrastructure metrics by time window
- Location: `aggregation/`
- Contains: Aggregation engine (`engine.py`), config defaults (`config.py`)
- Depends on: `psycopg`
- Used by: Standalone job execution (future: Cloud Run Job or pg_cron)

**Database Layer:**
- Purpose: Schema definitions, migrations, seed data
- Location: `sql/`
- Contains: Full schema with partitioning (`init.sql`), alert queries (`alert_queries.sql`), local init (`init_local.sql`), migrations (`migrations/`)
- Used by: PostgreSQL init (Docker), API startup migration runner

**Onboarding Layer:**
- Purpose: Automated client setup with config generation
- Location: `onboarding/`
- Contains: Client setup script (`setup_client.py`) - generates extractor configs, aggregation configs, connectivity tests, and registry entries
- Depends on: `pyyaml`

**Visualization Layer:**
- Purpose: Apache Superset dashboard provisioning
- Location: `superset/`
- Contains: Bootstrap script (`bootstrap.py`), Superset config (`superset_config.py`)
- Depends on: Superset REST API

## Data Flow

**Cost Extraction Pipeline:**

1. Extractor process starts (via Docker, API subprocess, or CLI)
2. `extractors/entrypoint.py` reads `EXTRACTOR_TYPE` and dispatches to correct module
3. Extractor authenticates with cloud provider (using `config/auth.py` credential chain)
4. Raw cost data fetched from cloud API (BigQuery, Azure Cost Management, ECB XML)
5. Rows normalized into `NormalizedCostRecord` instances (provider-specific `normalise_row()` / `transform_row()`)
6. Records batch-inserted into `cost_records` table (`ON CONFLICT DO NOTHING` for idempotency)
7. Extractor health status updated in `extractor_health` table

**API-Triggered Extraction:**

1. Client calls `POST /api/v1/extractors/run` with provider and optional config_id
2. API loads `cloud_config` from database, builds environment variables
3. Extractor launched as subprocess (`python -m extractors.{type}`)
4. Background thread monitors subprocess stdout and exit code
5. Run status updated in `extractor_runs` table on completion

**Configuration Flow:**

1. User runs `python -m config` (wizard) or calls API auth endpoints
2. Authentication flow completes (device code, CLI, service principal)
3. Azure: subscriptions discovered, resource groups listed, user selects targets
4. Config saved to OS keyring (local) or `cloud_config` table (API)
5. Extractors read config at runtime from keyring or env vars

**State Management:**
- PostgreSQL is the sole persistent state store
- `extractor_health` table tracks last run status per extractor
- `extractor_runs` table stores execution history
- `cloud_config` table stores provider credentials and configuration
- OS keyring stores local dev credentials (via `keyring` library)
- In-memory: `api/runner.py` tracks running subprocesses in `_running_processes` dict with threading lock

## Key Abstractions

**NormalizedCostRecord:**
- Purpose: Universal cost record schema across GCP, Azure, AWS, and LLM providers
- Definition: `models/__init__.py`
- Pattern: Pydantic BaseModel with provider-agnostic fields plus LLM-specific optional fields
- Used by: All extractors produce these; PostgreSQL `cost_records` table mirrors this schema

**Provider Enum:**
- Purpose: Type-safe cloud provider identification
- Definition: `models/__init__.py` (`aws`, `gcp`, `azure`, `llm`)
- Note: Duplicate `Provider` enum in `api/models.py` with only `azure` and `gcp`

**ServiceCategory Enum:**
- Purpose: Normalized service classification (compute, storage, network, database, ml, llm, other)
- Definition: `models/__init__.py`
- Mapping: Each extractor maps provider-specific service names to categories (e.g., Azure `DEFAULT_METER_CATEGORY_MAP` in `extractors/azure_cost.py`)

**ClientConfig:**
- Purpose: Complete multi-provider configuration for a FinOps client
- Definition: `config/schema.py`
- Pattern: Nested Pydantic models with validation (GCP projects, Azure subscriptions, aggregation settings, PostgreSQL, Superset)
- Has `to_env_dict()` method for generating extractor environment variables

**Extractor Health Tracking:**
- Purpose: Monitor extractor lifecycle and detect stale/failed runs
- Pattern: Each extractor calls `_mark_health_start()` before extraction and `_mark_health_success()` / `_mark_health_failure()` after
- Implementation duplicated across extractors (not shared from `health_check.py`)

## Entry Points

**FastAPI Application:**
- Location: `api/main.py`
- Triggers: `uvicorn api.main:app` (Docker CMD)
- Responsibilities: REST API for config CRUD, extractor orchestration, health monitoring
- Routes: `/healthz`, `/api/v1/config/*`, `/api/v1/extractors/*`, `/api/v1/auth/*`

**Extractor Dispatcher:**
- Location: `extractors/entrypoint.py`
- Triggers: `python -m extractors.entrypoint` (Docker ENTRYPOINT), or direct module execution
- Responsibilities: Read `EXTRACTOR_TYPE`, import and call corresponding extractor's `main()`

**Individual Extractors:**
- `extractors/gcp_billing.py` - `main()` function, runnable via `python -m extractors.gcp_billing`
- `extractors/azure_cost.py` - `main()` function, runnable via `python -m extractors.azure_cost`
- `extractors/exchange_rates.py` - `main()` function, runnable via `python -m extractors.exchange_rates`

**Config Wizard:**
- Location: `config/wizard.py`
- Triggers: `python -m config.wizard` or `python -m config`
- Responsibilities: Interactive TUI for creating complete client configurations

**Auth CLI:**
- Location: `config/auth.py`
- Triggers: `python -m config.auth azure` or `python -m config.auth gcp`
- Responsibilities: OAuth flows, credential persistence, optional API push

**Client Onboarding:**
- Location: `onboarding/setup_client.py`
- Triggers: `python -m onboarding.setup_client <client_id>`
- Responsibilities: Generate configs, connectivity tests, register client

## Error Handling

**Strategy:** Retry with exponential backoff for transient errors; fail-fast for configuration errors

**Patterns:**
- `tenacity` decorators on all cloud API calls and DB connections: `@retry(retry=retry_if_exception_type(...), stop=stop_after_attempt(3), wait=wait_exponential(...))`
- Extractors catch exceptions, mark health as failed, and re-raise
- API runner captures subprocess exit codes and logs in `extractor_runs` table
- Database operations use explicit `conn.commit()` / `conn.rollback()` (no ORM)
- `ON CONFLICT DO NOTHING` on all inserts for idempotent re-runs

## Cross-Cutting Concerns

**Logging:** Python `logging` module; loggers named by module path (e.g., `extractors.gcp_billing`). Format: `%(asctime)s [%(levelname)s] %(name)s - %(message)s`. Level defaults to INFO.

**Validation:** Pydantic v2 models for all input validation (API request/response schemas, config models, cost records). `field_validator` decorators for business rules.

**Authentication:** Multi-method credential resolution in `config/auth.py` with fallback chain. No authentication on the API itself.

**Currency Conversion:** Exchange rates fetched from ECB, stored in `exchange_rates` table, loaded at extraction time. Azure extractor converts non-USD costs; GCP billing is already in billing currency.

---

*Architecture analysis: 2026-04-17*
