# Finna — FinOps Backend

FastAPI backend for the FinOps platform — cloud cost extraction, aggregation, and API.

> The frontend lives in the sibling repo [finna-app-ui](https://github.com/acarmisc/finna-app-ui).

## Quick Start

### Backend only (with mock data)

```bash
# Terminal — Mock API server
bun backend/frontend/mock-server.ts
```

→ http://localhost:8000/docs (Swagger UI)

### Backend only (with real database)

```bash
# Terminal — Real API backend
cd backend
python -m app.api.main
```

→ http://localhost:8000 (API)

### Docker Compose

```bash
docker-compose up --build
```

→ http://localhost:8000 (API), http://localhost:3000 (frontend from finna-app-ui)

## Project Structure

```
finna-app/
├── backend/
│   ├── app/api/              # FastAPI app + routes
│   │   ├── main.py           # FastAPI app entry
│   │   ├── auth.py           # JWT auth
│   │   ├── costs.py          # Cost data CRUD
│   │   ├── config.py         # Connections CRUD
│   │   ├── alerts.py         # Alert management
│   │   └── extractors.py     # Extractor orchestration
│   └── frontend/
│       └── mock-server.ts    # Bun mock API server (for dev)
├── extractors/               # Cloud cost extractors (GCP, Azure, LLM)
├── aggregation/              # Cost aggregation engine
├── alembic/                  # Database migrations
├── sql/                      # SQL init scripts & migrations
├── tests/                    # Python tests
├── k8s/                      # Kubernetes manifests
├── pyproject.toml            # Python dependencies (uv)
├── Dockerfile.api            # API container
├── Dockerfile.extractor      # Extractor container
└── docker-compose.yml        # Local dev stack
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/token` | No | Login, returns JWT |
| GET | `/healthz` | No | Health check |
| GET | `/api/v1/costs` | Yes | Cost records |
| GET | `/api/v1/costs/totals` | Yes | Aggregated totals |
| GET | `/api/v1/costs/daily` | Yes | Daily breakdown for chart |
| GET | `/api/v1/costs/by-sku` | Yes | SKU-level costs |
| GET | `/api/v1/config` | Yes | Connections list |
| POST | `/api/v1/config` | Yes | Create connection |
| DELETE | `/api/v1/config/:id` | Yes | Delete connection |
| GET | `/api/v1/alerts` | Yes | All alerts |
| GET | `/api/v1/alerts/active` | Yes | Firing alerts only |
| GET | `/api/v1/extractors/status` | Yes | Run history |
| POST | `/api/v1/extractors/run` | Yes | Trigger extractor |
| GET | `/api/v1/config/projects` | Yes | Projects list |

## Authentication

Default credentials: `admin` / `admin`

Returns a JWT token stored in the frontend's `localStorage` as `finna-auth-token`.

## Mock Server

The mock server (`backend/frontend/mock-server.ts`) provides:
- Full API schema matching the real backend
- Seed data: 7 connections, 15 cost records, 5 runs, 4 alerts, 30 days of daily costs
- JWT auth with `admin/admin` or `user/password`

Start: `bun backend/frontend/mock-server.ts`

## Development

### Run tests

```bash
pytest
```

### Run linter

```bash
ruff check .
```

### Run type checker

```bash
mypy backend/ extractors/ || exit 0
```

## CI/CD

- **CI**: Runs pytest, ruff, mypy on every push/PR to `main`
- **Docker**: Builds and pushes extractor image to GHCR on `v*` tags

## Docker

### API

```bash
docker build -f Dockerfile.api -t finna-api .
docker run --rm -p 8000:8000 -e PG_DSN=... finna-api
```

### Extractor

```bash
docker build -f Dockerfile.extractor -t finna-extractor .
docker run --rm -e EXTRACTOR_TYPE=gcp_billing finna-extractor
```
