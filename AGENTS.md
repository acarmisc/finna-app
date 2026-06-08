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
