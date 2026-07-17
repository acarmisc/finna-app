# finna-app — Agent Guide

Multi-cloud FinOps platform: Python FastAPI backend (API-only), cloud cost extractors, Grafana dashboards.

## Commands

```bash
# Install dependencies
uv sync

# Start dev server
uv run uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
uv run pytest -q                           # unit tests
uv run pytest -m integration               # integration tests (need running DB)
uv run pytest -m "not integration"         # skip integration tests

# Lint and typecheck (CI scope)
uv run ruff check backend/ extractors/ models/
uv run mypy backend/ extractors/ models/ --ignore-missing-imports --explicit-package-bases

# Full stack (API + PostgreSQL)
docker compose up --build
```

**Required env vars for local dev:** `PG_DSN`, `JWT_SECRET` (>=32 chars), `ENCRYPTION_KEY` (>=32 chars), `ALLOWED_ORIGINS`. Copy `.env.example` to `.env`.

## Architecture

**Backend entry points:**
- `backend/app/api/main.py` — FastAPI app factory, lifespan, CORS, rate limiting
- `backend/app/api/db.py` — async psycopg connection pool (`init_async_pool` at startup)
- `backend/app/api/auth.py` — JWT auth (`HS256` default), bcrypt passwords, OIDC support

**Key directories:**
- `backend/app/api/routes/` — endpoint modules: `costs.py`, `config.py`, `alerts.py`, `extractors_registry.py`, `wastage.py`, `auth_providers.py`, `oidc_auth.py`
- `backend/app/api/queries/` — SQL query modules per domain
- `backend/app/wastage/` — wastage rule engine (`rules/azure.py`, extensible via `@rule` decorator)
- `extractors/` — standalone cost extractors; dispatched via `EXTRACTOR_TYPE` env var (see `entrypoint.py`)
- `models/normalized.py` — shared Pydantic/data models
- `config/auth.py` — auth config helpers
- `utils/` — shared utilities (`encryption.py`, `log_sanitizer.py`)
- `sql/` — schema + seed data (`init.sql` for prod, `init_docker.sql` for CI/local)
- `alembic/` — top-level alembic config (CI uses this for migrations)
- `tests/` — pytest suite; `conftest.py` sets `TESTING=1` and generates random `JWT_SECRET`/`ENCRYPTION_KEY`

## CI Pipeline

`.github/workflows/ci.yml` runs on push to main/develop and PRs to main:
1. Lint + typecheck (`ruff check` + `mypy`)
2. Tests with postgres:16 service container (schema from `init_docker.sql`, then `alembic upgrade head`)
3. Docker build + push to `ghcr.io/acarmisc/finops-api` (main/tags only)

`.github/workflows/security.yml` — pip-audit, ruff, semgrep (continue-on-error), gitleaks, tests.

`.github/workflows/release.yml` — on `v*` tags: builds both `finops-api` and `finops-extractor` images, runs Trivy scan, creates GitHub Release.

## Key conventions

- **Python 3.11+** (pyproject says `>=3.11`, Dockerfiles use 3.12, CI uses 3.12)
- **Async psycopg** — always use the pool from `backend.app.api.db`; never raw connections
- **Tests set `TESTING=1`** — this bypasses pool init so tests don't need a real DB (conftest mocks or creates a small pool)
- **Integration tests** are marked `@pytest.mark.integration` and require a live PostgreSQL
- **Migrations**: two paths — `alembic upgrade head` (CI), or `AUTO_MIGRATE=true` env var in Docker (runs on boot)
- **Alembic DSN**: uses `PG_DSN` or `DATABASE_URL`; normalizes `postgres://` → `postgresql+psycopg://`
- **Two Dockerfiles**: `Dockerfile.api` (FastAPI backend) and `Dockerfile.extractor` (extractor runner, both Python 3.12-slim)
- **Extractor entrypoint**: `python -m extractors.entrypoint`, dispatches on `EXTRACTOR_TYPE` env var
- **Line length**: 120 (ruff.toml)

## Critical gotchas

- **Two SQL init files**: `init.sql` needs `pg_partman`/`pg_cron` (prod); `init_docker.sql` works with stock postgres (CI/local). Never use `init.sql` in Docker or CI.
- **Docker image COPY paths** use `python3.12` — if you bump the Python version in Dockerfiles, update the COPY paths too
- **`JWT_SECRET` and `ENCRYPTION_KEY`** are required at startup (app won't boot without them, >=32 chars each)
- **`ALLOWED_ORIGINS`** is required; wildcards (`*`) are rejected at startup
- **OIDC multi-replica warning**: in-memory state storage breaks under load balancers; set `DEPLOY_MODE=single` for single-replica