# finna-app — Agent Guide

Multi-cloud FinOps platform: Python FastAPI backend (API-only).

## Repository layout

- `backend/` — FastAPI app, routes, services, alembic migrations.
- `extractors/` — GCP/Azure/AWS/LLM cost-data extractors.
- `models/` — shared Python data models.
- `tests/` — pytest suite for backend.

## Common commands

### Backend
- **Install**: `uv sync` (or `uv pip install --system -e ".[dev]"`)
- **Run dev**: `uv run uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000 --reload`
- **Tests**: `uv run pytest -q`
- **Type check**: `uv run mypy backend/ extractors/ models/`
- **Lint**: `uv run ruff check .`

### Full stack
- `docker compose up --build` — boots api + postgres together.

## CI

`.github/workflows/ci.yml` — builds and pushes Docker images to ghcr.io on main/tags:
1. **Fast**: lint (ruff), typecheck (mypy), tests (pytest)
2. **Build**: multi-platform Docker image (amd64 + arm64) → ghcr.io/acarmisc/finops-api

**No deployment steps** — CI only builds and pushes images.

## Backend

- Type-hint everything; mypy strict on routes and services.
- Use psycopg async with the connection pool from `backend.app.api.db`.
- JWT in `Authorization: Bearer ...`; configured via `backend.app.api.auth`.

## Known issues / gotchas

- **Docker build**: Use Python 3.14 paths in COPY commands (not 3.12)
- **Colima users**: If buildx cache corrupts, run `colima stop && colima start`

## Grafana Deployment (staging)

Runs in `finna-app-staging` namespace on GKE.

- **Deployment**: `/Users/andrea/Projects/personal/finna-app/deploy/k8s/grafana-deployment.yaml`
- **Image**: `grafana/grafana:latest` (v13.0.2)
- **Access**: port-forward `kubectl -n finna-app-staging port-forward svc/grafana 3000:3000`
- **Login**: `admin` / `Grafana2026!`

### Dashboards (6 FinOps dashboards, v2)
Stored in `/Users/andrea/Projects/personal/finna-app/grafana/*-v2.json`

| Dashboard | UID | Panels | Key SQL patterns |
|-----------|-----|--------|-----------------|
| Cost Overview | `finops-cost-overview` | 13 | `$__timeFilter(usage_start)`, `project_name IN ($project) OR project_name IS NULL` |
| Projects & Budgets | `finops-projects` | 7 | `fin_projects` table, `COALESCE(NULLIF(cost_center,''),'Uncategorized')` |
| Alerts | `finops-alerts` | 8 | `alert`, `alert_rule`, `alert_notification_state` tables |
| Configs & Extractors | `finops-configs` | 7 | `cloud_config`, `extractors` tables |
| Extractors & Runs | `finops-extractors` | 7 | `extractor_runs` table |
| Wastage | `finops-wastage` | 8 | `resource_wastage` table |

### Template variables (Cost Overview)
All use `includeAll: true` + `multi: true` pattern (multi-select with "All"):
- `$provider` — from `cost_records.provider`
- `$project` — from `cost_records.project_name`
- `$region` — from `cost_records.region`
- `$service` — from `cost_records.service_name`
- `$resource_type` — from `cost_records.resource_type`
- `DS_POSTGRES` — datasource selector

### Database (finna-staging)
- **Host**: `10.1.128.19:5432`, **User**: `finna-staging`, **DB**: `finna-staging`
- **PG_DSN**: `postgres://finna-staging:abstract.2026.A@10.1.128.19:5432/finna-staging?sslmode=require`

**Key tables**: `cost_records` (12,189 rows, azure+llm), `fin_projects` (22 azure projects, all budget_cap=0, mtd=0)

### Known Grafana issues
- **Port-forward must restart** after each pod replacement (killed automatically)
- **LLM NULL columns**: LLM provider records have `project_name IS NULL`, `region IS NULL` — SQL must use `OR column IS NULL` pattern
- **Multi-value All**: Use `column IN ($var) OR column IS NULL` instead of `($var = '' OR column IN ($var))` to avoid SQL syntax errors with multi-select
- **`fin_projects.budget_cap`** is `0` for all projects (no budgets configured) — panels show "No data" because budget-based queries filter `WHERE budget_cap > 0`
