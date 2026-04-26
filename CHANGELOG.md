# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [Session: 2026-04-26] - GKE Staging Deployment & Azure Extraction Fix

### Goal

Deploy finna-app staging on GKE with Cloud SQL PostgreSQL connection and verify
Azure cost extraction works with stored SP credentials.

### Infrastructure

- **Cluster**: `REDACTED-CLUSTER-NAME`
- **Namespace**: `finna-app-staging`
- **Cloud SQL**: `REDACTED-INSTANCE-NAME` private IP `REDACTED-PRIVATE-IP:5432`
- **Database**: `finna-staging` (user: `finna-staging`, password: `REDACTED-DB-PASSWORD`)
- **Ingress**: Traefik with letsencrypt-prod, LB `REDACTED-LB-IP`
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
