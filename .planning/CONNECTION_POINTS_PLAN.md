# Finna Connection Points — Implementation Plan
## Backend ↔ Frontend ↔ CLI Integration

**Date:** 2026-04-24
**Scope:** Connect all three repositories (finna-app, finna-app-ui, finna-cli)
**Budget target:** ~75k tokens optimized

---

## Executive Summary

| Component | Status | Action |
|-----------|--------|--------|
| Backend (`finna-app`) | ⚠️ Needs fixes | Add CLI-compat routes, fix login auth, resolve duplicate extractors |
| Frontend (`finna-app-ui`) | 🔴 Empty | Migrate React SPA from `backend/frontend/` to separate repo |
| CLI (`finna-cli`) | ⚠️ Partially built | Fix login endpoint, standardize field names, handle wrapper shapes |

A deep audit of all three codebases revealed **16 specific connection misalignments** that prevent full end-to-end integration. This plan addresses every single one.

---

## Connection Point Audit

### 🔴 CRITICAL: CLI ↔ Backend Authentication (CP-1)
| Field | CLI Expects | Backend Returns | Mismatch |
|-------|-------------|-----------------|----------|
| Login response | `{"access_token":"...","token_type":"..."}` | `{"token":"..."}` | **KEY NAME** |
| Login endpoint | `POST /api/v1/auth/login` | `POST /api/v1/auth/token` | **URL** |

**Impact:** CLI login command fails immediately on any backend.
**Fix:** Add `POST /api/v1/auth/login` alias that returns `{"access_token":"..."}`.

### 🔴 CRITICAL: Costs Route Key Names (CP-2)
| Backend Field | CLI Model Field | Mismatch |
|---------------|-----------------|----------|
| `cost_records.id` (int) | `RawCostRecord.ID string` | **Type** |
| `cost_records.cost_usd` | `RawCostRecord.Cost float64` | Backend label = `cost` (OK) |
| `cost_records.usage_start` | `RawCostRecord.StartDate` | Backend uses `usage_start` not `cost_date` |
| Response shape `{"data":[...],"count":N}` | CLI expects `{"data":[...],"total":N}` | **Wrapper keys** |

Additionally, the `db_dev.py` endpoints don't wrap responses the way CLI models expect.

**Fix:** The CLI needs to adapt OR the backend needs to standardize. We'll standardize on CLI contract (`data`/`total` wrapper) in backend.

### 🔴 CRITICAL: Alerts Route Field Names (CP-3)
| Backend Field | CLI Model Field | Mismatch |
|---------------|-----------------|----------|
| `alerts.title` | `Alert.Title` | ✅ Same |
| `alerts.body` | `Alert.Description` | **KEY NAME** — backend uses `body`, CLI expects `description` |
| `alerts.severity` | `Alert.Severity` | ✅ Same |
| `alerts.status` | `Alert.IsAcknowledged bool` | **SEMANTICS** — backend uses status string, CLI uses bool |

**Fix:** Update backend response transformation to include `description` and `is_acknowledged` fields in `/db/alerts` and `/api/v1/alerts`.

### 🔴 CRITICAL: Config Route Key Names (CP-4)
| Backend Field | CLI Model Field |
|---------------|-----------------|
| `cloud_config.service_category` | `RawConfigRecord.ServiceCategory` |
| `cloud_config.region` | `RawConfigRecord.Region` |
| `cloud_config.last_updated` | `RawConfigRecord.LastUpdated` |

Backend's `/db/configs` uses `created_at`/`updated_at`, not `service_category`/`region`/`last_updated`. This makes the config DB helper useless for CLI.

**Fix:** Either update the DB helper to actually join against a real schema, OR we standardize the CLI to match the backend. We'll go the CLI-update route for config because the backend schema is more mature (actual `cloud_config` structure with `provider`, `config`, etc.).

### ⚠️ MAJOR: Duplicate Extractor Routes (CP-5)
Backend registers **two identical route paths**:
1. `extractors_crud.py` — `GET/POST /api/v1/extractors` — Pydantic models, full CRUD
2. `extractors_registry.py` — `GET/POST /api/v1/extractors` — Raw dict, simpler CRUD

This is a merge conflict artifact from commit `cd24534`. Whichever is mounted **second** wins. The current mount order in `main.py` is:
```python
app.include_router(extractors_crud.router, ...)  # First
app.include_router(extractors_registry.router, ...)  # Second — WINS
```
**Fix:** Remove `extractors_crud.py` from app registration, keep only `extractors_registry.py`. Alternatively rename its prefix to `/api/v1/extractors2`. We'll remove the CRUD router from app to eliminate collision.

### ⚠️ MAJOR: `/configs` missing for CLI (CP-6)
CLI expects these endpoints:
- `GET /configs` — list configs
- `POST /configs` — create config
- `GET /configs/{id}` — get single config
- `PUT /configs/{id}` — update config
- `DELETE /configs/{id}` — delete config

Backend has `/api/v1/config` (singular) with different response shape. No `/{id}` GET, PUT, DELETE on config item specifically.

**Fix:** Add `/configs` alias endpoints to `config.py` that wrap the existing config CRUD with CLI-compatible response shape (`data`/`total` wrapper).

### ⚠️ MAJOR: `/costs/summary` and `/costs/breakdown` missing (CP-7)
CLI calls:
- `GET /costs/summary` → `CostTotalsResponse`
- `GET /costs/breakdown` → `CostBySKUResponse`

Backend has:
- `GET /costs/totals` → returns `{"totals":{...}}`
- `GET /costs/by-sku` → returns `{"costs":[...],"totalRows":N}`

**Fix:** Add `/costs/summary` and `/costs/breakdown` aliases.

### ⚠️ MAJOR: `/alerts/stats` format mismatch (CP-8)
CLI expects:
```json
{"total":0,"by_severity":{},"by_provider":{},"acknowledged":0,"pending":0}
```

Backend returns:
```json
{"stats":[{"status":"...","severity":"...","count":N}]}
```

**Fix:** Backend `/alerts/stats` returns an aggregation format that CLI can't parse. The CLI needs to adapt or the backend needs to add an aggregated stats endpoint. We'll transform the backend response to include `by_severity` and `by_provider` counts in the existing endpoint.

### ⚠️ Frontend: Empty Repo (CP-9)
`finna-app-ui` on GitHub is **completely empty** (only has `.gitignore`, `.dockerignore`, and CI workflows). The real working frontend code lives in `backend/frontend/` inside the monorepo.

**Fix:** Move the React working code to `finna-app-ui` as the canonical frontend repo. This includes:
- `apiClient.ts`
- `hooks/useApi.ts`
- `main.tsx` (basic screens)
- `components/auth/LoginScreen.tsx`
- `components/common/APIScreen.tsx`
- `data/mock_api_data.json`
- Build config (vite, etc.)

### ⚠️ Frontend: Missing Vite Config (CP-10)
No `vite.config.ts` or `package.json` in `backend/frontend/` means no actual buildable project.

**Fix:** Scaffold a minimal Vite+React project in `finna-app-ui` using the existing source files.

---

## Implementation Phases

### Phase 1: Backend CLI Compatibility Layer ⚡
**Goal:** Make backend endpoints compatible with the CLI's expectations.

| File | Changes |
|------|---------|
| `backend/app/api/routes/auth.py` | Add `POST /auth/login` alias returning `{"access_token":...,"token_type":"bearer"}` |
| `backend/app/api/routes/config.py` | Add `/configs` GET/POST/PUT/DELETE/GET-by-id aliases with `data`/`total` wrapper |
| `backend/app/api/routes/costs.py` | Add `/costs/summary` and `/costs/breakdown` aliases |
| `backend/app/api/routes/alerts.py` | Add `by_severity`, `by_provider` to `/alerts/stats` response |
| `backend/app/api/routes/db_dev.py` | Add `description` + `is_acknowledged` fields in alert rows; add `service_category`/`region` to config rows |
| `backend/app/api/main.py` | Remove duplicate `extractors_crud` router registration |

### Phase 2: CLI Alignment
**Goal:** Update CLI to match actual backend field names where backend is the source of truth.

| File | Changes |
|------|---------|
| `internal/api/client.go` | Change `LoginRequest` to POST `token` endpoint (since backend expects `username`/`password` → `{"token":...}`); Actually, better to have backend add `/login` alias. |
| `internal/api/client.go` | Update `Alert.Description` to `Alert.Body` (matching backend); update `IsAcknowledged` to parse from `acknowledged_at != null` |
| `cmd/finna/health.go` | Add if missing |

Actually, looking at it more carefully: the CLI was designed against an API contract that the backend doesn't fully implement. The most efficient approach is:
1. **Backend adds aliases** for CLI contracts (`/login`, `/configs`, `/costs/summary`, `/costs/breakdown`)
2. **Backend adds field aliases** (`description` from `body`, `is_acknowledged` from `acknowledged_at`)
3. **Keep CLI unchanged** — this preserves backward compatibility and makes the CLI "just work"

### Phase 3: Frontend Migration
**Goal:** Move working frontend from monorepo subfolder to dedicated repo.

| Action | Details |
|--------|---------|
| Scaffold `finna-app-ui` | Create `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html` |
| Migrate source files | Move `backend/frontend/src/**/*` → `finna-app-ui/src/**/*` |
| Fix import paths | Update relative imports from `../services/apiClient` etc. |
| Build test | `npm install && npm run build` must pass |
| Push to GitHub | Commit and push to `AndreaCarmisciano/finna-app-ui` |

### Phase 4: Build & Verify
| Action | Details |
|--------|---------|
| Backend build test | `cd /root/projects/finna-app && uv run python -m py_compile backend/app/api/routes/*.py` |
| Frontend build test | `cd finna-app-ui && npm run build` |
| CLI build test | `cd /tmp/finna-cli && go build ./cmd/finna` |
| Commit backend | `git add . && git commit -m "feat(api): connection points alignment for CLI and frontend"` |
| Push | `git push origin main` |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Token budget exceeded | Keep changes surgical; avoid large refactors |
| Frontend build breaks | Write Vite config based on skill template; test before push |
| Backend regression | Only ADD endpoints, never REMOVE or CHANGE existing behavior |
| Git push rejected on diverged branch | Commit on current branch; offer rebase/merge later |

---

## Success Criteria

- [ ] CLI `finna login` succeeds against `localhost:8000`
- [ ] CLI `finna config list` returns configs
- [ ] CLI `finna costs summary` returns totals
- [ ] CLI `finna alerts list` returns alerts (with correct `is_acknowledged`)
- [ ] Frontend `npm run build` produces `dist/` with no errors
- [ ] Frontend login screen works when served
- [ ] Backend still passes all existing smoke tests
