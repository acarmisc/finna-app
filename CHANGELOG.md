# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **FastAPI Orchestrator** - New API service for cloud credential management
  - `api/main.py` - FastAPI app with healthz endpoint
  - `api/db.py` - PostgreSQL connection pool and query helpers
  - `api/models.py` - Pydantic schemas for request/response
  - `api/routes/config.py` - CRUD endpoints for cloud configurations
  - `api/routes/extractors.py` - Run, status, and health endpoints
  - `api/routes/auth.py` - Device code flow endpoints (not fully tested)
  - `api/runner.py` - Subprocess executor with status tracking
  - `sql/migrations/001_cloud_config.sql` - DB schema for `cloud_config` and `extractor_runs` tables
  - `Dockerfile.api` - API container definition
  - `docker-compose.yml` - Updated with API service

- **CLI Integration** - New flags for API workflow
  - `--api-url` - Push config to API after auth (e.g., `http://localhost:8000`)
  - `--run` - Trigger extractor run after auth (requires `--api-url`)

- **AZURE_AUTH_METHOD Support** - New env var for CLI authentication
  - When `AZURE_AUTH_METHOD=cli`, extractor uses `AzureCliCredential` instead of `ClientSecretCredential`
  - Enables K8s deployment with credentials configured AFTER deployment (not before)

### Fixed

- **credential_type injection** - API now reads `credential_type` from DB column and injects into config JSON before passing to extractor
- **API config selection** - Changed to use most recent config (`ORDER BY created_at DESC`) instead of oldest
- **Credential type mapping** - CLI now maps `azure_cli` → `cli` when pushing to API

### Known Issues

- Auth proxy (`api/routes/auth.py`) not fully tested
- K8s manifests not yet implemented (Fase 7 of implementation plan)
- Records count shows 0 in API response even when records were extracted (parsing issue in runner.py)

---

## [Session: 2026-04-14] - FastAPI Orchestrator Implementation

### Goal

Implement an API-based orchestrator that:
1. Receives credentials from CLI after authentication
2. Persists them in PostgreSQL database
3. Executes extractors as subprocesses
4. Enables K8s deployment with credentials configured AFTER deployment

### Flow

```
CLI (az login) → POST /api/v1/config → DB
                                     ↓
                              POST /api/v1/extractors/run
                                     ↓
                              Subprocess: extractors.azure_cost
                                     ↓
                              26 cost records → PostgreSQL
```

### Testing

```bash
# Start API
docker-compose up -d postgres
PG_DSN="postgresql://finops:finops_dev@localhost:5432/finops" \
  .venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Run CLI with API integration
python -m config.auth azure --api-url http://localhost:8000 --run --auto-select
```

### Files Created/Modified

| File | Status |
|------|--------|
| `api/__init__.py` | Created |
| `api/db.py` | Created |
| `api/main.py` | Created |
| `api/models.py` | Created |
| `api/routes/__init__.py` | Created |
| `api/routes/auth.py` | Created |
| `api/routes/config.py` | Created |
| `api/routes/extractors.py` | Created |
| `api/runner.py` | Created |
| `sql/migrations/001_cloud_config.sql` | Created |
| `Dockerfile.api` | Created |
| `docker-compose.yml` | Modified |
| `config/auth.py` | Modified |
| `pyproject.toml` | Modified |

### Next Steps for Next Agent

1. **Test full end-to-end flow** - Already working ✓
2. **Implement K8s manifests** - Not yet done
3. **Fix records_extracted parsing** - Shows 0 in API response
4. **Add authentication to API** - Currently open
5. **Add rate limiting** - For production use
6. **Add monitoring/logging** - Structured logging, metrics

---

## [Previous Sessions]

See git log for earlier changes:
- `f2b42a3` - Azure cost extraction with RG-level scope
- `c58ea33` - Multi-subscription/multi-billing-account support
- `89d5b1b` - Fix numeric overflow and health-tracking bugs
- `b1104f9` - Add GCP CSV ingestion mode
