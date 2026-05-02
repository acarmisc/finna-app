# finna-app — Agent Guide

Multi-cloud FinOps platform: Python FastAPI backend + React/Vite/Tailwind frontend in a single monorepo.

## Repository layout

- `backend/` — FastAPI app, routes, services, alembic migrations.
- `extractors/` — GCP/Azure/AWS/LLM cost-data extractors.
- `models/` — shared Python data models.
- `ui/` — frontend (React + Vite + Tailwind v4 + Zustand + TanStack Query).
- `k8s/` — kustomize manifests for staging/prod.
- `tests/` — pytest suite for backend.
- `ui/` has its own Jest suite — see `ui/AGENTS.md` for frontend-specific conventions.

## Common commands

### Backend
- **Install**: `uv sync` (or `uv pip install --system -e ".[dev]"`)
- **Run dev**: `uv run uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000 --reload`
- **Tests**: `uv run pytest -q`
- **Type check**: `uv run mypy backend/ extractors/ models/`
- **Lint**: `uv run ruff check .`

### Frontend (run inside `ui/`)
- **Dev**: `cd ui && npm run dev` → http://localhost:5173
- **Build**: `cd ui && npm run build`
- **Tests**: `cd ui && npm test`

### Full stack
- `docker compose up --build` — boots api + postgres + ui together.

## CI

Path-filtered workflows live in `.github/workflows/`:
- `api-build.yml`, `ci.yml` — trigger on backend changes (skip `ui/**`).
- `ui-ci.yml`, `ui-build.yml` — trigger on `ui/**` changes only.
- `docker-build.yml` — extractor image (`Dockerfile.extractor`).
- `update-images.yml` — bumps k8s image tags.

## Frontend conventions

See `ui/AGENTS.md` for routes, state, styling, auth specifics.

## Backend conventions

- Type-hint everything; mypy strict on routes and services.
- Use psycopg async with the connection pool from `backend.app.api.db`.
- JWT in `Authorization: Bearer ...`; configured via `backend.app.api.auth`.
