# FinOps Console - Agent Guide

This is a pixel-art dark-themed FinOps dashboard (Azure/GCP/LLM costs). Follow these conventions.

## Commands

- **Run dev**: `npm run dev` → `http://localhost:5173`
- **Build**: `npm run build` (`tsc` + `vite build`)
- **Preview**: `npm run preview`
- **CI**: GitHub Actions runs `npm ci` then `npx tsc --noEmit` and `npm run build`

## Architecture

- **Entry**: `src/main.tsx` — hash-based router (`#/dashboard`, `#/projects`, etc.)
- **Layout**: `AppShell` wraps pages with `Sidebar` + `TopBar`
- **State**: Zustand (`useAuthStore`) with JWT in `localStorage.finna_token`
- **Styling**: Tailwind v4 with custom `@theme` tokens in `src/index.css`
- **Auth**: Basic login (`admin/admin`) — stores token on login

## Routes

| Path | Page |
|------|------|
| `#/dashboard` | DashboardPage |
| `#/projects` | ProjectsListPage |
| `#/projects/:slug` | ProjectDetailPage |
| `#/costs` | CostsPage |
| `#/configs` | ConfigsListPage |
| `#/configs/new` | ConfigCreatePage (3-step wizard) |
| `#/alerts` | AlertsPage |
| `#/settings` | SettingsPage |
| `#/runs` | RunHistoryPage |
| `#/sources` | DataSourcesPage |

## Design Conventions

- **Font**: `JetBrains Mono` for numbers/labels, `Inter` for body
- **Theme**: Dark first (`--bg: #0d1117`), light mode via `.dark`/`.light` classes
- **Buttons**: `[label]` bracket style (`pixel-btn` / `btn` classes)
- **Borders**: Sharp (radius: 0), no shadows
- **Provider colors**: `--azure` (#0078d4), `--gcp` (#ea4335), `--llm` (#7c3aed)

## Important Notes

- Dev server proxies `/api` to `http://localhost:8000` (vite.config.ts:17)
- Deployment uses GKE (`finna-app-staging` namespace, `finna-console` deployment)
- Docker image: `europe-west1-docker.pkg.dev/abs-digital-playground/finna-app-staging/frontend:latest`
- Backend endpoint: `https://finna-app.ces.abssrv.it/api/v1`
- Frontend URL: `https://finna-app-ui.ces.abssrv.it`
- Build artifact: `dist/` → nginx `/usr/share/nginx/html/`

## Testing

- Typecheck: `npx tsc --noEmit` (CI step)
- No test framework configured yet

## UI Library

- shadcn/ui (base-nova style, `"@tailwindcss/vite": "^4.2.4"`)
- Components: `src/components/ui/` and `src/components/shared/`
