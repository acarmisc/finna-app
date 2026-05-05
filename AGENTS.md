# finna-app — Agent Guide

Multi-cloud FinOps platform: Python FastAPI backend + React/Vite/Tailwind frontend in a single monorepo.

## Repository layout

- `backend/` — FastAPI app, routes, services, alembic migrations.
- `extractors/` — GCP/Azure/AWS/LLM cost-data extractors.
- `models/` — shared Python data models.
- `ui/` — frontend (React + Vite + Tailwind v4 + Zustand + TanStack Query).
- `k8s/` — kustomize manifests for staging/prod.
- `tests/` — pytest suite for backend.

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

`.github/workflows/ci.yml` — builds and pushes Docker images to ghcr.io on main/tags:
1. **Fast**: lint (ruff), typecheck (mypy + tsc), tests (pytest + jest)
2. **Build**: multi-platform Docker image (amd64 + arm64) → ghcr.io/acarmisc/finops-api

**No deployment steps** — CI only builds and pushes images.

`docker-build.yml` — separate workflow for extractor image (runs on tags).

## CI/CD Architecture

### Monolithic Container
- `Dockerfile.api` — builds both frontend + backend into single image
- nginx on port 80 → serves frontend + proxies `/api/` to backend
- FastAPI on port 8000 (internal only)

### Multi-Platform Builds
Images built for `linux/amd64` and `linux/arm64` using Docker Buildx.

## Design System

**Fonts** (loaded from Google Fonts in `ui/src/styles.css`):
- **Inter** — body text
- **JetBrains Mono** — numbers, IDs, labels
- **Press Start 2P** — pixel titles (login page, headers)

**Theme**: Dark-first pixel-art corporate style (radius 0, 1px borders, no blur shadows).

**Provider colors**: Azure (#0078d4), GCP (#ea4335), LLM (#7c3aed), AWS (#ff9900)

See `ui/design/wip/handoff/02-design-system.md` for full design tokens.

## Frontend

See `ui/AGENTS.md` for routes, state, styling, auth specifics.

## Backend

- Type-hint everything; mypy strict on routes and services.
- Use psycopg async with the connection pool from `backend.app.api.db`.
- JWT in `Authorization: Bearer ...`; configured via `backend.app.api.auth`.

## Known issues / gotchas

- **Docker build**: Use Python 3.14 paths in COPY commands (not 3.12)
- **Colima users**: If buildx cache corrupts, run `colima stop && colima start`
- **Dev server**: proxies `/api` to `http://localhost:8000`