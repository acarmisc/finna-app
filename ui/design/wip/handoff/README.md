# Finna Console — Engineering Handoff

This folder is the production-rebuild specification for **Finna Console**. It accompanies the HTML mockup `Finna Console.html` and turns it into a real React + TypeScript application wired to a backend.

## How to use this pack

1. Read **00-getting-started.md** first — it establishes the stack and gets a project running.
2. Read **01-architecture.md** for the big picture (routing, state, data flow).
3. Read **02-design-system.md** before writing any UI — every component depends on these tokens.
4. Read **03-auth.md** and **04-app-shell.md** before any page (everything is rendered inside the shell).
5. Pages can then be built independently. Each page doc (`05` through `11`) is self-contained: layout, props, state, data, interactions, edge cases, acceptance.
6. **12-api-reference.md** + **13-schemas.md** are the contract with the backend team — share them.
7. **14-acceptance.md** is the QA checklist; gate the release on it.
8. **15-known-gaps.md** is what was deferred from the mockup — prioritise with the PM.

## Index

| # | File | What's in it |
|---|---|---|
| 00 | `00-getting-started.md` | Stack, env, install, scripts, repo layout |
| 01 | `01-architecture.md` | Routes, state ownership, query keys, data flow |
| 02 | `02-design-system.md` | Tokens, typography, shadows, components, Tailwind wiring |
| 03 | `03-auth.md` | Login UI, SSO providers, token lifecycle, guards |
| 04 | `04-app-shell.md` | Sidebar, topbar, date range, breadcrumb, theme toggle |
| 05 | `05-page-dashboard.md` | KPI grid, charts, customise mode |
| 06 | `06-page-projects.md` | List + detail |
| 07 | `07-page-costs.md` | Overview / By SKU / Daily tabs |
| 08 | `08-page-configs.md` | List + 3-step create wizard |
| 09 | `09-page-extractors.md` | Trigger + run history with polling |
| 10 | `10-page-alerts.md` | Triage table, ack/silence/dismiss |
| 11 | `11-page-settings.md` | Profile, API keys, notifications, tags |
| 12 | `12-api-reference.md` | All endpoints, methods, request/response |
| 13 | `13-schemas.md` | TypeScript types + Zod schemas |
| 14 | `14-acceptance.md` | QA checklist before ship |
| 15 | `15-known-gaps.md` | Deferred work, feature flags |

## Mockup files (also in the zip)

| File | Role |
|---|---|
| `Finna Console.html` | Entry HTML (React 18 + Babel standalone, all logic inline) |
| `styles.css` | Base CSS: tokens (light + dark), shell, components |
| `pixel-art.css` | Pixel-art aesthetic layer (Press Start 2P titles, chunky shadows, dither, scanlines) |
| `tweaks-panel.jsx` | Floating Tweaks panel (host protocol + `useTweaks` hook) |
| `data.js` | Mock data matching OpenAPI schemas (`window.FinnaData`) |
| `components.jsx` | Shared components |
| `shell.jsx` | `AppShell`, `Sidebar`, `Topbar`, `DateRangePicker`, hash router |
| `pages-1.jsx` | `LoginPage`, `DashboardPage`, `ProjectsListPage`, `ProjectDetailPage`, `CostsPage` |
| `pages-2.jsx` | `ConfigsListPage`, `ConfigCreatePage`, `ExtractorsPage`, `AlertsPage`, `SettingsPage` |
| `app.jsx` | Top-level `App` — auth gate, theme, routes, `TWEAK_DEFAULTS` |

## Conventions across docs

- **Italian-style brackets in actions** are intentional: `[ RUN EXTRACTOR ]` is a bracketed bracketed mono button (see design system).
- TypeScript snippets are illustrative — adapt to your codebase style.
- API paths are relative to `${VITE_API_URL}/api/v1`.
- All endpoints expect `Authorization: Bearer <access_token>` unless noted.
- All `POST`s accept `Idempotency-Key: <uuid>` header.
