# Technology Stack

**Analysis Date:** 2026-04-17

## Languages

**Primary:**
- Python 3.11+ (required minimum) / 3.12 (Docker runtime) - All application code

**Secondary:**
- SQL (PostgreSQL 16) - Schema definitions, migrations, seed data, materialized views
- YAML - Configuration files (client configs, registry, CI workflows)

## Runtime

**Environment:**
- Python 3.12 (Docker images use `python:3.12-slim`)
- PostgreSQL 16 (Alpine variant in Docker)

**Package Manager:**
- `uv` (Astral) - Used in Dockerfiles for fast installs (`ghcr.io/astral-sh/uv:latest`)
- `pip` - Standard fallback
- Lockfile: `uv.lock` present at project root

## Frameworks

**Core:**
- FastAPI >= 0.115 - REST API (`api/main.py`)
- Pydantic >= 2.0 - Data models, validation, serialization (`models/__init__.py`, `config/schema.py`, `api/models.py`)

**Testing:**
- pytest >= 9.0 - Test runner, config in `pyproject.toml` (`testpaths = ["tests"]`)

**Build/Dev:**
- Docker - Multi-stage builds for API and extractor containers
- docker-compose - Local development orchestration
- uv - Dependency resolution and installation

## Key Dependencies

**Critical:**
- `psycopg[binary]` >= 3.1 - PostgreSQL driver (sync and async), used throughout all data operations
- `google-cloud-bigquery` >= 3.11 - GCP billing data extraction from BigQuery
- `azure-mgmt-costmanagement` >= 4.0 - Azure Cost Management API queries
- `azure-identity` >= 1.14 - Azure authentication (DeviceCode, CLI, ClientSecret, DefaultAzure)
- `azure-mgmt-resource` >= 23.0 - Azure resource group discovery
- `msal` >= 1.30 - Microsoft Authentication Library for device code flow
- `msal-extensions` >= 1.3 - Encrypted token cache persistence

**Infrastructure:**
- `tenacity` >= 8.2 - Retry logic with exponential backoff (all extractors, DB connections)
- `uvicorn[standard]` >= 0.30 - ASGI server for FastAPI
- `pyarrow` >= 14.0 - BigQuery result serialization
- `boto3` >= 1.28 - AWS SDK (declared but no active extractor yet)

**CLI/TUI:**
- `questionary` >= 2.0 - Interactive prompts for config wizard and auth flows
- `rich` >= 13.0 - Terminal UI rendering (panels, tables, formatted output)
- `keyring` >= 25.0 - OS-level secure credential storage

**Data Processing:**
- `pyyaml` >= 6.0 - YAML config file parsing
- `python-dotenv` >= 1.0 - Environment variable loading from `.env` files

## Configuration

**Environment:**
- Configuration via environment variables (12-factor style)
- Key vars: `PG_DSN`, `EXTRACTOR_TYPE`, `GCP_PROJECT`, `BQ_DATASET`, `BQ_TABLE`, `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
- Multi-project/subscription support via prefixed env vars (`GCP_{PREFIX}_PROJECT`, `AZURE_{PREFIX}_SUBSCRIPTION_ID`)
- `.env` files generated per client by wizard but not committed

**Build:**
- `pyproject.toml` - Project metadata, dependencies, pytest config
- `Dockerfile.api` - API container (multi-stage, `python:3.12-slim`)
- `Dockerfile.extractor` - Extractor container (multi-stage, `python:3.12-slim`)
- `docker-compose.yml` - Local dev stack (API + extractor + PostgreSQL 16)

## Platform Requirements

**Development:**
- Python >= 3.11
- PostgreSQL 16 (or Docker for local)
- `uv` recommended for fast dependency installs
- Optional: `gcloud` CLI for GCP auth, `az` CLI for Azure auth

**Production:**
- Docker containers (API + extractors)
- PostgreSQL 16 with `pg_partman` and `pg_cron` extensions
- Cloud Run Jobs (extractors designed for this)
- Container registry: GitHub Container Registry (`ghcr.io`)

---

*Stack analysis: 2026-04-17*
