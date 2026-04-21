# Frontend Integration TODO Handoff

## Status

**Mostly Complete** — All screens wired to API, mock server works, production build succeeds. Browser rendering issue with production build (Vite module loading). Dev server works for local development.

## What's Been Done

### ✅ Phase 1: Authentication Flow (COMPLETE)
- ✅ `src/main.tsx` — AuthGuard + LoginScreen with JWT auth
- ✅ `src/services/apiClient.ts` — APIClient with login/logout/token
- ✅ Login form with error handling and credential validation
- ✅ Fixed AuthGuard to check localStorage token first (no more "Failed to fetch")

### ✅ Phase 2: API Client & Data Hooks (COMPLETE)
- ✅ `src/hooks/useApi.ts` — All hooks wired:
  - `useCosts`, `useCostTotals`, `useDailyCosts`, `useCostsBySku`
  - `useConfigs`, `useCreateConfig`, `useDeleteConfig`
  - `useAlerts`, `useActiveAlerts`
  - `useExtractorRuns`, `useTriggerExtractor`
  - `useDashboardSummary`, `useAuth`
  - `transformDailyData`, `transformConfigsToConnections` helpers

### ✅ Phase 3: Dashboard Screen (COMPLETE)
- ✅ `DashboardScreen.tsx` — Fully rewritten, connected to real API
- ✅ `ConnectionsScreen.tsx` — `useConfigs` + CRUD operations
- ✅ `ExplorerScreen.tsx` — `useCosts` with filtering/sorting
- ✅ `AlertsScreen.tsx` — `useAlerts` with tab filtering
- ✅ `RunsScreen.tsx` — `useExtractorRuns` with status filter

### ✅ Phase 4: Build System (COMPLETE)
- ✅ `package.json` — React 18 + Vite 6 + react-router-dom
- ✅ `vite.config.ts` — Vite + React + proxy config
- ✅ `tsconfig.json` — TypeScript config
- ✅ `index.html` — Entry HTML with fonts
- ✅ `src/main.tsx` — App entry point with auth routing
- ✅ `dev-server.ts` — Combined dev server (static files + mock API)

### ✅ Phase 5: Local Test Environment (COMPLETE)
- ✅ `backend/frontend/mock-server.ts` — Standalone Bun mock API server
- ✅ `dev-server.ts` — Combined server (serves dist/ + mock API on port 3000)
- ✅ Build succeeds: 74 modules, 269KB JS, 36KB CSS

### ✅ Phase 6: Browser Testing (PARTIAL)
- ✅ Login screen renders correctly in browser
- ✅ Mock API server responds correctly (health check, auth, costs, alerts)
- ✅ Login form submits and calls API successfully
- ⚠️ Production build doesn't render in browser (investigating Vite module loading issue)

## Browser Test Results

### Successful Tests
1. ✅ Login screen renders with correct form UI
2. ✅ Credentials: admin/admin accepted by mock API
3. ✅ Health check returns 200 from browser
4. ✅ Auth token generated and returned correctly
5. ✅ All API endpoints tested via curl (costs, alerts, configs, runs)
6. ✅ Build succeeds with no errors

### Known Issue
- Production build (`dist/`) doesn't render React content in browser
- Root element exists but stays empty
- No JavaScript errors in console
- Script loads and executes (269KB transfer)
- Issue appears to be Vite module resolution in headless Chrome
- **Workaround**: Use Vite dev server for local development

## Testing

### Option 1: Mock Data (Frontend Dev)
```bash
# Terminal 1 — Mock API server
bun backend/frontend/mock-server.ts

# Terminal 2 — Frontend dev server
npx vite --host 0.0.0.0
```
→ http://localhost:3000

### Option 2: Combined Dev Server (Static + API)
```bash
bun dev-server.ts
```
→ http://localhost:3000 (serves dist/ + mock API)

### Option 3: Full Stack (Real Backend)
```bash
# Terminal 1 — Real API backend
cd backend && python -m app.api.main

# Terminal 2 — Frontend dev server
npx vite --host 0.0.0.0
```
→ http://localhost:3000 (proxies /api to localhost:8000)

### Build & Preview
```bash
npm run build    # Production build to dist/
npm run preview  # Preview production build
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

## Screens Implemented

- ✅ **Dashboard** — Overview with charts, stats, alerts, recent runs
- ✅ **Cost Explorer** — Filterable/sortable cost records table
- ✅ **Connections** — Cloud provider connections (cards/table)
- ✅ **Alerts** — Firing/resolved alert rules
- ✅ **Run Log** — Extractor run history
- ✅ **Projects** — Project budget governance
- ✅ **Budgets** — Monthly caps per scope
- ✅ **Settings** — Workspace configuration

## Key Files

| File | Purpose |
|------|---------|
| `src/services/apiClient.ts` | HTTP client, auth, error handling |
| `src/hooks/useApi.ts` | Data hooks with loading/error states |
| `src/main.tsx` | Auth guard + login flow + router |
| `src/components/screens/DashboardScreen.tsx` | Main dashboard wired to API |
| `dev-server.ts` | Combined dev server (static + mock API) |
| `backend/frontend/mock-server.ts` | Standalone mock API server |
| `vite.config.ts` | Vite + React + proxy config |

## Credentials

- Admin: `admin` / `admin`
- User: `user` / `password`
