# Finna Console — Engineering Handoff

> Production rebuild specification. Built for an implementing agent (Claude Code or human) who will translate this self-contained HTML mockup into a real React + TypeScript app wired to a backend.

**Mockup**: `Finna Console.html` (React 18 + Babel standalone, all logic inline)
**Target stack**: React 18 + TypeScript + Vite + React Router 6 + TanStack Query v5 + Tailwind v4 + shadcn/ui (new-york-v4) + Radix + Recharts + Zod + react-hook-form
**Visual direction**: "Pixel-art corporate". Sharp corners (radius: 0), 1px solid borders everywhere, chunky pixel-step shadows (no blur), `Press Start 2P` for headlines + key labels, `VT323` for stat values, `JetBrains Mono` for numbers/IDs/code/buttons, `Inter` for body chrome and prose. NES-style solid-block badges. `[ BRACKETED ]` uppercase mono labels for primary actions. Dithered card headers, scanline overlay on dark theme, pixel-stitch progress bars.

---

## 1 · File layout (mockup)

| File | Role |
|---|---|
| `Finna Console.html` | Entry HTML — loads React, Babel, lucide, then all .js/.jsx in order |
| `styles.css` | Base CSS: tokens (light + dark), shell, components, layout |
| `pixel-art.css` | Pixel-art aesthetic layer (fonts, shadows, dither, scanlines, sprite borders). Layered on top of `styles.css` |
| `tweaks-panel.jsx` | Floating Tweaks panel (host protocol + `useTweaks` hook). Used in mockup for theme toggle |
| `data.js` | Mock data matching OpenAPI schemas. Exposed as `window.FinnaData` |
| `components.jsx` | Shared components: `Icon`, `ProviderBadge`, `StatusBadge`, `SeverityBadge`, `Button`, `StatCard`, `ProgressBar`, `CostDelta`, `EmptyState`, `Dialog`, `LineChart`, `StackedAreaChart`, `HBarList`, `ToastProvider`/`useToast`. Plus `money(n)`, `moneyShort(n)` |
| `shell.jsx` | `AppShell`, `Sidebar`, `Topbar`, `DateRangePicker`, `useHashRoute()`, `navigate(path)`, `NAV` config |
| `pages-1.jsx` | `LoginPage`, `DashboardPage`, `ProjectsListPage`, `ProjectDetailPage`, `Sparkline`, `CostsPage`, `CostsOverview`, `CostsBySku`, `CostsDaily` |
| `pages-2.jsx` | `ConfigsListPage`, `ConfigCreatePage`, `ExtractorsPage`, `AlertsPage`, `SettingsPage` |
| `app.jsx` | Top-level `App` — auth gate, theme plumbing, route table, `TWEAK_DEFAULTS` |

---

## 2 · Information architecture

### 2.1 Routes

All hash-routed in mockup. Replace with `react-router-dom@6` `<BrowserRouter>` + nested routes.

| Route | Auth | Component | Description |
|---|---|---|---|
| `/login` | public | `LoginPage` | Two-column hero + auth form. Redirects to `/dashboard` on success |
| `/dashboard` | required | `DashboardPage` | KPI strip, daily cost chart, top projects, LLM by model, recent runs |
| `/projects` | required | `ProjectsListPage` | Searchable project table |
| `/projects/:slug` | required | `ProjectDetailPage` | Project header, MTD/cap progress, daily area chart, tags, alerts, cost-center card |
| `/configs` | required | `ConfigsListPage` | Cloud config cards (per provider account/subscription) |
| `/configs/new` | required | `ConfigCreatePage` | 3-step wizard (provider → credentials → review) |
| `/configs/:id` | required | `ConfigCreatePage` (edit) | Same component, hydrated. **NOT IMPLEMENTED in mockup — see §10** |
| `/extractors` | required | `ExtractorsPage` | Trigger panel + run history table with polling sim |
| `/costs` | required | `CostsPage` | Tabbed explorer: Overview / By SKU / Daily, driven by topbar date range |
| `/alerts` | required | `AlertsPage` | Triage table, severity badges, ack/silence/dismiss |
| `/settings` | required | `SettingsPage` | Profile, API keys, notifications, tags. Mostly placeholder |

### 2.2 Sidebar nav structure (`shell.jsx::NAV`)

```ts
const NAV = [
  { sec:'Overview' },
  { id:'dashboard',  label:'Dashboard',    icon:'layout-dashboard', path:'/dashboard' },
  { id:'costs',      label:'Cost explorer', icon:'line-chart',      path:'/costs' },
  { sec:'Resources' },
  { id:'projects',   label:'Projects',      icon:'folders',         path:'/projects' },
  { id:'configs',    label:'Cloud configs', icon:'plug',            path:'/configs' },
  { id:'extractors', label:'Extractors',    icon:'workflow',        path:'/extractors' },
  { sec:'Monitoring' },
  { id:'alerts',     label:'Alerts',        icon:'bell',            path:'/alerts',   badge:'count' },
  { id:'settings',   label:'Settings',      icon:'settings',        path:'/settings' },
];
```

The `count` badge for `alerts` reads from `GET /api/v1/alerts/stats` → `firing_count`.

### 2.3 Topbar surfaces (`shell.jsx::Topbar`)

- Breadcrumb: `finna / <pageLabel>` (driven by route)
- Date range chips: `MTD | 7D | 30D | 90D` (segmented, shown on Dashboard + Costs only)
- `DateRangePicker` popover: calendar picker for custom ranges, two months side-by-side
- Theme toggle: sun/moon icon
- Notifications bell with count badge → `/alerts`
- Avatar: opens menu (Profile, Settings, Sign out) — **menu is mocked in `Sidebar` footer instead; topbar avatar is decorative**

---

## 3 · Authentication

### 3.1 Login screen contract

`LoginPage` props: `{ onAuth: () => void }`

**Layout** (`pages-1.jsx::LoginPage`):
- ≥900px: 2-column grid (`grid-template-columns: 1fr 1fr`)
- <900px: single column, branding panel hidden
- Left: dithered + scanline `login-brand` panel, `> finna` mark (Press Start 2P), headline H1, paragraph, three KPI tiles ($1.2M tracked / 3 cloud + LLM / 99.9% uptime)
- Right: `login-form` max-width 380px, centered. Heading "Sign in to Finna", subtitle, then SSO list, then `or` divider, then collapsed email/password section, footer "Need an account? Contact admin · v2.4.1"

**SSO providers** (`SSO_PROVIDERS` const at top of `pages-1.jsx`):

| id | Display | Method | Backend endpoint | Notes |
|---|---|---|---|---|
| `google` | Continue with Google | OAuth 2.0 | `GET /api/v1/auth/sso/google/init` | Redirect to Google consent. Callback: `/auth/callback?provider=google&code=…` |
| `microsoft` | Continue with Microsoft | OAuth 2.0 | `GET /api/v1/auth/sso/microsoft/init` | Azure AD / Entra. Tenant configured per-org |
| `okta` | Continue with Okta | SAML 2.0 | `GET /api/v1/auth/sso/okta/init?org=<slug>` | Org-keyed |
| `github` | Continue with GitHub | OAuth 2.0 | `GET /api/v1/auth/sso/github/init` | |
| `saml` | SAML SSO | SAML 2.0 | `POST /api/v1/auth/sso/saml/init` body: `{org_slug}` | Generic enterprise IdP |

**Each SSO flow:**
```ts
async function ssoLogin(providerId: string) {
  const { authorization_url } = await api.post(`/auth/sso/${providerId}/init`, { return_to: '/dashboard' });
  window.location.href = authorization_url;     // redirect to IdP
}
// IdP redirects back to /auth/callback?code=…&state=…
// /auth/callback page POSTs code → backend → receives JWT → stores → redirects to return_to
```

**Email/password fallback** (collapsed under "Sign in with email and password"):
- `email` (required, valid email format)
- `password` (required, min 8)
- "Forgot password?" link → `/auth/forgot` (**NOT IMPLEMENTED**)
- Submit: `POST /api/v1/auth/token` body: `{username, password}` → `{access_token, refresh_token, user}`
- Inline error if 401: "Invalid email or password"

**Session storage:**
- Mockup: `localStorage["finna_auth"] = "1"` (boolean flag)
- Production:
  - `localStorage["finna_access_token"]` (short-lived JWT, ~15 min)
  - `localStorage["finna_refresh_token"]` (long-lived, ~30 days)
  - `localStorage["finna_user"]` (cached `User` object for UI)
- Logout: `POST /api/v1/auth/revoke` body: `{refresh_token}` → clear localStorage → navigate `/login`

**Auth guard** (production):
```tsx
function ProtectedRoute({ children }) {
  const token = localStorage.getItem('finna_access_token');
  if (!token) return <Navigate to="/login" replace />;
  return children;
}
```

**401 interceptor** in axios/fetch client:
1. Try refresh: `POST /api/v1/auth/refresh` with refresh_token → new access token
2. If refresh fails: clear storage, redirect `/login?expired=1`

---

## 4 · Page-by-page specification

### 4.1 `DashboardPage` (`pages-1.jsx::DashboardPage`)

**Props**: `{ range: 'mtd' | '7d' | '30d' | '90d' | 'custom', customRange?: {start: ISO, end: ISO} }`

**Layout** (top-to-bottom):
1. **Page head** — H1 "Dashboard", subtitle `// last refresh · {timeAgo} · all sources healthy · window: {rangeLabel}`. Right: `[ CUSTOMIZE ]`, `[ REFRESH ]`, `[ EXPORT ]` buttons
2. **Customize strip** (only when edit mode on) — dashed border, restore-pill buttons for hidden tiles
3. **KPI grid** — 5 `StatCard` tiles: Total / Azure / GCP / LLM / Active alerts. Drag-reorder (HTML5 drag&drop). × hide button per tile in edit mode. Order persisted to `localStorage["finna_kpi_order"]`, hidden set to `["finna_kpi_hidden"]`
4. **Two-column row** (`grid-template-columns: 2fr 1fr`):
   - Left: **Daily cost** card with `LineChart` (3 series: Azure / GCP / LLM)
   - Right: **Top projects** card — top 5 projects by MTD cost, `HBarList` with provider badge + name + bar + cost
5. **Two-column row** (`grid-template-columns: 1fr 1fr`):
   - Left: **LLM spend by model** — claude-sonnet, gpt-4o, embeddings, haiku rows with token counts and bar chart
   - Right: **Recent extractor runs** — last 6 runs, table format

**State** (in component):
```ts
const [kpiOrder, setKpiOrder] = useState<KpiId[]>(/* from localStorage or DEFAULT_KPIS */);
const [hidden, setHidden] = useState<Set<KpiId>>(/* from localStorage */);
const [editMode, setEditMode] = useState(false);
const dragRef = useRef<KpiId | null>(null);
```

**Data fetches** (production):
```ts
useQuery(['totals', range], () => api.totals.get(range))         // KPI values
useQuery(['costs', 'daily', range], () => api.costs.daily(range))  // line chart
useQuery(['projects', { sort:'cost_desc', limit:5, range }],
         () => api.projects.list({ sort:'cost_desc', limit:5, window: range }))
useQuery(['llm', 'usage', range], () => api.llm.usage(range))    // model breakdown
useQuery(['runs', { limit: 6 }], () => api.runs.list({ limit:6 }))
```

**Customize-mode interactions:**
- Click `[ CUSTOMIZE ]` → button becomes `[ DONE ]`, tiles get `cursor: move`, drag handles, × buttons
- Drag a tile: `dragRef = tile.id`; on drop on another tile, splice `from` before `to`
- × on tile: add to `hidden` set. Strip above grid shows restore-pills
- Click restore-pill: remove from `hidden`
- All changes persist immediately to localStorage. **Production: PUT `/api/v1/users/me/preferences` with `{kpi_order, kpi_hidden}`**

**Tweaks/Variations exposed in mockup:** none for Dashboard yet — only the global theme.

### 4.2 `ProjectsListPage` (`pages-1.jsx::ProjectsListPage`)

**Props**: none

**Layout:**
- Page head: H1 "Projects", subtitle `// {n} projects · {totalMTD} this period`. Right: search input (`q`), `[ FILTER ]`, `[ NEW PROJECT ]` button
- Single full-width card containing a `<table className="tbl">`:
  - Columns: Project (name + slug), Owner, Cost center, Tags (chips), MTD cost (right), Cap (right), Usage (progress bar), Last sync

**State:**
```ts
const [q, setQ] = useState('');
```

**Filtering**: client-side `filter(p => p.name.includes(q) || p.slug.includes(q) || p.tags.some(t => t.includes(q)))`

**Data**: `useQuery(['projects'], () => api.projects.list())`

**Row click** → `navigate(`/projects/${slug}`)`

### 4.3 `ProjectDetailPage` (`pages-1.jsx::ProjectDetailPage`)

**Props**: `{ slug: string }`

**Layout:**
1. Page head: breadcrumb back link `← All projects`, H1 with project name + provider badge, subtitle `// owner: {owner} · cost-center: {cc} · tags: {tags}`
2. Three-tile strip: MTD cost / Budget cap / Forecast end-of-month
3. Two-column:
   - Left: **Daily cost** — `StackedAreaChart` showing per-SKU breakdown over the date window
   - Right: **Active alerts** for this project (filtered list, severity badges, ack buttons)
4. **Tags & metadata** card — cost-center, owner, created, last sync, notes (free-form)
5. **Cost breakdown by SKU** — table of SKUs sorted by MTD cost desc

**Data:**
```ts
useQuery(['project', slug], () => api.projects.get(slug))
useQuery(['costs', { project: slug, range, group_by:'sku' }], …)
useQuery(['alerts', { project: slug }], …)
```

**Empty/error states:** if `project == null`, show `EmptyState` "Project not found" with `[ BACK TO PROJECTS ]`.

### 4.4 `CostsPage` + sub-tabs (`pages-1.jsx`)

**Props**: `{ range, customRange }` (from topbar)

**Layout:**
- Page head: H1 "Cost explorer", subtitle `// window: {rangeLabel} · total: {money}`. Right: `[ EXPORT CSV ]`, `[ EXPORT XLSX ]`
- Tab strip: Overview / By SKU / Daily
- Tab content area

**Sub-components:**
- `CostsOverview({ rows })` — provider summary cards + project ranking table
- `CostsBySku({ rows })` — grouped by SKU within provider, expandable rows
- `CostsDaily({ providers })` — large `StackedAreaChart`, provider toggle chips, date-range chip showing the active window

**State:**
```ts
const [tab, setTab] = useState<'overview'|'sku'|'daily'>('overview');
const [providerFilter, setProviderFilter] = useState<Set<Provider>>(new Set(['azure','gcp','llm']));
```

**Data:**
```ts
useQuery(['costs', { window: range, ...filters }],
         () => api.costs.list({ window: range, providers: [...providerFilter] }))
```

### 4.5 `ConfigsListPage` (`pages-2.jsx::ConfigsListPage`)

**Props**: none

**Layout:**
- Page head: H1 "Cloud configs", subtitle `// {n} configured · {failures} test failures in last 24h`. Right: `[ + NEW CONFIG ]` → `/configs/new`
- 3-column grid of config cards. Each card:
  - Top row: name (h3) + provider badge
  - Sub: credential type (`service_principal` / `managed_identity` / `cli`)
  - Metadata table: tenant_id (truncated), subscription_id or project_id, created date, last test (status badge + relative time)
  - If `last_test === 'err'`: red error band showing `error_message` (mono)
  - Footer actions: `[ EDIT ]` `[ TEST ]` `Delete` (ghost)

**Interactions:**
- `[ EDIT ]` → `navigate(`/configs/${id}`)`
- `[ TEST ]` → `POST /api/v1/config/${id}/test` → toast success/fail, optimistically update `last_test`
- `Delete` → confirmation Dialog → `DELETE /api/v1/config/${id}`

**Data:**
```ts
useQuery(['configs'], () => api.configs.list())
useMutation(testConfig); useMutation(deleteConfig);
```

### 4.6 `ConfigCreatePage` (`pages-2.jsx::ConfigCreatePage`) — 3-step wizard

**Props** (production): `{ id?: string }` — when present, hydrate from `api.configs.get(id)` for edit mode

**Steps:**
1. **Provider** — radio cards: Azure / GCP / LLM / AWS (disabled in mockup). Sets `prov`
2. **Credentials** — branched form by provider:
   - Azure: tenant_id, subscription_id, client_id, client_secret, OR managed_identity toggle
   - GCP: project_id, service_account_key (JSON paste or upload)
   - LLM: api_provider (anthropic/openai/azure-openai), api_key, base_url (optional)
3. **Review** — read-only summary, `[ TEST CONNECTION ]` button (calls `POST /api/v1/config/test` with body), then `[ SAVE CONFIG ]`

**State:**
```ts
const [step, setStep] = useState(1);
const [prov, setProv] = useState<Provider | null>(null);
const [form, setForm] = useState<Record<string, string>>({});
const [testResult, setTestResult] = useState<'idle'|'pending'|'ok'|'err'>('idle');
```

**Validation** (use Zod):
```ts
const azureSchema = z.object({
  tenant_id: z.string().uuid(),
  subscription_id: z.string().uuid(),
  credential_type: z.enum(['service_principal','managed_identity']),
  client_id: z.string().uuid().optional(),
  client_secret: z.string().min(8).optional(),
}).refine(d => d.credential_type === 'managed_identity' ||
              (d.client_id && d.client_secret),
              { message: 'client_id + client_secret required for service_principal' });
// gcpSchema, llmSchema similar
```

**Submit:**
- New: `POST /api/v1/config` body: `{name, provider, ...credentialFields}` → on 201, navigate `/configs`
- Edit: `PATCH /api/v1/config/${id}` body: changed fields

### 4.7 `ExtractorsPage` (`pages-2.jsx::ExtractorsPage`)

**Layout** (2-col, 1fr / 2fr):
- **Left column — Trigger run** card:
  - Config dropdown (populated from configs list)
  - Extractor type input (optional, hint: "blank · defaults based on provider")
  - `[ ▷ RUN EXTRACTOR ]` primary block button
  - On submit: optimistic insertion of new run with `status='started'`; backend `POST /api/v1/runs` returns `{run_id, status:'started'}`. Polling kicks in.
- **Right column — Run history** card:
  - Filter chips: `status: all` `provider: all` (dropdowns)
  - Sortable table:
    - Status (`StatusBadge`)
    - Run ID (mono)
    - Extractor (e.g. `azure_cost`)
    - Provider (`ProviderBadge`)
    - Started (relative time)
    - Finished (relative time, em-dash if running)
    - Records (right-aligned, mono)
    - Duration (right, mono)
  - Click row → expand inline detail: full timestamps, full run_id, error_message if failed, raw config_id link

**State:**
```ts
const [sel, setSel] = useState<ConfigId>(D.CONFIGS[0].id);
const [extractorType, setExtractorType] = useState('');
const [filter, setFilter] = useState<{status:string, provider:string}>({status:'all',provider:'all'});
const [expandedRun, setExpandedRun] = useState<string | null>(null);
const [newRun, setNewRun] = useState<string | null>(null);  // currently-polling run
```

**Polling:**
```ts
useQuery(['run', newRun], () => api.runs.get(newRun!), {
  enabled: !!newRun,
  refetchInterval: data => ['running','started'].includes(data?.status) ? 2000 : false,
});
```

**Data fetches:**
```ts
useQuery(['runs', filter], () => api.runs.list(filter), { refetchInterval: 10_000 })
useQuery(['configs'], () => api.configs.list())  // for dropdown
useMutation(api.runs.trigger)
```

### 4.8 `AlertsPage` (`pages-2.jsx::AlertsPage`)

**Layout:**
- Page head: H1 "Alerts", subtitle `// {firing} firing · {acked} acked · {silenced} silenced`. Right: `[ NEW RULE ]`
- Stats strip: 4 tiles — Critical / Warning / Info / Silenced (counts)
- Filter row: `severity: all` `status: all` `project: all`
- Triage table:
  - Status, Severity (`SeverityBadge`), Description, Rule (mono, truncated), Project, Triggered (relative), Owner, Actions (ack / silence / dismiss as ghost buttons)

**Interactions:**
- Ack: `POST /api/v1/alerts/${id}/ack` → optimistic status change to `acked`
- Silence: opens Dialog with duration picker (1h / 4h / 24h / custom) → `POST /api/v1/alerts/${id}/silence` body: `{until: ISO}`
- Dismiss: confirmation → `POST /api/v1/alerts/${id}/dismiss`

### 4.9 `SettingsPage`

Currently a placeholder. **Sections to build out:**

1. **Profile** — name, email (read-only), avatar upload, timezone, locale
2. **Organization** — org name, billing email, plan tier, seat usage
3. **API keys** — list of issued keys with `created`, `last_used`, `scopes`. `[ CREATE KEY ]` opens Dialog with name + scope checkboxes → returns one-time-display key
4. **Notifications** — channels (email, slack, webhook) and per-event toggles
5. **Tags** — list of all tags in use, with edit/merge/delete

Each section: `useQuery` + `useMutation` against the corresponding endpoints in §6.

---

## 5 · Component reference (`components.jsx`)

| Component | Props | Behavior |
|---|---|---|
| `Icon({name, size=14, stroke=1.5})` | lucide icon name | Wraps `<i data-lucide=…/>` + `lucide.createIcons()`. **Replace with `lucide-react` `<X size={14}/>` imports** |
| `Button({variant='default', size='md', icon, iconRight, bracket, block, onClick, disabled, type})` | variant: `default\|primary\|danger\|ghost`. `bracket=true` wraps text in `[ ]` and uppercases | Renders `<button class="btn btn-{variant}">…</button>`. Replace with shadcn `<Button>` + a custom `bracket` variant in `cva` |
| `StatCard({label, value, unit, delta, deltaDir, meta, accent, loading})` | accent: `primary\|azure\|gcp\|llm\|danger\|accent` | Stat tile with left-rail accent color. `loading=true` shows skeleton |
| `ProviderBadge({p, size='sm'})` | p: `azure\|gcp\|llm\|aws\|ecb` | Solid block, mono code |
| `StatusBadge({status})` | status: `running\|started\|completed\|failed\|cancelled` | NES block; running gets pulsing green dot |
| `SeverityBadge({severity})` | severity: `critical\|warning\|info` | NES block |
| `ProgressBar({value, max=100, size='sm', stepped, segments})` | | Pixel-stitched bar; tone (danger/warn/ok) auto-derived from pct |
| `CostDelta({value, showArrow=true})` | signed pct | ▲ red / ▼ green / — gray. **Note: cost going up = bad → red** |
| `EmptyState({icon='inbox', title, message, action})` | | Icon + title + mono `// hint` + optional action button |
| `Dialog({open, onClose, title, children, actions})` | | Full-width footer for actions. Pixel-art chrome via `pixel-art.css` |
| `LineChart({series, width=700, height=220, showLegend, stacked})` | series: `[{name, color, data:[{label,value}]}]` | **Replace with Recharts `<LineChart>` in production** |
| `StackedAreaChart({series, width=900, height=280})` | | **Replace with Recharts `<AreaChart>`** |
| `HBarList({items, max, colorFor})` | items: `[{label, value, badge?}]` | Keep hand-rolled — simpler than Recharts |
| `ToastProvider`, `useToast()` | `push(tone, msg)` where tone is `ok\|err\|info` | **Replace with shadcn `useToast`** |
| `money(n, decimals=2)` | | `$1,234.56` |
| `moneyShort(n)` | | `$1.2M` / `$120.5K` |

**`Sparkline({seed, up})`** in `pages-1.jsx` — stylized sine wave for project cards. Replace with Recharts `<Sparkline>` or keep as-is.

---

## 6 · API contract

### 6.1 Base

- Base URL: `${VITE_API_URL}/api/v1` (e.g. `https://api.finna.example.com/api/v1`)
- Auth: `Authorization: Bearer <access_token>` on every request except `/auth/*`
- Content-type: `application/json`
- Pagination: `?page=1&page_size=50`. Responses include `{data: [], page, page_size, total}`
- Errors: RFC 7807 `application/problem+json`: `{type, title, status, detail, instance, errors?}`
- Idempotency: `Idempotency-Key: <uuid>` accepted on all `POST` (extractor triggers, key creation, etc.)

### 6.2 Endpoints

**Auth**
| Method | Path | Body / Query | Returns |
|---|---|---|---|
| POST | `/auth/token` | `{username, password}` | `{access_token, refresh_token, user: User}` |
| POST | `/auth/refresh` | `{refresh_token}` | `{access_token}` |
| POST | `/auth/revoke` | `{refresh_token}` | `204` |
| GET | `/auth/sso/{provider}/init` | `?return_to=/…` | `{authorization_url}` |
| POST | `/auth/sso/saml/init` | `{org_slug, return_to}` | `{authorization_url}` |
| POST | `/auth/sso/callback` | `{provider, code, state}` | `{access_token, refresh_token, user}` |
| GET | `/auth/me` | — | `User` |

**Totals & costs**
| Method | Path | Query | Returns |
|---|---|---|---|
| GET | `/totals` | `window=mtd\|7d\|30d\|90d\|custom`, `start`, `end` | `{total, azure, gcp, llm, alerts: {firing, critical, warning}}` each `{mtd, delta_pct, prev_period}` |
| GET | `/costs` | `window`, `provider[]`, `project[]`, `sku[]`, `group_by=provider\|project\|sku\|day` | `{rows: CostRow[]}` |
| GET | `/costs/daily` | `window`, `provider[]` | `{series: [{provider, points: [{date, value}]}]}` |
| GET | `/llm/usage` | `window` | `{models: [{model, provider, tokens_in, tokens_out, cost_usd}]}` |

**Projects**
| Method | Path | Query / Body | Returns |
|---|---|---|---|
| GET | `/projects` | `?q=&sort=cost_desc&limit=&window=` | `{data: Project[]}` |
| GET | `/projects/{slug}` | — | `Project` (extended with `daily`, `skus`, `alerts`) |
| POST | `/projects` | `{name, owner, cost_center, budget_cap, tags[]}` | `Project` |
| PATCH | `/projects/{slug}` | partial | `Project` |
| DELETE | `/projects/{slug}` | — | `204` |

**Configs**
| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/config` | — | `{data: CloudConfig[]}` |
| GET | `/config/{id}` | — | `CloudConfig` |
| POST | `/config` | provider-specific (see §4.6) | `CloudConfig` |
| PATCH | `/config/{id}` | partial | `CloudConfig` |
| DELETE | `/config/{id}` | — | `204` |
| POST | `/config/{id}/test` | — | `{ok: bool, error?: string, latency_ms}` |
| POST | `/config/test` | full credential body (pre-save) | same |

**Extractors / runs**
| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/runs` | `?status=&provider=&config_id=&limit=` | `{data: ExtractorRun[]}` |
| GET | `/runs/{id}` | — | `ExtractorRun` |
| POST | `/runs` | `{config_id, extractor_type?, params?}` | `{run_id, status:'started'}` |
| POST | `/runs/{id}/cancel` | — | `204` |
| GET | `/runs/{id}/logs` | `?tail=200` | `{lines: string[]}` |

**Alerts**
| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/alerts` | `?severity=&status=&project=` | `{data: Alert[]}` |
| GET | `/alerts/stats` | — | `{firing, acked, silenced, by_severity: {critical, warning, info}}` |
| POST | `/alerts/{id}/ack` | `{note?}` | `Alert` |
| POST | `/alerts/{id}/silence` | `{until: ISO}` | `Alert` |
| POST | `/alerts/{id}/dismiss` | — | `Alert` |
| GET | `/alert-rules` | — | `{data: AlertRule[]}` |
| POST | `/alert-rules` | `{name, expression, severity, channels}` | `AlertRule` |

**User / settings**
| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/users/me` | — | `User` |
| PATCH | `/users/me` | partial profile | `User` |
| GET | `/users/me/preferences` | — | `Preferences` |
| PUT | `/users/me/preferences` | full prefs | `Preferences` |
| GET | `/api-keys` | — | `{data: ApiKey[]}` |
| POST | `/api-keys` | `{name, scopes[]}` | `{key: ApiKey, secret: string}` (one-time) |
| DELETE | `/api-keys/{id}` | — | `204` |
| GET | `/tags` | — | `{data: Tag[]}` |

### 6.3 Schemas (TypeScript shape, Zod-derivable)

```ts
type Provider = 'azure' | 'gcp' | 'llm' | 'aws' | 'ecb';

type User = {
  id: string;
  email: string;
  name: string;
  org_id: string;
  role: 'admin' | 'member' | 'viewer';
  avatar_url?: string;
  timezone: string;       // IANA
  locale: string;         // BCP 47
  created_at: string;     // ISO
};

type Preferences = {
  theme: 'dark' | 'light' | 'system';
  kpi_order: string[];
  kpi_hidden: string[];
  default_window: 'mtd' | '7d' | '30d' | '90d';
};

type Project = {
  id: string;
  slug: string;
  name: string;
  owner: string;
  cost_center: string;
  provider?: Provider;        // primary provider
  budget_cap: number;         // USD
  mtd: number;                // USD
  forecast_eom?: number;
  tags: string[];
  note?: string;
  created_at: string;
  last_sync_at?: string;
  // detail-only:
  daily?: { date: string; value: number; sku?: string }[];
  skus?: { sku: string; mtd: number; units?: number }[];
  alerts?: Alert[];
};

type CloudConfig = {
  id: string;
  name: string;
  provider: Provider;
  credential_type: 'service_principal' | 'managed_identity' | 'cli' | 'oauth' | 'api_key';
  created_at: string;
  last_test: 'ok' | 'err' | 'warn' | 'pending';
  last_test_at: string;       // ISO
  error_message?: string;

  // Azure
  tenant_id?: string;
  subscription_id?: string;
  client_id?: string;
  // (client_secret never returned to UI)

  // GCP
  project_id?: string;
  service_account_email?: string;

  // LLM
  api_provider?: 'anthropic' | 'openai' | 'azure-openai';
  base_url?: string;
};

type ExtractorRun = {
  run_id: string;
  config_id: string;
  extractor: string;          // 'azure_cost', 'gcp_billing', 'otel_llm', 'exchange_rates'
  provider: Provider;
  status: 'started' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string;
  finished_at?: string;
  duration_seconds?: number;
  records_extracted?: number;
  error_message?: string;
};

type CostRow = {
  date?: string;              // present when group_by='day'
  provider: Provider;
  project: string;            // slug
  sku: string;
  units?: number;
  cost_usd: number;
  delta_pct?: number;
};

type Alert = {
  id: string;
  status: 'firing' | 'acked' | 'silenced' | 'dismissed';
  severity: 'critical' | 'warning' | 'info';
  description: string;
  rule: string;               // expression
  project?: string;           // slug
  triggered_at: string;
  acked_by?: string;
  acked_at?: string;
  silenced_until?: string;
};

type ApiKey = {
  id: string;
  name: string;
  prefix: string;             // first 6 chars of secret, for identification
  scopes: string[];
  created_at: string;
  last_used_at?: string;
};
```

---

## 7 · Global state & data flow

### 7.1 What lives where

| State | Lives in | Persistence |
|---|---|---|
| Auth tokens | `localStorage` | Survives reload |
| Current user (`User`) | TanStack Query cache (`['auth','me']`) | Refetched on mount |
| Theme | `localStorage["finna_theme"]` + `[data-theme]` on `<html>` | |
| Date range (topbar) | `AppShell` state, propagated as props | Lost on hard reload (acceptable). **Persist to URL search params** for deep-linkable views: `?window=30d` or `?start=…&end=…` |
| KPI order/hidden | `localStorage` (mockup) → `Preferences` API (prod) | |
| Sidebar collapsed | `AppShell` state | Add `localStorage["finna_sidebar_collapsed"]` |
| Tweaks panel state | `localStorage` via tweaks-panel host protocol | |
| Form drafts (config wizard) | Component state + `sessionStorage` for crash-safety | |

### 7.2 TanStack Query keys (recommended)

```ts
['auth','me']
['totals', range]
['costs', 'list', { window, providers, projects, skus, group_by }]
['costs', 'daily', { window, providers }]
['llm', 'usage', range]
['projects', 'list', { q, sort, limit }]
['project', slug]
['configs', 'list']
['config', id]
['runs', 'list', { status, provider, config_id, limit }]
['run', id]                    // polled while running
['alerts', 'list', filters]
['alerts', 'stats']
['alert-rules']
['users','me','preferences']
['api-keys']
['tags']
```

### 7.3 Date range plumbing

```tsx
// Top-level (in AppShell or a dedicated <RangeProvider>):
const [searchParams, setSearchParams] = useSearchParams();
const range = (searchParams.get('window') as RangeKey) || 'mtd';
const customStart = searchParams.get('start');
const customEnd = searchParams.get('end');

const apiWindow = useMemo(() => {
  if (range === 'custom' && customStart && customEnd) {
    return { start: customStart, end: customEnd };
  }
  return resolvePreset(range); // {start, end} ISO from preset
}, [range, customStart, customEnd]);

// Propagate via context to topbar + dashboard + costs.
```

---

## 8 · Visual system / design tokens

### 8.1 Token names

Defined as CSS custom properties at `:root`. Override via `[data-theme="light"]`. Token list (primary):

```
--bg, --surface, --surface-2, --surface-3
--border, --border-2
--fg, --fg-muted, --fg-subtle
--primary, --primary-fg
--accent (green, ok/running)
--warning (yellow)
--danger (red)
--info (blue)
--azure (#0078d4), --gcp (#ea4335), --llm (#7c3aed), --aws (#ff9900)
--shadow-panel, --ring
--scroll-track, --scroll-thumb

/* pixel-art layer adds: */
--pxshadow-1, --pxshadow-2, --pxshadow-3
--pxshadow-primary, --pxshadow-danger
```

### 8.2 Tailwind v4 wiring

```css
/* src/index.css */
@import 'tailwindcss';
@import './tokens.css';   /* the :root tokens block from styles.css */
@import './pixel-art.css';

@theme {
  --color-bg: var(--bg);
  --color-surface: var(--surface);
  --color-surface-2: var(--surface-2);
  --color-fg: var(--fg);
  --color-fg-muted: var(--fg-muted);
  --color-primary: var(--primary);
  --color-accent: var(--accent);
  --color-warning: var(--warning);
  --color-danger: var(--danger);
  --color-azure: var(--azure);
  --color-gcp: var(--gcp);
  --color-llm: var(--llm);

  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
  --font-pixel: 'Press Start 2P', monospace;
  --font-display: 'VT323', monospace;

  --radius: 0;
}
```

### 8.3 Type rules (don't deviate)

| Surface | Family | Size / weight |
|---|---|---|
| Body / chrome | Inter | 13.5px / 400 |
| Page H1 | Press Start 2P | 16px / 400 (looks bigger; no `text-transform`) |
| Card title (`.card-hd h3`) | Inter | 13px / 600 |
| Stat value (`.stat-val`) | VT323 | 30px / 400 |
| Stat label | Press Start 2P | 8px / 400, letter-spacing 0.06em |
| Button label | JetBrains Mono | 12px / 500 (uppercased when `bracket`) |
| Badges | Press Start 2P | 8px / 400 |
| IDs / paths / numbers in tables | JetBrains Mono | inherits |
| Hint / `// terminal-style` | JetBrains Mono | inherits 12-13px |

### 8.4 Spacing / shape

- **Radius: 0** everywhere. Never round.
- **Borders: 1px solid `var(--border)`** on all containers, inputs, badges, table cells. Sidebar/topbar use 2px.
- **Shadows: pixel-step**. `box-shadow: 2px 2px 0 0 rgba(0,0,0,0.6)` (small), 4px (medium), 6px (dialog). Never blur.
- **Hover**: 60-80ms steps animations. Buttons translate(-1px,-1px) and gain shadow; press translates(2px,2px) and drops shadow.
- **Focus**: 2px solid primary outline (no offset).

### 8.5 Color usage rules

- **Primary (orange/blue depending on theme)** — primary actions, accents, active sidebar items
- **Azure / GCP / LLM** — provider tags **only**. Never decorative.
- **Accent (green)** — success, running status, "OK"
- **Warning (yellow)** — soft caution, low alerts
- **Danger (red)** — critical alerts, destructive actions, AND **upward cost deltas** (cost rising = bad)
- **Surface-2 / Surface-3** — subtle elevation, table headers, hover states

---

## 9 · Theme toggle

`<html data-theme="dark|light">` + `localStorage["finna_theme"]`. Three sources can write to it:

1. Topbar sun/moon button (`Topbar` `setTheme`)
2. Tweaks panel theme toggle (`app.jsx`)
3. System preference on first visit (if no stored value): `prefers-color-scheme`

```ts
function useTheme() {
  const [theme, setTheme] = useState<'dark'|'light'>(() => {
    return (localStorage.getItem('finna_theme') as any)
        ?? (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('finna_theme', theme);
  }, [theme]);
  return [theme, setTheme] as const;
}
```

---

## 10 · Not implemented / known gaps

These are flagged for the implementer to prioritize:

| Gap | Notes |
|---|---|
| Notifications dropdown | Bell currently routes to `/alerts`. Add `GET /api/v1/notifications?unread=true` + dropdown |
| `/auth/forgot` | Forgot-password flow not built. Add password-reset email + token endpoint |
| `/configs/:id` edit hydration | Route exists, form starts blank. Wire up `useQuery(['config', id])` and seed `form` state |
| Saved date ranges | Custom range picker doesn't persist named ranges. Add `Preferences.saved_ranges: [{name, start, end}]` |
| Real OAuth/SAML callbacks | Mockup uses `setTimeout`; production needs `/auth/callback` page that exchanges `code` for tokens |
| Export buttons | `[ EXPORT CSV ]`, `[ EXPORT XLSX ]` are decorative. Wire to `GET /costs/export?format=csv&...` |
| Tag drag-reorder in Settings | Static list today |
| Mobile breakpoints (<900px) | Login degrades to single column; rest is desktop-only. Add mobile sidebar drawer |
| Run logs viewer | `GET /runs/{id}/logs` defined but not surfaced in UI yet — add to expanded run row |
| WebSocket for live alerts/runs | Currently polling. Consider `/ws` channel for push updates |

---

## 11 · Port checklist

### 11.1 Skeleton

```bash
pnpm create vite@latest finna-console -- --template react-ts
cd finna-console
pnpm add react-router-dom@6 @tanstack/react-query@5 axios
pnpm add recharts lucide-react zod react-hook-form @hookform/resolvers
pnpm add date-fns
pnpm add -D tailwindcss@next @tailwindcss/vite @types/node
pnpm dlx shadcn@latest init
pnpm dlx shadcn@latest add \
  button input select checkbox switch dialog toast \
  table tabs badge separator dropdown-menu \
  popover calendar form label radio-group \
  card progress
```

### 11.2 Folder structure

```
src/
  api/
    client.ts          # axios instance + interceptors
    auth.ts
    totals.ts
    costs.ts
    projects.ts
    configs.ts
    runs.ts
    alerts.ts
    settings.ts
  components/
    ui/                # shadcn primitives
    StatCard.tsx
    ProviderBadge.tsx
    StatusBadge.tsx
    SeverityBadge.tsx
    BracketButton.tsx  # the [ FOO ] variant
    DateRangePicker.tsx
    EmptyState.tsx
    LineChart.tsx      # Recharts wrapper
    StackedAreaChart.tsx
    HBarList.tsx
    Sparkline.tsx
  features/
    auth/
      LoginPage.tsx
      AuthCallback.tsx
      ProtectedRoute.tsx
      useAuth.ts
    dashboard/
      DashboardPage.tsx
      KpiGrid.tsx
      RecentRuns.tsx
      TopProjects.tsx
      LlmByModel.tsx
    projects/
      ProjectsListPage.tsx
      ProjectDetailPage.tsx
    costs/
      CostsPage.tsx
      CostsOverview.tsx
      CostsBySku.tsx
      CostsDaily.tsx
    configs/
      ConfigsListPage.tsx
      ConfigCreatePage.tsx
      ConfigCard.tsx
      steps/
        StepProvider.tsx
        StepCredentials.tsx
        StepReview.tsx
    extractors/
      ExtractorsPage.tsx
      TriggerRunCard.tsx
      RunHistoryTable.tsx
    alerts/
      AlertsPage.tsx
      AlertRow.tsx
    settings/
      SettingsPage.tsx
      ProfileSection.tsx
      ApiKeysSection.tsx
      NotificationsSection.tsx
      TagsSection.tsx
  hooks/
    useTheme.ts
    useDateRange.ts
    usePolling.ts
  layouts/
    AppShell.tsx
    Sidebar.tsx
    Topbar.tsx
  schemas/
    project.ts         # Zod
    config.ts
    run.ts
    alert.ts
  styles/
    tokens.css
    pixel-art.css
    index.css
  utils/
    money.ts
    time.ts
  App.tsx
  main.tsx
```

### 11.3 Key wiring

```tsx
// src/App.tsx
function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage/>}/>
          <Route path="/auth/callback" element={<AuthCallback/>}/>
          <Route element={<ProtectedRoute><AppShell/></ProtectedRoute>}>
            <Route path="/dashboard"        element={<DashboardPage/>}/>
            <Route path="/projects"         element={<ProjectsListPage/>}/>
            <Route path="/projects/:slug"   element={<ProjectDetailPage/>}/>
            <Route path="/configs"          element={<ConfigsListPage/>}/>
            <Route path="/configs/new"      element={<ConfigCreatePage/>}/>
            <Route path="/configs/:id"      element={<ConfigCreatePage/>}/>
            <Route path="/extractors"       element={<ExtractorsPage/>}/>
            <Route path="/costs"            element={<CostsPage/>}/>
            <Route path="/alerts"           element={<AlertsPage/>}/>
            <Route path="/settings"         element={<SettingsPage/>}/>
            <Route index                    element={<Navigate to="/dashboard" replace/>}/>
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace/>}/>
        </Routes>
      </BrowserRouter>
      <Toaster/>
    </QueryClientProvider>
  );
}
```

```tsx
// src/api/client.ts
import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL + '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(cfg => {
  const t = localStorage.getItem('finna_access_token');
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

api.interceptors.response.use(
  r => r,
  async err => {
    if (err.response?.status === 401 && !err.config._retry) {
      err.config._retry = true;
      const refreshed = await tryRefresh();
      if (refreshed) {
        err.config.headers.Authorization = `Bearer ${refreshed}`;
        return api(err.config);
      }
      localStorage.clear();
      window.location.href = '/login?expired=1';
    }
    return Promise.reject(err);
  }
);
```

### 11.4 Charts swap

```tsx
// LineChart.tsx (Recharts replacement)
import { ResponsiveContainer, LineChart as RC, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';

export function LineChart({ series }: { series: Series[] }) {
  // Reshape from {name, color, data:[{label,value}]} to flat {label, [name]: value}
  const flat = series[0].data.map((p, i) => {
    const row: any = { label: p.label };
    series.forEach(s => { row[s.name] = s.data[i].value; });
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={220}>
      <RC data={flat} margin={{ top: 12, right: 12, bottom: 28, left: 48 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="2 3" vertical={false}/>
        <XAxis dataKey="label"
               tick={{ fontFamily: 'JetBrains Mono', fontSize: 10, fill: 'var(--fg-subtle)' }}
               stroke="var(--border)"/>
        <YAxis tickFormatter={moneyShort}
               tick={{ fontFamily: 'JetBrains Mono', fontSize: 10, fill: 'var(--fg-subtle)' }}
               stroke="var(--border)"/>
        <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 0, fontFamily: 'JetBrains Mono', fontSize: 11 }}/>
        <Legend wrapperStyle={{ fontFamily: 'JetBrains Mono', fontSize: 11 }}/>
        {series.map(s => (
          <Line key={s.name} type="monotone" dataKey={s.name}
                stroke={s.color} strokeWidth={1.5} dot={false} isAnimationActive={false}/>
        ))}
      </RC>
    </ResponsiveContainer>
  );
}
```

### 11.5 BracketButton variant

```tsx
// Extend shadcn Button with `bracket` variant via cva:
const buttonVariants = cva(
  "inline-flex items-center justify-center transition-[transform,box-shadow] duration-75 …",
  {
    variants: {
      variant: {
        default: "bg-surface border border-border hover:bg-surface-3",
        primary: "bg-primary text-primary-fg",
        danger:  "bg-danger text-white",
        ghost:   "bg-transparent border-transparent hover:bg-surface-2",
      },
      bracket: {
        true: "font-mono uppercase tracking-wide before:content-['['] before:mr-1.5 before:opacity-70 after:content-[']'] after:ml-1.5 after:opacity-70",
        false: "",
      },
    },
    defaultVariants: { variant: "default", bracket: false },
  },
);
```

### 11.6 Acceptance checklist

Before shipping, verify each of:

- [ ] Login → SSO redirect → callback → dashboard land works for all 5 providers
- [ ] Email/password login validates, shows inline errors, clears password on failure
- [ ] 401 on any API call triggers refresh → retry; if refresh fails, redirect to `/login?expired=1`
- [ ] Topbar date range writes to URL search params; deep-link `/dashboard?window=30d` works
- [ ] Custom date range from picker writes `?start=…&end=…`
- [ ] Dashboard KPI drag-reorder persists to `/users/me/preferences` (not localStorage)
- [ ] Dashboard hide/restore tile persists same
- [ ] Theme toggle writes to localStorage AND `data-theme`; survives reload
- [ ] Sidebar collapse persists to localStorage
- [ ] Cloud config wizard validates per-provider, enables `[ TEST ]` only when current step is valid, surfaces test latency on success
- [ ] Extractors trigger creates run optimistically, polls status every 2s, stops polling on terminal status
- [ ] Run history table refetches every 10s while page mounted
- [ ] Alert ack/silence/dismiss are optimistic with rollback on error
- [ ] Empty states show on `data: []` for all lists
- [ ] Loading states show skeletons matching the final layout (not spinners)
- [ ] Error states show retry button + the API problem `detail`
- [ ] All buttons have `disabled` while their mutation is pending
- [ ] All forms use `react-hook-form` + Zod, with field-level errors shown inline
- [ ] Lucide icons via `lucide-react` (not the global `data-lucide` runtime)
- [ ] Light theme passes WCAG AA contrast on body text and badges
- [ ] Print stylesheet hides sidebar/topbar (for cost-explorer reports)
- [ ] No console warnings or errors on any route

---

## 12 · Tone / copy

- **Action labels** — imperative, lowercase. Brackets when primary. `refresh`, `[ RUN EXTRACTOR ]`, `delete`
- **Empty states** — short, slightly nerdy. `no runs yet` / `// awaiting first extraction`
- **Errors** — present tense, plain. "Enter a password to continue" not "Password is required"
- **Hints** — `//` prefix only for terminal-style hints near code/IDs
- **Numbers** — tabular nums always, currency suffix `$1,234.56 USD`
- **Dates** — relative ("4 min ago") in tables, absolute ("Apr 24, 2026 14:32 UTC") on detail views

---

## 13 · Environment / config

```env
VITE_API_URL=https://api.finna.example.com
VITE_SENTRY_DSN=...
VITE_FEATURE_NOTIFICATIONS_DROPDOWN=false
VITE_FEATURE_WEBSOCKETS=false
```

Feature flags gate the in-progress surfaces from §10.

---

Ship it.
