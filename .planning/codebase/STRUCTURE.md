# Codebase Structure

**Analysis Date:** 2026-04-17

## Directory Layout

```
finna-app/
├── api/                    # FastAPI REST API (orchestrator)
│   ├── __init__.py
│   ├── main.py             # FastAPI app, lifespan, health check, router mounting
│   ├── db.py               # PostgreSQL connection helpers (sync + async)
│   ├── models.py           # Pydantic request/response schemas
│   ├── runner.py           # Extractor subprocess launcher and monitor
│   └── routes/             # API route modules
│       ├── __init__.py
│       ├── auth.py         # Device code OAuth flow endpoints
│       ├── config.py       # Cloud config CRUD endpoints
│       └── extractors.py   # Extractor run/status endpoints
├── aggregation/            # Infrastructure metrics aggregation engine
│   ├── __init__.py
│   ├── config.py           # Aggregation defaults (window sizes)
│   └── engine.py           # Core aggregation logic + batch insert
├── config/                 # Authentication and configuration
│   ├── __init__.py
│   ├── __main__.py         # `python -m config` entrypoint
│   ├── auth.py             # Multi-provider OAuth flows + credential management
│   ├── schema.py           # Pydantic models for full client configuration
│   └── wizard.py           # Interactive TUI configuration wizard
├── extractors/             # Cloud cost data extractors
│   ├── __init__.py
│   ├── entrypoint.py       # Dispatcher: reads EXTRACTOR_TYPE, imports correct module
│   ├── azure_cost.py       # Azure Cost Management extractor (~840 lines)
│   ├── exchange_rates.py   # ECB exchange rate extractor
│   ├── gcp_billing.py      # GCP BigQuery billing extractor
│   ├── gcp_csv.py          # GCP CSV billing file importer
│   ├── gcp_shared.py       # Shared GCP normalization utilities
│   └── health_check.py     # Extractor health monitoring utilities
├── models/                 # Shared data models
│   ├── __init__.py         # NormalizedCostRecord, Provider, ServiceCategory
│   └── normalized.py       # Re-exports from __init__.py
├── onboarding/             # Client onboarding automation
│   └── setup_client.py     # Idempotent client directory + config generation
├── sql/                    # Database schema and migrations
│   ├── init.sql            # Full schema: tables, indexes, partitioning, seed data
│   ├── init_local.sql      # Local development init variant
│   ├── alert_queries.sql   # Alert/monitoring SQL queries
│   └── migrations/         # Incremental migrations
│       └── 001_cloud_config.sql  # cloud_config + extractor_runs tables
├── superset/               # Apache Superset integration
│   ├── bootstrap.py        # Dashboard provisioning via Superset REST API
│   └── superset_config.py  # Superset Flask configuration
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── test_aggregation_engine.py
│   ├── test_azure_extractor.py
│   ├── test_exchange_rates.py
│   ├── test_gcp_extractor.py
│   ├── test_gcp_shared.py
│   ├── test_health_check.py
│   └── test_multi_subscription.py
├── data/                   # Data directory (CSV mounts, etc.)
├── docs/                   # Documentation
├── Dockerfile.api          # Multi-stage Docker build for API
├── Dockerfile.extractor    # Multi-stage Docker build for extractors
├── docker-compose.yml      # Local dev: API + extractor + PostgreSQL
├── pyproject.toml          # Project metadata, dependencies, pytest config
├── uv.lock                 # Dependency lockfile
├── CHANGELOG.md
├── README.md
└── LICENSE                 # Apache-2.0
```

## Directory Purposes

**`api/`:**
- Purpose: REST API orchestrator for cloud credential management and extractor execution
- Contains: FastAPI application, route handlers, database helpers, subprocess runner
- Key files: `main.py` (app definition), `runner.py` (subprocess management), `db.py` (all SQL execution)

**`extractors/`:**
- Purpose: Standalone cloud cost data extraction modules
- Contains: One module per cloud provider/data source, each with `main()` entrypoint
- Key files: `entrypoint.py` (dispatcher), `azure_cost.py` (largest at ~840 lines)
- Pattern: Each extractor follows the same structure: config from env vars, fetch data, normalize rows, batch-insert, track health

**`models/`:**
- Purpose: Shared Pydantic data models used across extractors and API
- Contains: `NormalizedCostRecord`, `Provider` enum, `ServiceCategory` enum
- Note: `normalized.py` just re-exports from `__init__.py` (redundant)

**`config/`:**
- Purpose: Authentication flows, configuration schemas, and setup wizard
- Contains: OAuth/auth implementations, full client config Pydantic models, interactive TUI
- Key files: `auth.py` (credential management, ~880 lines), `schema.py` (config models), `wizard.py` (interactive setup)

**`aggregation/`:**
- Purpose: Statistical aggregation of infrastructure metrics into time windows
- Contains: Window alignment, percentile computation, batch insert to `infra_metrics_agg`
- Status: Core logic implemented, standalone job entrypoint is a skeleton

**`sql/`:**
- Purpose: PostgreSQL schema management
- Contains: Full init script with partitioning and seed data, incremental migrations
- Key files: `init.sql` (production-ready schema), `migrations/001_cloud_config.sql`

**`onboarding/`:**
- Purpose: Automated new-client provisioning
- Contains: Script that generates client-specific configs and connectivity tests under `clients/` directory

**`superset/`:**
- Purpose: Apache Superset dashboard auto-provisioning
- Contains: Bootstrap script that calls Superset REST API to create database connections and datasets

**`tests/`:**
- Purpose: Unit tests for extractors, aggregation, and health checks
- Contains: pytest test files, one per component

## Key File Locations

**Entry Points:**
- `api/main.py`: FastAPI application (`uvicorn api.main:app`)
- `extractors/entrypoint.py`: Extractor dispatcher (`python -m extractors.entrypoint`)
- `config/__main__.py`: Config module entry (`python -m config`)
- `config/wizard.py`: Interactive wizard (`python -m config.wizard`)
- `config/auth.py`: Auth CLI (`python -m config.auth <provider>`)
- `onboarding/setup_client.py`: Client setup (`python -m onboarding.setup_client <id>`)

**Configuration:**
- `pyproject.toml`: Dependencies, project metadata, pytest paths
- `docker-compose.yml`: Local dev services
- `Dockerfile.api`: API container build
- `Dockerfile.extractor`: Extractor container build
- `.github/workflows/docker-build.yml`: CI pipeline

**Core Logic:**
- `models/__init__.py`: `NormalizedCostRecord` definition (shared data contract)
- `extractors/gcp_billing.py`: GCP BigQuery extraction pipeline
- `extractors/azure_cost.py`: Azure Cost Management extraction pipeline
- `extractors/exchange_rates.py`: ECB exchange rate extraction
- `aggregation/engine.py`: Metrics aggregation algorithms
- `config/auth.py`: Multi-provider authentication with keyring persistence
- `config/schema.py`: Full client configuration Pydantic models
- `api/runner.py`: Subprocess-based extractor orchestration

**Database:**
- `sql/init.sql`: Complete schema with partitioning, indexes, materialized views, seed data
- `sql/migrations/001_cloud_config.sql`: Cloud config and extractor runs tables
- `api/db.py`: Database connection management and query helpers

**Testing:**
- `tests/test_aggregation_engine.py`: Aggregation logic tests
- `tests/test_azure_extractor.py`: Azure cost extraction tests
- `tests/test_gcp_extractor.py`: GCP billing extraction tests
- `tests/test_exchange_rates.py`: ECB rate extraction tests
- `tests/test_health_check.py`: Health monitoring tests
- `tests/test_multi_subscription.py`: Multi-subscription discovery tests

## Naming Conventions

**Files:**
- `snake_case.py` for all Python modules (e.g., `gcp_billing.py`, `azure_cost.py`)
- `UPPERCASE.sql` not used; SQL files use `snake_case` with numeric prefix for migrations (e.g., `001_cloud_config.sql`)

**Directories:**
- `snake_case` for all directories (e.g., `extractors/`, `aggregation/`)
- Each directory is a Python package with `__init__.py`

## Where to Add New Code

**New Cloud Provider Extractor:**
1. Create `extractors/{provider}_cost.py` with `main()` function following existing pattern
2. Add entry to `EXTRACTOR_MAP` in `extractors/entrypoint.py`
3. Add provider to `Provider` enum in `models/__init__.py`
4. Add service category mapping (like `DEFAULT_METER_CATEGORY_MAP` in `extractors/azure_cost.py`)
5. Add tests in `tests/test_{provider}_extractor.py`
6. Add provider mapping in `api/runner.py` (`_get_extractor_type()`)

**New API Endpoint:**
1. Create route module in `api/routes/{feature}.py` with `APIRouter()`
2. Add Pydantic request/response models to `api/models.py`
3. Mount router in `api/main.py` with `app.include_router()`
4. Use `api/db.py` helpers (`query_one`, `query_all`, `execute`, `insert_and_return`) for database access

**New Database Table:**
1. Add to `sql/init.sql` for full-schema definition
2. Create migration file in `sql/migrations/` (e.g., `002_new_table.sql`)
3. Migration auto-runs on API startup via `api/db.py` `init_db()`

**New Configuration Section:**
1. Add Pydantic model to `config/schema.py`
2. Add wizard prompts to `config/wizard.py`
3. Include in `ClientConfig` model

**Utilities/Shared Code:**
- Shared extraction helpers: `extractors/gcp_shared.py` (or create `extractors/shared.py`)
- Shared Pydantic models: `models/__init__.py`
- Database utilities: `api/db.py`

## Special Directories

**`data/`:**
- Purpose: Mount point for CSV billing exports
- Generated: No (data is user-provided)
- Committed: Directory exists but contents are not committed

**`clients/`:**
- Purpose: Per-client configuration directories generated by wizard/onboarding
- Generated: Yes (by `config/wizard.py` and `onboarding/setup_client.py`)
- Committed: No (contains secrets in `.env` files)

**`.planning/`:**
- Purpose: Planning and analysis documents
- Generated: Yes (by tooling)
- Committed: Depends on project policy

---

*Structure analysis: 2026-04-17*
