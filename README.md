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

# 2. Start PostgreSQL
docker compose up -d postgres

# 3a. Run the API
export PG_DSN="postgresql://finops:finops_dev@localhost:5432/finops"
uv run python -m uvicorn api.main:app --port 8000

# 3b. Authenticate (optional — for cloud extraction)
uv run python -m config.auth azure    # Azure: browser login
uv run python -m config.auth gcp     # GCP: delegates to gcloud

# 4. Run an extractor
EXTRACTOR_TYPE=exchange_rates docker compose --profile extractors up extractor

# 5. Start the frontend (in a separate terminal)
npm install && npm run dev
# → Open http://localhost:5173
```

Smoke test:
```bash
bash scripts/smoke-test.sh
```

## Extractor Plugins

Finna uses a plugin-based architecture. Each extractor declares:

- **Metadata**: `display_name`, `description`, `provider`
- **Auth methods**: What authentication options it supports (e.g. device code, service principal, ADC)
- **Config fields**: What configuration the frontend should render (text, password, select, etc.)

### Built-in plugins

| Type | Provider | Auth | Description |
|------|----------|------|-------------|
| `gcp_billing` | GCP | ADC, service account key | BigQuery billing export |
| `gcp_csv` | GCP | — | CSV billing file |
| `azure_cost` | Azure | Device code, service principal, Azure CLI | Cost Management API |
| `exchange_rates` | ECB | None | Daily ECB forex rates |

### Writing a custom plugin

1. Create `extractors/my_source.py`:

```python
from extractors.base import ExtractorPlugin, ConfigField, extractor_plugin

@extractor_plugin("my_source", display_name="My Source", description="Extract from My Source API")
class MySourcePlugin(ExtractorPlugin):
    def extract(self) -> int:
        # Your extraction logic here
        # Config values available via self.config["field_name"]
        # Write rows to PostgreSQL via self.pg_dsn
        return 42  # number of records inserted

    def health_name(self) -> str:
        return "my_source"

    @classmethod
    def config_fields(cls) -> list[ConfigField]:
        return [
            ConfigField(name="api_key", label="API Key", field_type="password"),
            ConfigField(name="region", label="Region", required=False,
                        options=[{"value": "us", "label": "US East"}, {"value": "eu", "label": "EU West"}]),
        ]

    @classmethod
    def auth_methods(cls) -> list[dict[str, str]]:
        return [{"id": "apikey", "label": "API Key", "sub": "Static key authentication"}]

    @classmethod
    def provider_id(cls) -> str:
        return "my_cloud"
```

2. Register it by adding to `EXTRACTOR_PLUGINS` env var or `extractors/plugins.py` `DISCOVERY_MODULES` list.

3. The frontend automatically picks it up via `GET /api/v1/plugins` and renders the correct connection form.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Health check |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/api/v1/plugins` | List registered extractor plugins |
| `GET` | `/api/v1/plugins/{type}` | Get single plugin metadata |
| `GET` | `/api/v1/config` | List cloud configurations |
| `POST` | `/api/v1/config` | Create configuration |
| `GET` | `/api/v1/config/{id}` | Get configuration |
| `PUT` | `/api/v1/config/{id}` | Update configuration |
| `DELETE` | `/api/v1/config/{id}` | Delete configuration |
| `POST` | `/api/v1/extractors/run` | Start extractor run |
| `GET` | `/api/v1/extractors/status` | List recent runs |
| `GET` | `/api/v1/extractors/status/{id}` | Get run detail |
| `POST` | `/api/v1/extractors/cancel/{id}` | Cancel running extractor |
| `GET` | `/api/v1/extractors/health` | Extractor health status |
| `POST` | `/api/v1/auth/token` | Get JWT token |
| `POST` | `/api/v1/auth/device-code` | Start device code flow |
| `POST` | `/api/v1/auth/token/poll` | Poll device code token |

## Project Structure

```
api/                 FastAPI orchestrator (auth, config, extractors, plugins, metrics)
config/              CLI auth wizard and Pydantic config schema
extractors/          Extractor plugins
  base.py            ExtractorPlugin ABC and @extractor_plugin decorator
  plugins.py         Built-in plugin registration and discovery
  gcp_billing.py      GCP BigQuery extractor
  gcp_csv.py          GCP CSV file extractor
  azure_cost.py       Azure Cost Management extractor
  exchange_rates.py    ECB exchange rate extractor
  gcp_shared.py       GCP normalization utilities
  health_check.py     Extractor health query utility
models/              Shared Pydantic models (NormalizedCostRecord)
sql/                DDL, seed data, migrations, alert queries
src/                React/TypeScript frontend (Vite)
  api/               API client layer (fetch hooks, auth, types)
  components/        UI components (screens, modals, common)
  hooks/             React hooks (useTheme, useLocalStorage, useAppData)
  data/              Mock fallback data (used when API is unavailable)
tests/              pytest suite (12 test files)
scripts/            Operational scripts (smoke-test.sh)
superset/           Dashboard bootstrap for existing Superset instance
```

## Configuration

### CLI / TUI

```bash
# Interactive wizard
uv run python -m config.wizard

# Direct auth
uv run python -m config.auth azure --api-url http://localhost:8000 --run
uv run python -m config.auth gcp --api-url http://localhost:8000 --run
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `PG_DSN` | PostgreSQL connection string | Yes |
| `ENCRYPTION_KEY` | Fernet key for secret encryption | Yes (API) |
| `JWT_SECRET` | JWT signing key | Yes (API) |
| `EXTRACTOR_TYPE` | Which extractor to run | Yes (Docker) |
| `EXTRACTOR_PLUGINS` | Comma-separated Python modules for third-party plugins | No |
| `AUTO_MIGRATE` | Run Alembic migrations on startup | No (default: false) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry collector endpoint | No |

### Database

`sql/init.sql` creates partitioned tables, materialized views, and 90 days of seed data. See `alembic/` for migrations.

## Testing

```bash
uv run pytest                    # Unit + integration tests
uv run ruff check .              # Lint
uv run mypy api/ extractors/      # Type check
```

## Docker

```bash
docker compose up -d                    # Postgres only
docker compose --profile extractors up  # + extractors
```

Build and push:
```bash
git tag v1.0.0 && git push origin v1.0.0  # Builds finops-api + finops-extractor
```

## License

[Apache License 2.0](LICENSE)