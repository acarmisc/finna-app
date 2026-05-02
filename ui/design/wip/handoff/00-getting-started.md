# 00 · Getting started

## Target stack

- **React 18** + **TypeScript** (strict)
- **Vite** (build/dev)
- **React Router 6** (`BrowserRouter`)
- **TanStack Query v5** (server state)
- **axios** (HTTP client + interceptors)
- **Tailwind v4** + **shadcn/ui (new-york-v4)** + **Radix UI**
- **Recharts** (charts)
- **Zod** + **react-hook-form** (forms + validation)
- **lucide-react** (icons)
- **date-fns** (date math)

Optional: **Sentry** (errors), **PostHog** (product analytics), **MSW** (mocked API in dev).

## Repository layout

```
finna-console/
├── public/
├── src/
│   ├── api/                 # axios client + per-resource clients
│   ├── components/
│   │   ├── ui/              # shadcn primitives
│   │   └── …                # shared app components
│   ├── features/            # one folder per page or domain
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── projects/
│   │   ├── costs/
│   │   ├── configs/
│   │   ├── extractors/
│   │   ├── alerts/
│   │   └── settings/
│   ├── hooks/
│   ├── layouts/             # AppShell, Sidebar, Topbar
│   ├── schemas/             # Zod
│   ├── styles/              # tokens.css, pixel-art.css, index.css
│   ├── utils/               # money, time
│   ├── App.tsx
│   └── main.tsx
├── .env.example
├── package.json
└── vite.config.ts
```

## Bootstrap

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

## Environment

`.env.example`:

```env
VITE_API_URL=https://api.finna.example.com
VITE_SENTRY_DSN=
VITE_FEATURE_NOTIFICATIONS_DROPDOWN=false
VITE_FEATURE_WEBSOCKETS=false
```

## Scripts (`package.json`)

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit",
    "lint": "eslint . --ext .ts,.tsx",
    "test": "vitest"
  }
}
```

## Done when

- [ ] `pnpm dev` boots, shadcn primitives render
- [ ] Tailwind v4 picks up `src/styles/tokens.css` (see `02-design-system.md`)
- [ ] Press Start 2P + JetBrains Mono + Inter all loaded (Google Fonts via `<link>` in `index.html`)
- [ ] `.env.local` resolves `VITE_API_URL`
- [ ] axios instance + 401 refresh interceptor are in place (`03-auth.md`)
