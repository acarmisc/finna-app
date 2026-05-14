# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v1.3.0] - 2026-05-14

### Added
- `extractors/litellm_cost.py`: LiteLLM proxy spend extractor. Pulls `/spend/logs?summarize=false`, paginated, normalizes per-request transactions into `cost_records` with `provider='llm'`. Covers all 5 cost dimensions: model (`service_name`/`model_name`), period (`usage_start`/`usage_end`), user (`account_id` + `tags.end_user`), task (`project_id` via `LITELLM_TASK_TAG_PREFIX`), team (`team`). Idempotent via `ON CONFLICT (record_id) DO NOTHING`.
- `extractors/entrypoint.py`: registered `litellm_cost` in `EXTRACTOR_MAP`.
- `backend/app/api/runner.py`: provider `llm`/`litellm` → `litellm_cost`; env build from cloud_config (`LITELLM_BASE_URL`, `LITELLM_MASTER_KEY`, `LITELLM_PAGE_SIZE`, `LITELLM_TIMEOUT`, `LITELLM_TASK_TAG_PREFIX`).
- `tests/test_litellm_cost.py`: 20 unit tests (parsers, normalization, pagination via `httpx.MockTransport`, insert path, env-guard paths).

### Notes
- Validated end-to-end on staging: 1812 spend log rows → 375 records inserted ($52.80 USD, 73.5M tokens) across opus-4-7 / sonnet-4-6 / haiku-4-5.
- `_mark_health_*` is schema-aware: tolerates both `last_run_start`/`last_run_end` (init.sql) and `last_run_ts` (init_docker.sql) shapes; failures are best-effort.
- LiteLLM stores spend in USD only — `cost_original = cost_usd`, `currency_original = "USD"`. No exchange-rate join.

## [v1.1.0] - 2026-05-07

### Added
- `ci(release)`: build & push UI image (`finops-ui`) to GHCR, plus conditional GCR push to `europe-west1-docker.pkg.dev/abs-digital-playground/finna-app-staging/frontend` when `GCP_SA_KEY` is set
- `ui/screenshots/`: QA evidence merged from archived `acarmisc/finna-app-ui` repo

### Fixed
- `db.py`: 3-attempt exponential-backoff retry on `PoolTimeout` for sync + async connections; replaced `assert` in `get_*_pool` with explicit `ValueError`; satisfy mypy `[return]` on `get_connection` retry loop (#125, fixes #110)
- `auth.py`: annotate `response.json()` returns to satisfy mypy `no-any-return`
- `ci(release)`: build UI `dist/` (`npm ci && npm run build`) before docker buildx context; use job-level `env.HAS_GCP` instead of `secrets.X` in `if:` (invalid)
- `k8s/base/cronjob-azure.yaml`: switch from `europe-west1-docker.pkg.dev/.../api:latest` to `ghcr.io/acarmisc/finna-app/finops-extractor:1.1.0` (proper extractor image)

### Changed
- repo hygiene: untrack 130 `graphify-out/*` artifacts (already gitignored); drop `sql/seed_default_user.sql` and its `docker-compose.yml` mount
- archived legacy `acarmisc/finna-app-ui` repo; all useful work merged into monorepo `ui/`

### Deployment
- Helm release `finna-app` in `finna-app-staging` namespace upgraded to chart `1.0.1` / appVersion `1.1.0`; chart `values.yaml` `image.repository` aligned to `ghcr.io/acarmisc/finna-app/finops-api`, `image.tag: 1.1.0` to remove drift from manual `kubectl set image` patches

## [Session: 2026-04-27] - Azure Cronjob API-Triggered Extraction

### Goal

Fix Azure extraction workflow: cronjob should trigger API instead of direct extractor,
poll for completion status, then complete job with success/failure.

### Problem

Previously, cronjob tried to run extractors directly with Kubernetes secrets.
But finna-app stores credentials in PostgreSQL `cloud_config` table and triggers
extractors via API. The Kubernetes secrets approach was mismatched.

### Solution

- **Cronjob now triggers API**: `POST /api/v1/extractors/run` endpoint
- **Polling**: Cronjob monitors `GET /api/v1/extractors/run/{id}` until completion
- **Final status**: Job completes with success/failure based on API extraction result
- **Auth via secrets**: API_USERNAME/API_PASSWORD stored in Kubernetes secret

### Architecture Changes

| Component | Old Approach | New Approach |
|-----------|-------------|--------------|
| Credentials | `k8s secrets` | DB `cloud_config` + API auth |
| Extraction | Direct subprocess | API-triggered subprocess |
| Status | Command exit code | API status polling |
| Cronjob | `finops-extractor:latest` | API image (`api:latest`) |

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `EXTRACTOR_PROVIDER` | Provider name (`azure`, `gcp`) |
| `CONFIG_ID` | Cloud config ID from DB (default: 1) |
| `API_URL` | API endpoint URL |
| `AUTH_USERNAME` | API basic auth username |
| `AUTH_PASSWORD` | API basic auth password |
| `PG_DSN` | PostgreSQL connection for status checks |

### Testing

```bash
# Trigger manual extraction
kubectl create job --from=cronjob/finops-extractor-azure manual-azure-extract -n finna-app-staging

# Check status
kubectl get jobs manual-azure-extract -n finna-app-staging
kubectl get pods -l job-name=manual-azure-extract -n finna-app-staging

# Watch API logs
kubectl logs -f deployment/finops-api -n finna-app-staging
```

### Files Created/Modified

| File | Status |
|------|--------|
| `k8s/base/cronjob-azure.yaml` | Modified (API-triggered extraction) |
| `k8s/base/secret.yaml` | Modified (added API credentials, full Azure config) |

### Next Steps

- Test actual extraction with polling
- Verify status updates in `extractor_runs` table
- Confirm job completion status matches extraction result
- Add metrics endpoint for observability
- Consider adding `activeDeadlineSeconds` to prevent stuck jobs

---

## [Session: 2026-04-26] - GKE Staging Deployment & Azure Extraction Fix

## [Session: 2026-04-26] - GKE Staging Deployment & Azure Extraction Fix

### Goal

Deploy finna-app staging on GKE with Cloud SQL PostgreSQL connection and verify
Azure cost extraction works with stored SP credentials.

### Infrastructure

- **Cluster**: `gke_abs-digital-playground_europe-west1_abs-ces-n8w`
- **Namespace**: `finna-app-staging`
- **Cloud SQL**: `ces-dev-db-03` private IP `10.1.128.19:5432`
- **Database**: `finna-staging` (user: `finna-staging`, password: `abstract.2026.A`)
- **Ingress**: Traefik with letsencrypt-prod, LB `34.79.180.243`
- **API URL**: `https://finna-app.ces.abssrv.it`

### Key Issues Fixed

1. **Encrypted credentials not decrypted in runner.py**
   - `cloud_config.client_secret` is stored as Fernet-encrypted blob (`__enc__: True`)
   - `runner.py` was reading `config.get("client_secret")` which returned `None`
   - This caused `AZURE_AUTH_METHOD=cli` fallback → `DefaultAzureCredential` → all RGs failed
   - **Fix**: Added `decrypt_config()` call before building subprocess env vars

2. **AZURE_TENANT_ID/AZURE_CLIENT_ID/AZURE_CLIENT_SECRET not passed to extractor**
   - When `azure_cost.py` builds `multi_subs` from saved subscription selections,
     it was not including `tenant_id/client_id/client_secret` from env vars
   - **Fix**: Modified `azure_cost.py` to include credentials from env vars when
     building multi_subs selections so `ClientSecretCredential` is used

3. **async pool initialization mismatch**
   - `main.py` called `init_pool()` but pool method was `init_async_pool()`
   - `close_pool()` → `close_pools()`, connection uses `async with` context manager

### Azure Extraction Results

- **9,504 records** extracted across 22 resource groups in ~10 minutes
- All 22 RGs succeeded with `ClientSecretCredential` authentication
- Resource groups: ABS-ATOS-DEV (38), ABS-DEVOPS-RESOURCES (527), ABS-GEOSTRATEGY-DEV (341),
  ABS-SHIELD-DEV (324), ABS-TEST-GEN-AI (155), ABS-VSP (56), MyLux4Consumers (720),
  OrderTracker (186), RayBanDev (348), Recon3Dev (655), Recon3Test (620), RedCarpet (1073),
  Sgsfs (777), SmartRetailOperations (867), WCS-Test (175), databricks-rg-shield-dev-dbks (207),
  MC_ABS-DEVOPS-RESOURCES (589), MC_ABS-GEOSTRATEGY-DEV (434), MC_ABS-SHIELD-DEV (435),
  MC_ABS-SITE-DEV_abssitedevaks (367), MC_ABS-SITE-DEV_abssitedevaks-bck (57),
  MC_SmartRetailOperations_sro2-aks (553)

### Files Created/Modified

| File | Status |
|------|--------|
| `config/__init__.py` | Created |
| `config/auth.py` | Created |
| `k8s/overlays/staging-deploy/namespace.yaml` | Created |
| `k8s/overlays/staging-deploy/configmap.yaml` | Created |
| `k8s/overlays/staging-deploy/serviceaccount.yaml` | Created |
| `k8s/overlays/staging-deploy/deployment.yaml` | Created |
| `k8s/overlays/staging-deploy/service.yaml` | Created |
| `k8s/overlays/staging-deploy/ingress.yaml` | Created |
| `backend/app/api/runner.py` | Modified (decrypt_config fix) |
| `extractors/azure_cost.py` | Modified (multi-subs credential fix) |
| `backend/app/api/main.py` | Modified (async pool fix) |
| `Dockerfile.api` | Modified (add config/ module) |
| `docker-compose.yml` | Modified |

---

## [Session: 2026-04-14] - FastAPI Orchestrator Implementation
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
- ~~Records count shows 0 in API response even when records were extracted~~ - **Fixed** (9,504 records extracted in latest run)

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
