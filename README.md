# finna-app

[![CI](https://github.com/acarmisc/finna-app/actions/workflows/ci.yml/badge.svg)](https://github.com/acarmisc/finna-app/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache_2.0-green.svg)](https://opensource.org/licenses/Apache-2.0)

Multi-cloud FinOps platform — normalize, aggregate, and visualize cost data from GCP, Azure, LLM gateways, and custom sources via a plugin-based extractor system.

## Architecture

```
Sources                    Extractors (plugins)           Storage           Visualization
─────────                 ─────────────────              ────────          ─────────────
GCP Billing  ──►  gcp_billing  ──┐
GCP CSV      ──►  gcp_csv      ──┤
Azure Cost   ──►  azure_cost   ──┼──► normalize ──► PostgreSQL ──►  Finna UI (React)
ECB Rates    ──►  exchange_rates──┤    + write         │           ──►  Superset (optional)
OTel/LLM     ──►  otel_llm *   ──┤                    │
Your source  ──►  custom_plugin ─┘                ──►  Alert queries
                                                    ──►  Daily aggregates
* otel_llm is planned — not yet implemented
```

## Quick Start

```bash
# 1. Install dependencies
uv sync
cd frontend && npm install && cd ..

# 2. Start PostgreSQL
docker compose -f deploy/docker-compose.yml up -d postgres

# 3. Run the Backend API
export PG_DSN="postgresql://finops:finops_dev@localhost:5432/finops"
make run-api

# 4. Populate sample data (optional - for local testing)
make seed

# 5. Start the Frontend (in a separate terminal)
make dev-frontend
# → Open http://localhost:5173
```

Smoke test:
```bash
bash scripts/smoke-test.sh
```

## Project Structure

Finna is organized into specialized directories for clarity and modularity:

*   **`backend/`**: Core server-side logic.
    *   `app/`: FastAPI orchestrator (auth, config, metrics).
    *   `extractors/`: Plugin-based extraction engine.
    *   `models/`: Shared Pydantic models.
    *   `alembic/`: Database schema migrations.
*   **`frontend/`**: Isolated React 18 / TypeScript / Vite application.
*   **`cli/`**: Interactive TUI wizards and cloud authentication tools.
*   **`deploy/`**: Containerization (Docker, Compose) and Kubernetes manifests.
*   **`resources/`**: Accessory assets (Superset dashboards, SQL scripts, fixtures).
*   **`docs/`**: Technical guides and operational runbooks.

## Extractor Plugins

Finna uses a plugin-based architecture. To add a new source:
1. Create a class inheriting from `ExtractorPlugin` in `backend/extractors/`.
2. Decorate with `@extractor_plugin`.
3. Register it in `backend/extractors/plugins.py`.

See the [Extractor Plugin Guide](docs/plugins-guide.md) for details.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Health check |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/api/v1/plugins` | List registered extractor plugins |
| `POST` | `/api/v1/extractors/run` | Start extractor run |
| `POST` | `/api/v1/auth/token` | Get JWT token |

## Testing

```bash
uv run pytest                    # Unit + integration tests
make build-frontend              # Verify frontend production build
```

## Docker

```bash
docker compose -f deploy/docker-compose.yml up -d
```

Build and push:
```bash
git tag v0.2.0 && git push origin v0.2.0  # Triggers CI build for finops-api + extractor
```

## License

[Apache License 2.0](LICENSE)
