# 01 · Architecture

High-level map of the app: how routes, state, and data flow connect.

## Routes

All routes hash-routed in the mockup (`#/dashboard`). In production: `BrowserRouter`.

| Route | Auth | Component | Doc |
|---|---|---|---|
| `/login` | public | `LoginPage` | `03-auth.md` |
| `/auth/callback` | public | `AuthCallback` | `03-auth.md` |
| `/dashboard` | protected | `DashboardPage` | `05` |
| `/projects` | protected | `ProjectsListPage` | `06` |
| `/projects/:slug` | protected | `ProjectDetailPage` | `06` |
| `/costs` | protected | `CostsPage` | `07` |
| `/configs` | protected | `ConfigsListPage` | `08` |
| `/configs/new` | protected | `ConfigCreatePage` | `08` |
| `/configs/:id` | protected | `ConfigCreatePage` (edit) | `08` |
| `/extractors` | protected | `ExtractorsPage` | `09` |
| `/alerts` | protected | `AlertsPage` | `10` |
| `/settings` | protected | `SettingsPage` | `11` |
| `*` | — | `Navigate to /dashboard` | — |

Wiring sketch:

```tsx
function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage/>} />
          <Route path="/auth/callback" element={<AuthCallback/>} />
          <Route element={<ProtectedRoute><AppShell/></ProtectedRoute>}>
            <Route path="/dashboard"      element={<DashboardPage/>} />
            <Route path="/projects"       element={<ProjectsListPage/>} />
            <Route path="/projects/:slug" element={<ProjectDetailPage/>} />
            <Route path="/costs"          element={<CostsPage/>} />
            <Route path="/configs"        element={<ConfigsListPage/>} />
            <Route path="/configs/new"    element={<ConfigCreatePage/>} />
            <Route path="/configs/:id"    element={<ConfigCreatePage/>} />
            <Route path="/extractors"     element={<ExtractorsPage/>} />
            <Route path="/alerts"         element={<AlertsPage/>} />
            <Route path="/settings"       element={<SettingsPage/>} />
            <Route index element={<Navigate to="/dashboard" replace/>} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace/>} />
        </Routes>
      </BrowserRouter>
      <Toaster/>
    </QueryClientProvider>
  );
}
```

## State ownership

| State | Where | Persistence |
|---|---|---|
| Auth tokens | `localStorage` | survives reload |
| Current user | TanStack Query `['auth','me']` | refetched on mount |
| Theme | `localStorage["finna_theme"]` + `<html data-theme>` | yes |
| Date range | URL search params (`?window=…&start=…&end=…`) | deep-linkable |
| KPI order / hidden | `Preferences` API | server-persisted |
| Sidebar collapsed | `localStorage["finna_sidebar_collapsed"]` | yes |
| Form drafts (wizard) | component state + `sessionStorage` | crash-safe |
| Tweaks panel (mockup only) | host protocol | dev-only |

## TanStack Query keys

```ts
['auth','me']
['totals', range]
['costs', 'list',  { window, providers, projects, skus, group_by }]
['costs', 'daily', { window, providers }]
['llm',   'usage', range]
['projects', 'list', { q, sort, limit }]
['project', slug]
['configs', 'list']
['config',  id]
['runs', 'list', { status, provider, config_id, limit }]
['run',  id]                     // polled while running
['alerts', 'list', filters]
['alerts', 'stats']
['alert-rules']
['users','me','preferences']
['api-keys']
['tags']
```

## Date range plumbing

Source of truth: URL search params, propagated via context.

```tsx
function useDateRange() {
  const [searchParams, setSearchParams] = useSearchParams();
  const range = (searchParams.get('window') as RangeKey) || 'mtd';
  const customStart = searchParams.get('start');
  const customEnd   = searchParams.get('end');

  const apiWindow = useMemo(() => {
    if (range === 'custom' && customStart && customEnd) {
      return { start: customStart, end: customEnd };
    }
    return resolvePreset(range); // {start, end} ISO from preset
  }, [range, customStart, customEnd]);

  return { range, apiWindow, setRange: (r: RangeKey) => setSearchParams({window: r}) };
}
```

`Topbar`, `DashboardPage`, `CostsPage`, `ProjectDetailPage` all read this hook.

## Polling rules

| Surface | Strategy |
|---|---|
| `useQuery(['run', id])` | `refetchInterval: data => isTerminal(data?.status) ? false : 2000` |
| Run history `useQuery(['runs','list', f])` | `refetchInterval: 10_000`, paused when tab not visible |
| Alerts list | `refetchInterval: 30_000` |
| Dashboard totals | manual refresh button + `staleTime: 60_000` |

## Error & loading patterns

- **Loading**: skeleton matching final layout, never spinners except on inline buttons.
- **Empty**: `EmptyState` with mono `// hint` and primary CTA.
- **Error**: inline error card with retry button + `problem.detail`.
- **Mutation pending**: button disabled + label swapped (`[ RUN ]` → `[ RUNNING… ]`).

## Feature flags

Read via `import.meta.env.VITE_FEATURE_*` and gate the surfaces in `15-known-gaps.md`.
