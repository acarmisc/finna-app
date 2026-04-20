# Frontend Integration TODO Handoff

## Status

**Partially Complete** - Authentication and API client foundation is done. DashboardScreen has a bug (duplicate function) and screens still need to be connected to real API.

## What's Been Done

### ✅ Phase 1: Authentication Flow (COMPLETE)
- Created LoginScreen in frontend/src/screens/LoginScreen.tsx
- Created AuthGuard in frontend/src/components/AuthGuard.tsx
- Extended API client with login/logout/token functions in frontend/src/api/client.ts
- Updated main.tsx to use AuthGuard + LoginScreen flow

### ✅ Phase 2: API Client & Data Hooks (COMPLETE)
- Extended frontend/src/api/client.ts with all backend endpoints:
  - Config: getConfigs, createConfig, deleteConfig, getConfig, updateConfig
  - Extractor: getExtractorRuns, triggerExtractor, getRunStatus
  - Costs: getCosts, getCostTotals, getDailyCosts, getCostsBySku
  - Alerts: getAlerts, getActiveAlerts, getAlertStats
  - Health: getHealth
- Created frontend/src/hooks/useData.ts with hooks:
  - useConfigs, useCreateConfig, useDeleteConfig
  - useCosts, useCostTotals, useDailyCosts, useCostsBySku
  - useAlerts, useActiveAlerts
  - useExtractorRuns, useTriggerExtractor
  - useDashboardSummary
  - Helper transforms: transformDailyData, transformConfigsToConnections

### ❌ Phase 3: Dashboard Screen (PARTIAL - BUG)
- Attempted to update DashboardScreen.tsx but created a bug
- **CRITICAL**: DashboardScreen.tsx has duplicate function declaration
- Need to rewrite entire file cleanly

## Git Status

Repo was reset due to merge conflicts. Need to re-apply changes.

## TODO List for Next Agent

1. **CRITICAL**: Fix DashboardScreen.tsx - rewrite without duplicate function
2. Connect DashboardScreen to real data using hooks from useData.ts
3. Update ConnectionsScreen.tsx:
   - Import useConfigs hook
   - Replace mock connections with API data
   - Wire up create/delete connection forms
4. Update ExplorerScreen.tsx:
   - Import useCosts hook
   - Replace mock costs with API data
   - Wire up filters
5. Update AlertsScreen.tsx:
   - Import useAlerts hook
   - Replace mock alerts with API data
6. Update RunsScreen.tsx:
   - Import useExtractorRuns hook
   - Replace mock runs with API data
7. Test build: cd frontend && npm run build
8. Run backend: cd backend && python -m app.api.main
9. Test login and data flow

## Key Files Created (Need to reapply)

```
frontend/src/screens/LoginScreen.tsx
frontend/src/components/AuthGuard.tsx
frontend/src/hooks/useData.ts
```

## Key Files Modified (Need to reapply)

```
frontend/src/api/client.ts - Add all API functions
frontend/src/main.tsx - Add routing/auth
frontend/src/components/screens/DashboardScreen.tsx - Connect to real data
```

## Reference

See FRONTEND_INTEGRATION_PLAN.md for full implementation details (in git history or recreate).

## Backend API Base URL

- `/api/v1` - All endpoints
- `/api/v1/auth/token` - Login (POST username/password)
- `/healthz` - Health check (no auth)

## Testing

Default credentials: admin / admin

## Commands

```bash
# Backend
cd backend
python -m app.api.main

# Frontend
cd frontend
npm install
npm run dev

# Build
cd frontend
npm run build
```
