# Finna Console - Implementation Plan

> Production rebuild specification. Mapping from WIP mockup to React + TypeScript implementation.

## Summary of Current State

**Project Status**: ✅ Existing implementation with substantial foundation

** Tech Stack **(All present):
- ✅ React 18 + TypeScript + Vite
- ✅ React Router DOM v6 (hash-based)
- ✅ TanStack Query v5 (installed, basic setup needed)
- ✅ Zustand for state management
- ✅ Axios for API calls
- ✅ Tailwind CSS v4 + shadcn/ui (new-york-v4)
- ✅ Recharts, Lucide icons, Zod, React Hook Form (installed)
- ✅ Font sources: Inter, JetBrains Mono (installed)

**Directory Structure** (Partial):
```
src/
├── api/
│   ├── client.ts (basic setup, needs refinement)
│   └── schemas.ts
├── components/
│   ├── ui/ (shadcn components)
│   ├── shared/ (15+ components, mostly complete)
│   └── layout/ (AppShell, Sidebar, TopBar - functional)
├── pages/ (8 pages, various completion levels)
├── store/ (auth, ui zustand stores)
├── types/ (minimal TypeScript types)
├── config/ (env config)
└── styles.css (995 lines, comprehensive pixel-art styling)
```

**Completed Components**:
- ✅ Base CSS with design system tokens (dark/light themes)
- ✅ AppShell layout with hash-based routing
- ✅ Sidebar navigation with collapsing sections
- ✅ TopBar with date range picker (custom implementation, not using shadcn)
- ✅ 15+ shared components (StatCard, Button, ProviderBadge, StatusBadge, LineChart, etc.)
- ✅ LoginPage (basic auth form)
- ✅ DashboardPage (KPI grid, charts, recent runs)
- ✅ ProjectsListPage (searchable table)
- ✅ ProjectsDetailPage (project details)
- ✅ CostsPage (3-tab explorer)
- ✅ ConfigsListPage (config cards with test/delete)
- ✅ ConfigCreatePage (3-step wizard)
- ✅ AlertsPage (alert listing)
- ✅ SettingsPage (placeholder)
- ✅ RunHistoryPage, DataSourcesPage (custom pages)

**Key Differences from HANDOFF.md**:
1. **Routing**: Currently uses hash-based routing with custom `useHashRoute()` hook in `AppShell.tsx`, but `main.tsx` wraps with `<BrowserRouter>` - inconsistent
2. **API Client**: Missing proper token.refresh logic (401 interceptor clears token but doesn't refresh)
3. **Date Range**: TopBar has custom date picker (custom implementation), missing URL search param sync
4. **TanStack Query**: Lacking proper query key structure, no default options, missing react-query-devtools
5. **Theme Toggle**: Exists in TopBar, but not synced to localStorage or HTML `data-theme` attribute
6. **Protected Routes**: Missing `ProtectedRoute` wrapper component
7. **SSO**: Only email/password login exists
8. **Extractors Page**: Custom page exists but not in HANDOFF routes
9. **Missing**: `/auth/callback`, `/configs/:id` edit hydration, notifications dropdown

---

## Missing Components and Pages

### High Priority - Core Functionality

| Component | Status | Notes |
|-----------|--------|-------|
| `ProtectedRoute.tsx` | Partial | File exists but not exported/used consistently |
| `AuthCallback.tsx` | Missing | OAuth callback page - handles code exchange |
| `/configs/:id` Edit | Partial | Route exists, but form starts blank, no hydration |
| `TweaksPanel.tsx` | Missing | Host protocol for theme + debug toggles |
| API Layer | Basic | Missing dedicated API files (`api/auth.ts`, `api/totals.ts`, etc.) |
| Context Providers | Missing | Theme, DateRange, Toast context needed |
| URL Sync | Missing | Date range not persisted to URL params |

### Medium Priority - Page Features

| Page | Missing Features |
|------|------------------|
| DashboardPage | KPI drag-reorder (client-side only), hide/restore tiles, customize mode |
| CostsPage | Export buttons (CSV/Excel), tab state sync to URL, filters persist |
| ConfigCreatePage | Edit mode hydration, LLM provider, AWS provider, validation (Zod schema) |
| AlertsPage | Ack/silence/dismiss actions, optimisitic updates, filter state sync |
| SettingsPage | API keys section, notifications, tags management, profile upload |
| ExtractorsPage | Run trigger (optimistic), polling, log viewer, expandable rows |

### Low Priority - nice-to-haves

| Feature | Priority | Notes |
|---------|----------|-------|
| SSO providers (Google, Microsoft, Okta, GitHub, SAML) | Low | Requires backend OAuth setup |
| Mobile responsive sidebar (drawer) | Low | Login degrades, rest is desktop-only |
| WebSocket for live updates | Low | Currently polling only |
| Saved date ranges | Low | Preferences API |
| Notifications dropdown | Low | Bell routes to /alerts |

---

## Implementation Phases

### **Phase 1: Infrastructure & Core Setup** (High Priority, 3-4 days)

**Goal**: Establish proper foundation for the application

#### Tasks:

1. **Fixed Router Architecture**
   - [ ] Remove `HashRouter` wrapper from `main.tsx`
   - [ ] Use only `<BrowserRouter>` (not hash-based)
   - [ ] Add `ProtectedRoute` component wrapping authenticated routes
   - [ ] Ensure `/configs/:id` route uses same `ConfigCreatePage` component
   - [ ] Add `/auth/callback` route for OAuth flows
   - [ ] Move hash routing logic to navigation layer, not layout

2. **Enhanced API Client**
   - [ ] Create `src/api/client.ts` with proper axios instance
   - [ ] Add 401 interceptor with automatic token refresh
   - [ ] Add request idempotency key generation
   - [ ] Create dedicated API files:
     - [ ] `src/api/auth.ts` (SSO, login, refresh)
     - [ ] `src/api/totals.ts` (totals, costs summary)
     - [ ] `src/api/costs.ts` (cost exploration)
     - [ ] `src/api/projects.ts`
     - [ ] `src/api/configs.ts`
     - [ ] `src/api/runs.ts`
     - [ ] `src/api/alerts.ts`
     - [ ] `src/api/settings.ts`
   - [ ] Add TypeScript interfaces for all API types

3. **Enhanced State Management**
   - [ ] Create `useTheme()` hook (sync `data-theme` + localStorage)
   - [ ] Create `useDateRange()` hook (sync URL params: `?window=30d&start=...&end=...`)
   - [ ] Add `useToast()` context provider
   - [ ] Enhance `useAuthStore` with refresh token logic
   - [ ] Add `usePreferences` hook (KPI order/hidden, default window)
   - [ ] Add `useSidebar` hook (collapse state + localStorage)

4. **Context Providers**
   - [ ] Create `ThemeContext` with `ThemeToggle` component
   - [ ] Create `DateRangeContext` with `RangeProvider`
   - [ ] Create `ToastContext` with `ToastProvider`
   - [ ] Update `main.tsx` to wrap with contexts
   - [ ] Update `AppShell` to consume context instead of local state

5. **Enhanced Shadcn Components**
   - [ ] Create `src/components/ui/ bracket-button.tsx` (BRACKETED variant)
   - [ ] Create `src/components/ui/line-chart.tsx` (Recharts wrapper)
   - [ ] Create `src/components/ui/stacked-area-chart.tsx` (Recharts)
   - [ ] Create `src/components/ui/status-badge.tsx` (NES style)
   - [ ] Create `src/components/ui/provider-badge.tsx` (color-coded)
   - [ ] Create `src/components/ui/progress-bar.tsx` (pixel-stitched)
   - [ ] Create `src/components/ui/cost-delta.tsx` (up = red, down = green)

6. **Environment Configuration**
   - [ ] Update `.env.example` with all required variables:
     ```env
      VITE_API_BASE_URL=https://<your-domain>/api/v1
     VITE_APP_NAME="FinOps Console"
     VITE_APP_VERSION=0.1.0
     VITE_FEATURE_SSO=true
     VITE_FEATURE_WEBSOCKETS=false
     ```
   - [ ] Create `src/config/env.ts` with typed configuration
   - [ ] Add feature flags for opt-in features

**Deliverables**:
- Clean router using `<BrowserRouter>` only
- Working authentication with token refresh
- Centralized theme/date context
- Type-safe API client structure

---

### **Phase 2: Authentication Flow** (High Priority, 2-3 days)

**Goal**: Complete SSO + email/password login flow

#### Tasks:

1. **SSO Provider Buttons**
   - [ ] Add 5 SSO buttons in `LoginPage.tsx`
   - [ ] Implement handler for each provider:
     ```typescript
     const handleSSO = async (provider: string) => {
       const response = await api.post(`/auth/sso/${provider}/init`, { 
         return_to: window.location.hash || '#/dashboard' 
       })
       window.location.href = response.data.authorization_url
     }
     ```
   - [ ] Add SSO providers config (`src/config/sso.ts`)
   - [ ] Add conditional SSO display based on `VITE_FEATURE_SSO`

2. **OAuth Callback Page**
   - [ ] Create `src/components/auth/AuthCallback.tsx`
   - [ ] Parse URL params: `?code=...&state=...&provider=...`
   - [ ] Submit code to backend: `POST /auth/sso/callback`
   - [ ] Store tokens on success
   - [ ] Redirect to `return_to` or `/dashboard`
   - [ ] Handle errors gracefully (toast + error state)

3. **Token Refresh Flow**
   - [ ] Update `useAuthStore` to store `refreshToken` separately
   - [ ] Implement `refreshAccessToken()` in auth store
   - [ ] Update `api/client.ts` 401 interceptor:
     ```typescript
     if (error.response?.status === 401 && !config._retry) {
       config._retry = true
       const newToken = await authStore.refreshAccessToken()
       config.headers.Authorization = `Bearer ${newToken}`
       return api(config)
     }
     ```

4. **Logout Flow**
   - [ ] Implement `POST /auth/revoke` with `refresh_token`
   - [ ] Clear all tokens from localStorage
   - [ ] Clear TanStack Query cache
   - [ ] Navigate to `/login`

5. **Google Cloud Shell Integration**
   - [ ] If running in Cloud Shell, auto-auth using gcloud ADC
   - [ ] Add environment variable: `VITE_USEADC=true`

**Deliverables**:
- Complete login flow (email + 5 SSO providers)
- OAuth callback page
- Automatic token refresh
- Clean logout

---

### **Phase 3: Dashboard & Page Enhancements** (High Priority, 4-5 days)

**Goal**: Complete dashboard KPI features, enhance data pages

#### Tasks:

1. **DashboardPage Enhancements**
   - [ ] Implement KPI order persistence (localStorage + preferences API)
   - [ ] Add drag-and-drop reordering (HTML5 Drag API)
   - [ ] Add KPI hide/restore functionality
   - [ ] Add "Customize Strip" when in edit mode
   - [ ] Add refresh button with manual refetch
   - [ ] Add "Last refresh" timestamp display
   - [ ] Add `customRange` support via date context

2. **KPI Grid Reordering**
   ```typescript
   // src/features/dashboard/KpiGrid.tsx
   const [kpiOrder, setKpiOrder] = useState<KpiId[]>(() => {
     const saved = localStorage.getItem('finna_kpi_order')
     return saved ? JSON.parse(saved) : DEFAULT_KPIS
   })
   const handleDragStart = (id: KpiId) => setDraggedId(id)
   const handleDragOver = (e: React.DragEvent) => e.preventDefault()
   const handleDrop = (targetId: KpiId) => {
     const newOrder = kpiOrder.filter(id => id !== draggedId)
     newOrder.splice(targetIndex, 0, draggedId)
     setKpiOrder(newOrder)
     localStorage.setItem('finna_kpi_order', JSON.stringify(newOrder))
   }
   ```

3. **Date Range URL Sync**
   - [ ] Update `DateRangePicker` to sync with URL params
   - [ ] Read from `?window=mtd&start=2026-04-01&end=2026-04-30`
   - [ ] Write updates on preset change:
     ```typescript
     const [searchParams, setSearchParams] = useSearchParams()
     const handlePresetChange = (range: string) => {
       setSearchParams({
         window: range,
         // clear custom if switching from custom
       })
     }
     ```

4. **TanStack Query Configuration**
   - [ ] Create `src/query/queryClient.ts` with defaults
   - [ ] Add retry with exponential backoff
   - [ ] Setup stale time per endpoint
   - [ ] Add query keys:
     ```typescript
     const queryKeys = {
       auth: { me: ['auth', 'me'], refresh: ['auth', 'refresh'] },
       totals: (window: string) => ['totals', window],
       costs: (filters: any) => ['costs', 'list', filters],
       projects: (filters: any) => ['projects', 'list', filters],
       project: (slug: string) => ['project', slug],
       configs: () => ['configs', 'list'],
       config: (id: string) => ['config', id],
       runs: (filters: any) => ['runs', 'list', filters],
       run: (id: string) => ['run', id],
       alerts: (filters: any) => ['alerts', 'list', filters],
       stats: () => ['alerts', 'stats'],
     }
     ```

5. **Project Detail Page**
   - [ ] Add MTD cost / Budget cap / Forecast EOM tiles
   - [ ] Add daily stacked area chart
   - [ ] Add active alerts filtered by project
   - [ ] Add tags & metadata section
   - [ ] Add cost breakdown by SKU table
   - [ ] Add empty state when project not found

6. **AlertsPage Actions**
   - [ ] Implement Acknowledge (POST `/alerts/${id}/ack`)
   - [ ] Implement Silence (POST `/alerts/${id}/silence` with duration)
   - [ ] Implement Dismiss (POST `/alerts/${id}/dismiss`)
   - [ ] Add optimistic updates with rollback on error
   - [ ] Add silence modal with duration picker

7. **CostsPage Refinements**
   - [ ] Add CSV export (GET `/costs/export?format=csv`)
   - [ ] Add XLSX export (GET `/costs/export?format=xlsx`)
   - [ ] Persist filter state between navigations
   - [ ] Add provider toggle chips
   - [ ] Fix `CostDeltaCell` to show red for cost increases

**Deliverables**:
- Dashboard with draggable KPI tiles
- Date range synced to URL
- Alert actions (ack/silence/dismiss)
- Cost export functionality

---

### **Phase 4: Config & Run Management** (Medium Priority, 3-4 days)

**Goal**: Complete configuration and extractor workflows

#### Tasks:

1. **ConfigCreatePage Edit Mode**
   - [ ] Detect when `id` param present (edit mode)
   - [ ] Fetch config: `useQuery(['config', id], () => api.configs.get(id))`
   - [ ] Seed form state with fetched config
   - [ ] Update submit to use PATCH instead of POST
   - [ ] Add "Save" vs "Create" button logic

2. **Add Missing Providers**
   - [ ] Implement LLM provider in Config Wizard
     ```typescript
     // Step 1: LLM provider card
     {id:'llm', title:'LLM / API', desc:'Anthropic, OpenAI, Azure OpenAI', color:'var(--llm)'}
     // Step 2: LLM credentials form
     api_provider (select): anthropic, openai, azure-openai
     api_key (password input)
     base_url (optional, text input)
     ```
   - [ ] Implement AWS provider in Config Wizard (similar to Azure)

3. **Config Test & Validation**
   - [ ] Add Zod validation schema for each provider:
     ```typescript
     // src/schemas/config.ts
     export const azureSchema = z.object({
       name: z.string().min(3),
       provider: z.literal('azure'),
       credential_type: z.enum(['service_principal','managed_identity']),
       tenant_id: z.string().uuid(),
       subscription_id: z.string().uuid(),
       client_id: z.string().uuid().optional(),
       client_secret: z.string().min(8).optional(),
     }).refine(d => d.credential_type === 'managed_identity' || (d.client_id && d.client_secret), {
       message: 'client_id + client_secret required for service_principal',
     })
     ```
   - [ ] Add test endpoint call (`POST /config/test`)
   - [ ] Show latency on success: `{ok: true, latency_ms: 450}`
   - [ ] Show error band if test fails

4. **Config Management**
   - [ ] Implement delete config (DELETE `/config/${id}`)
   - [ ] Add confirmation dialog before delete
   - [ ] Add success toast after delete
   - [ ] Add loading state on test button

5. **ExtractorsPage / RunHistoryPage**
   - [ ] Add trigger run endpoint (`POST /runs`)
   - [ ] Implement optimistic run creation
   - [ ] Add polling logic:
     ```typescript
     useQuery(['run', runId], () => api.runs.get(runId), {
       enabled: !!runId,
       refetchInterval: (data) => {
         if (['running','started'].includes(data?.status)) return 2000
         return false
       }
     })
     ```
   - [ ] Add run history table with sorting
   - [ ] Add expandable run rows with logs
   - [ ] Add filter chips (status, provider)

6. **DataSourcesPage** (if exists)
   - [ ] Implement as source configuration page
   - [ ] Add add/edit/delete source logic
   - [ ] Add connection testing

**Deliverables**:
- Working config CRUD (create/edit/delete/test)
- LLM + AWS provider support
- Optimistic run triggering with polling

---

### **Phase 5: Settings & User Preferences** (Medium Priority, 2-3 days)

**Goal**: Complete user settings and preferences system

#### Tasks:

1. **SettingsPage Sections**
   - [ ] **Profile Section**
     - [ ] Read user from `useQuery(['auth', 'me'])`
     - [ ] Display read-only fields (email, org, role)
     - [ ] Add avatar upload (POST `/users/me/avatar`)
     - [ ] Add timezone picker (select)
     - [ ] Add locale picker (select)
   - [ ] **Organization Section**
     - [ ] Display org name, billing email
     - [ ] Show plan tier + seat usage
     - [ ] Add upgrade button (placeholder)
   - [ ] **API Keys Section**
     - [ ] List existing keys (GET `/api-keys`)
     - [ ] Add "Create Key" button
     - [ ] Create modal with name + scopes
     - [ ] Display secret one-time (toast + copy button)
     - [ ] Add revoke button
   - [ ] **Notifications Section**
     - [ ] Email toggle (switch)
     - [ ] Slack webhook input
     - [ ] Webhook URL input
     - [ ] Per-event toggles
   - [ ] **Tags Section**
     - [ ] List all tags in use
     - [ ] Add edit tag modal
     - [ ] Add merge tag functionality
     - [ ] Add delete tag with usage count

2. **Preferences Management**
   - [ ] Add `GET /users/me/preferences` endpoint
   - [ ] Add `PUT /users/me/preferences` endpoint
   - [ ] Implement KPI order/hidden sync
   - [ ] Implement default window preference
   - [ ] Add preferences loading skeleton

3. **Theme Preferences**
   - [ ] Persist theme toggle to preferences API
   - [ ] Fall back to localStorage if API fails
   - [ ] Add "System" option (auto-detect)

4. **User Menu**
   - [ ] Update topbar avatar (currently decorative)
   - [ ] Add dropdown with: Profile, Settings, Sign out
   - [ ] Add user thumbnail if available
   - [ ] Add org name in dropdown

**Deliverables**:
- Complete settings page with 5 sections
- API keys with secret display
- User preferences synced to backend

---

### **Phase 6: Polish & Optimization** (Medium Priority, 3-4 days)

**Goal**: Final polish, performance, accessibility

#### Tasks:

1. **Performance Optimization**
   - [ ] Add React.memo to heavy components (StatCard, ProviderBadge)
   - [ ] Optimize Charts with Recharts shouldComponentUpdate
   - [ ] Add React.Query caching with staleTime
   - [ ] Implement pagination on large tables
   - [ ] Add virtualization for tables with >100 rows (react-virtual)

2. **Accessibility (WCAG AA)**
   - [ ] Add proper ARIA labels to buttons
   - [ ] Ensure keyboard navigation (Tab/Enter/Space)
   - [ ] Add focus outlines on interactive elements
   - [ ] Add contrast ratio checks (ensure 4.5:1 min)
   - [ ] Add screen reader labels to icons

3. **Error Boundaries**
   - [ ] Add React.ErrorBoundary wrapper
   - [ ] Add fallback UI for API errors
   - [ ] Add retry button on error states
   - [ ] Log errors to Sentry/Datadog

4. **Toast System**
   - [ ] Integrate `sonner` or `react-hot-toast`
   - [ ] Add error toast on API failures
   - [ ] Add success toast on mutations
   - [ ] Add loading toast for operations
   - [ ] Add toast auto-dismiss with duration

5. **Skeleton Loading States**
   - [ ] Add skeleton for KPI tiles during load
   - [ ] Add skeleton for table rows
   - [ ] Add skeleton for charts
   - [ ] Add skeleton for profile/organization sections

6. **Print Stylesheet**
   - [ ] Add `@media print` styles
   - [ ] Hide sidebar and topbar
   - [ ] Show only cost explorer data
   - [ ] Add "Exported on: [date]" footer
   - [ ] Ensure print-friendly color scheme

7. **Code Quality**
   - [ ] Run `npx tsc --noEmit` (CI step) - fix all errors
   - [ ] Format with Prettier (add config if missing)
   - [ ] Add ESLint rules for React hooks
   - [ ] Add husky pre-commit hook
   - [ ] Run build in CI and fix console warnings

**Deliverables**:
- Fast, accessible production-ready UI
- Comprehensive error boundaries
- Print-friendly styles

---

### **Phase 7: Testing & Validation** (High Priority, 2-3 days)

**Goal**: Verify all functionality before ship

#### Tasks:

1. **Acceptance Checklist** (from HANDOFF.md §11.6)
   - [ ] Login → SSO redirect → callback → dashboard land works for all 5 providers
   - [ ] Email/password login validates, shows inline errors, clears password on failure
   - [ ] 401 on any API call triggers refresh → retry; if refresh fails, redirect to `/login?expired=1`
   - [ ] Topbar date range writes to URL search params; deep-link `/dashboard?window=30d` works
   - [ ] Custom date range from picker writes `?start=…&end=…`
   - [ ] Dashboard KPI drag-reorder persists to `/users/me/preferences`
   - [ ] Dashboard hide/restore tile persists same
   - [ ] Theme toggle writes to localStorage AND `data-theme`; survives reload
   - [ ] Sidebar collapse persists to localStorage
   - [ ] Cloud config wizard validates per-provider, enables `[ TEST ]` only when valid, surfaces test latency
   - [ ] Alert ack/silence/dismiss are optimistic with rollback on error
   - [ ] Empty states show on `data: []` for all lists
   - [ ] Loading states show skeletons matching final layout (not spinners)
   - [ ] Error states show retry button + API problem `detail`
   - [ ] All buttons have `disabled` while mutation is pending
   - [ ] All forms use `react-hook-form` + Zod, with field-level errors
   - [ ] Lucide icons via `lucide-react` (not global `data-lucide`)
   - [ ] Light theme passes WCAG AA contrast (body text, badges)
   - [ ] Print stylesheet hides sidebar/topbar (cost reports)
   - [ ] No console warnings or errors on any route

2. **Integration Tests**
   - [ ] Setup Vitest + React Testing Library (if not present)
   - [ ] Test auth flow (login, logout, refresh)
   - [ ] Test dashboard render with mock data
   - [ ] Test date range picker interaction
   - [ ] Test config create wizard flow
   - [ ] Test alert actions (mock API responses)

3. **E2E Tests (Optional for v1, Plan for v2)**
   - [ ] Add Cypress or Playwright
   - [ ] Test critical user journeys:
     - View dashboard, filter date range
     - Navigate to alerts, acknowledge one
     - Create config, test connection
     - Trigger run, verify polling

4. **TypeScript Coverage**
   - [ ] Fix all TypeScript errors (`npx tsc --noEmit`)
   - [ ] Add strict mode (`"strict": true` in tsconfig.json)
   - [ ] Add explicit types for API responses
   - [ ] Add Zod schema types for form validation

**Deliverables**:
- All acceptance criteria met
- Test coverage for critical paths
- Zero TypeScript errors

---

## Priority-Ordered Task List

### Must Have (v1.0 - Ship Blocker)

1. **Infrastructure & Router Fix** (Phase 1)
   - [ ] Unified router (no hash-based hybrid)
   - [ ] ProtectedRoute working
   - [ ] `/auth/callback` route
   - [ ] API client with 401 refresh logic

2. **Authentication** (Phase 2)
   - [ ] Token refresh flow (401 interceptor)
   - [ ] Email/password login validation
   - [ ] OAuth callback page
   - [ ] Logout with token revocation

3. **Dashboard Core** (Phase 3)
   - [ ] KPI order persistence (localStorage)
   - [ ] Date range URL sync
   - [ ] TanStack Query config
   - [ ] Alert actions (ack/silence/dismiss)

4. **API Integration** (Phase 1, Cross-cutting)
   - [ ] Complete API client structure
   - [ ] TypeScript interfaces for all endpoints
   - [ ] Error handling consistency
   - [ ] Idempotency key support

### Should Have (v1.1 - Nice to have)

1. **Config Management** (Phase 4)
   - [ ] Edit mode for configs
   - [ ] LLM/WSS provider support
   - [ ] Validation schemas
   - [ ] Run polling implementation

2. **Settings Page** (Phase 5)
   - [ ] API keys section
   - [ ] Notifications
   - [ ] User preferences sync

3. **Polish** (Phase 6)
   - [ ] Accessibility fixes
   - [ ] Print styles
   - [ ] Error boundaries
   - [ ] Skeleton loading states

### Could Have (v2.0 - Stretch)

1. **SSO Providers** (Phase 2)
   - [ ] Google, Microsoft, Okta, GitHub, SAML
   - [ ] Required backend OAuth setup

2. **Mobile Responsive** (Phase 6)
   - [ ] Sidebar drawer for <900px
   - [ ] Touch-friendly interactions

3. **Testing** (Phase 7)
   - [ ] Unit tests (Vitest)
   - [ ] E2E tests (Cypress/Playwright)

4. **Advanced Features** (Phase 4)
   - [ ] WebSocket for live updates
   - [ ] Saved date ranges
   - [ ] Notification dropdown

---

## Risks & Blockers

### High Risk

1. **Hybrid Routing (Hash + BrowserRouter)**
   - **Issue**: Current `main.tsx` uses both `HashRouter` and `BrowserRouter` - likely causing navigation bugs
   - **Impact**: Links not working, state not syncing
   - **Mitigation**: [Phase 1, Task 1] - Remove hash router, use only BrowserRouter with query param state

2. **401 Token Refresh Not Implemented**
   - **Issue**: API client clears token on 401 but doesn't attempt refresh
   - **Impact**: Users logged out abruptly, no automatic recovery
   - **Mitigation**: [Phase 1, Task 2] - Add refresh interceptor logic

3. **Missing API Endpoints**
   - **Issue**: Many HANDOFF API routes not implemented in client
   - **Impact**: Dashboard counts, cost exports, config test, etc. will fail
   - **Mitigation**: [Phase 1, Task 2] - Create `src/api/*` files for each resource

### Medium Risk

1. **Date Range UX Inconsistency**
   - **Issue**: TopBar has custom date picker, but not synced to URL or context
   - **Impact**: Deep links don't work, navigation loses state
   - **Mitigation**: [Phase 3, Task 2] - Create `useDateRange()` hook with URL sync

2. **KPI State Management**
   - **Issue**: Handoff specifies localStorage → preferences API, but current code only uses localStorage
   - **Impact**: KPI reordering not synced across devices/sessions
   - **Mitigation**: [Phase 3, Task 1] - Add preferences API sync

3. **Form Validation**
   - **Issue**: Config wizard has basic validation, missing Zod schemas
   - **Impact**: Invalid data sent to API, poor user feedback
   - **Mitigation**: [Phase 4, Task 2] - Add Zod schemas per provider

### Low Risk (But Notable)

1. **SSO Not Configured**
   - **Issue**: Login only has email/password, SSO buttons shown but not functional
   - **Impact**: Organizations requiring SSO cannot login
   - **Mitigation**: [Phase 2] - Backend must implement OAuth endpoints first

2. **Extractors Polling**
   - **Issue**: Run history exists but no polling logic
   - **Impact**: Users don't see run status updates
   - **Mitigation**: [Phase 4, Task 5] - Add `refetchInterval` logic

3. **Print Styles Missing**
   - **Issue**: No print-specific CSS
   - **Impact**: Sidebar/topbar prints,浪费 paper, poor readibility
   - **Mitigation**: [Phase 6, Task 4] - Add `@media print` block

---

## Recommended Next Steps

1. **Immediate (This Week)**
   - [ ] Create implementation plan review with team
   - [ ] Assign Phase 1 tasks (Infrastructure) to developer
   - [ ] Set up milestone tracker in GitHub Projects
   - [ ] Create PR template with acceptance checklist
   - [ ] Add CI step: `npm run lint` and `npm run typecheck`

2. **Week 2-3**
   - [ ] Complete Phase 1 (Infrastructure)
   - [ ] Complete Phase 2 (Authentication)
   - [ ] Update Handbook/manual with new auth flows
   - [ ] Deploy to staging for SSO testing

3. **Week 4-5**
   - [ ] Complete Phase 3 (Dashboard & Pages)
   - [ ] Fix all TypeScript errors (`npx tsc --noEmit 0 errors`)
   - [ ] Add E2E tests for critical paths
   - [ ] Performance audit (Lighthouse 90+ score)

4. **Week 6-7**
   - [ ] Complete Phase 4-5 (Configs & Settings)
   - [ ] Full acceptance testing
   - [ ] Accessibility audit (axe or WAVE)
   - [ ] Documentation update

5. **Week 8 (Ship)**
   - [ ] Final smoke test on staging
   - [ ] Zero-error production build
   - [ ] Deploy to production with monitoring
   - [ ] Post-ship review & retro

---

## Success Metrics

### Technical
- ✅ Zero TypeScript errors (`npx tsc --noEmit`)
- ✅ Lighthouse score ≥90 (performance, accessibility, best practices)
- ✅ Zero console errors or warnings on any route
- ✅ All API calls return proper error payloads
- ✅ All forms use `react-hook-form` + Zod (max 200 lines per form)

### User Experience
- ✅ Dashboard loads in <1.5s (P95)
- ✅ Navigation between pages <300ms (P95)
- ✅ Token refresh <200ms (no visible delay)
- ✅ Theme toggle instant (no flash of unstyled content)
- ✅ Error messages user-readable (not raw API detail)

### Maintainability
- ✅ All components under 300 lines (except Dashboard, >500 lines acceptable)
- ✅ 80%+ test coverage on critical paths
- ✅ No magic strings (all constants in `src/config/`)
- ✅ Single source of truth for API types (Zod schemas)

---

## Appendix: File Structure (After Cleanup)

```
src/
├── api/                              # API client layer
│   ├── client.ts                     # Axios instance + interceptors
│   ├── auth.ts                       # Login, SSO, refresh
│   ├── totals.ts                     # Summary totals
│   ├── costs.ts                      # Cost exploration
│   ├── projects.ts                   # Project CRUD
│   ├── configs.ts                    # Config CRUD + test
│   ├── runs.ts                       # Extractor runs
│   ├── alerts.ts                     # Alert management
│   ├── settings.ts                   # User settings + API keys
│   └── types.ts                      # Shared TypeScript types
│
├── components/
│   ├── ui/                           # shadcn/ui components
│   │   ├── bracket-button.tsx        # [ BRACKETED ] button variant
│   │   ├── line-chart.tsx            # Recharts LineChart
│   │   ├── stacked-area-chart.tsx    # Recharts AreaChart
│   │   ├── status-badge.tsx          # NES status badge
│   │   ├── provider-badge.tsx        # Provider color badge
│   │   ├── progress-bar.tsx          # Pixel steppers
│   │   ├── cost-delta.tsx            # Cost delta display
│   │   └── ...shadcn defaults
│   │
│   ├── shared/                       # Custom shared components
│   │   ├── stat-card.tsx
│   │   ├── button.tsx
│   │   ├── date-range-picker.tsx     # Custom picker (topbar)
│   │   ├── confirm-dialog.tsx
│   │   ├── dialog.tsx
│   │   ├── empty-state.tsx
│   │   ├── money.tsx
│   │   ├── Icon.tsx
│   │   ├── hbar-list.tsx
│   │   └── ... (existing)
│   │
│   └── layout/                       # Shell components
│       ├── AppShell.tsx              # Main layout
│       ├── Sidebar.tsx
│       ├── TopBar.tsx
│       └── ProtectedRoute.tsx
│
├── features/                         # Feature modules (new)
│   ├── auth/                         # Auth features
│   │   ├── LoginPage.tsx
│   │   ├── AuthCallback.tsx
│   │   ├── useAuth.ts
│   │   └── sso.ts
│   │
│   ├── dashboard/                    # Dashboard features
│   │   ├── DashboardPage.tsx
│   │   ├── KpiGrid.tsx               # Draggable KPI tiles
│   │   ├── TopProjects.tsx
│   │   ├── LlmByModel.tsx
│   │   └── RecentRuns.tsx
│   │
│   ├── projects/                     # Project features
│   │   ├── ProjectsListPage.tsx
│   │   ├── ProjectDetailPage.tsx
│   │   └── useProjects.ts
│   │
│   ├── costs/                        # Cost explorer features
│   │   ├── CostsPage.tsx
│   │   ├── CostsOverview.tsx
│   │   ├── CostsBySku.tsx
│   │   └── CostsDaily.tsx
│   │
│   ├── configs/                      # Config management
│   │   ├── ConfigsListPage.tsx
│   │   ├── ConfigCreatePage.tsx
│   │   ├── ConfigCard.tsx
│   │   └── steps/
│   │       ├── StepProvider.tsx
│   │       ├── StepCredentials.tsx
│   │       └── StepReview.tsx
│   │
│   ├── extractors/                   # Run management
│   │   ├── ExtractorsPage.tsx
│   │   ├── TriggerRunCard.tsx
│   │   └── RunHistoryTable.tsx
│   │
│   └── alerts/                       # Alert features
│       ├── AlertsPage.tsx
│       ├── AlertRow.tsx
│       └── useAlerts.ts
│
├── hooks/                            # Custom React hooks
│   ├── useAuth.ts
│   ├── useTheme.ts
│   ├── useDateRange.ts               # URL sync
│   ├── usePreferences.ts             # KPI order/hidden
│   ├── usePolling.ts                 # Repeated refetch
│   └── useToast.ts                   # Toast context
│
├── contexts/                         # React contexts
│   ├── ThemeContext.tsx
│   ├── DateRangeContext.tsx
│   ├── ToastContext.tsx
│   └── index.ts                      # Combined exports
│
├── store/                            # Zustand stores
│   ├── auth.ts                       # Auth tokens
│   ├── ui.ts                         # Theme, sidebar, date range
│   └── index.ts
│
├── query/                            # TanStack Query
│   ├── queryClient.ts                # Configured client
│   ├── queryKeys.ts                  # Key factory
│   └── providers.tsx                 # QueryClientProvider
│
├── schemas/                          # Zod schemas
│   ├── project.ts
│   ├── config.ts
│   ├── run.ts
│   └── alert.ts
│
├── types/                            # Typescript types
│   ├── api.ts
│   ├── index.ts
│   └── enums.ts
│
├── styles/                           # CSS
│   ├── tokens.css                    # :root tokens (if split)
│   ├── pixel-art.css                 # Pixel layer (if split)
│   └── index.css                     # Import all
│
├── utils/                            # Utilities
│   ├── money.ts
│   ├── time.ts
│   ├── format.ts
│   └── constants.ts                  # MAGIC strings
│
├── config/                           # Configuration
│   ├── env.ts                        # Typed env vars
│   ├── sso.ts                        # SSO providers config
│   ├── features.ts                   # Feature flags
│   └── index.ts
│
├── main.tsx                          # Entry point
├── App.tsx                           # Top-level app
└── vite-env.d.ts                     # Vite types
```

---

## Deployment Checklist

- [ ] Update `.env.example` with production variables
- [ ] Run `npm run build` - no TypeScript errors
- [ ] Run `npm run lint` - no ESLint errors
- [ ] Run `npm run preview` - manual smoke test
- [ ] Deploy to staging
- [ ] Test all routes on staging
- [ ] Update GKE deployment (`kubectl apply -f k8s/`)
- [ ] Verify health endpoint (`/healthz`)
- [ ] Monitor logs for errors
- [ ] Notify team of deployment success

---

## Sign-off

**Ready for implementation when**:
1. ✅ All infrastructurePhase tasks assigned
2. ✅ API endpoints documented in `API_ENDPOINTS.txt` (exists at root)
3. ✅ Team agrees onPhase split and timeline
4. ✅ Feature flag mechanism agreed upon

**Estimated Timeline**: 8 weeks (2 phases/week, Buffer: 2 weeks)

**Next Action**: Assign Phase 1 (Infrastructure & Router) to developer, begin Week 1 implementation.
