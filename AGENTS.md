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

All CI is in `.github/workflows/ci.yml` — consolidated pipeline that runs on main/tags:
- **Fast**: lint (ruff), typecheck (mypy + tsc), tests (pytest + jest)
- **Full**: multi-platform Docker build (amd64 + arm64) → ghcr.io
- **Stable**: GitHub release on tags, direct commit to staging k8s manifests

`docker-build.yml` — extractor image only (runs on tags).

**Important**: Repo blocks Actions from creating PRs — staging deploy commits directly to main.

## CI/CD Architecture

### Monolithic Container
The project now uses a **single Docker image** containing both frontend and backend:
- `Dockerfile.api` — for API/monolith builds (default)
- `Dockerfile.monolith` — explicit monolith build

**Container structure:**
- nginx on port 80 → serves frontend + proxies `/api/` to backend
- FastAPI backend on port 8000 (internal only)
- Frontend build output in `/app/ui/`

**Docker commands:**
```bash
# Build monolith
docker build -f Dockerfile.api -t finops-api .

# Run (local dev)
docker run --rm -p 80:80 -e PG_DSN=... -e JWT_SECRET=... finops-api
```

### Multi-Platform Builds
Images are built for `linux/amd64` and `linux/arm64` using Docker Buildx.
The cluster runs on `linux/amd64`; Apple Silicon dev machines use `linux/arm64`.

## Frontend conventions

See `ui/AGENTS.md` for routes, state, styling, auth specifics.

## Backend conventions

- Type-hint everything; mypy strict on routes and services.
- Use psycopg async with the connection pool from `backend.app.api.db`.
- JWT in `Authorization: Bearer ...`; configured via `backend.app.api.auth`.
