# Finna App UI - Implementation Plan

## Current State
- React 18 + Vite + TypeScript + Tailwind CSS v4 + shadcn/ui
- Basic auth store with Zustand
- Minimal App.tsx with Sidebar and Dashboard
- API client connecting to backend

## Issues to Implement (I6.1 - I9.5)

### High Priority Pages (I8.x)
1. I8.2 - Dashboard page (WIP - partial, needs routing)
2. I8.3 - Configurations list page
3. I8.4 - Configurations new (stepped form)
4. I8.6 - Projects list page
5. I8.9 - Cost explorer — Overview tab
6. I8.13 - 404 + error pages
7. I8.1 - Login page
8. I8.5 - Configurations edit page
9. I8.7 - Project detail page
10. I8.12 - Alerts page
11. I8.8 - Extractors page
12. I8.10 - Cost explorer — By SKU tab
13. I8.11 - Cost explorer — Daily trend tab

### Layout (I6.1 - I7.2)
14. I6.1 - Sidebar component (WIP - partial)
15. I6.2 - TopBar component
16. I6.3 - AppShell composition
17. I6.4 - ProtectedRoute wrapper
18. I7.1 - React Router configuration
19. I7.2 - Integrate router in App.tsx

### Polish (I9.1 - I9.5)
20. I9.1 - Format utilities
21. I9.2 - A11y audit
22. I9.3 - Light mode toggle verify
23. I9.4 - E2E smoke test (Playwright)
24. I9.5 - Frontend README

## Implementation Order

### Phase 1: Core Layout & Routing (I6.1-I7.2)
- Create proper Sidebar component
- Create TopBar component
- Create AppShell wrapper
- Implement ProtectedRoute
- Set up React Router with route configuration

### Phase 2: Page Components (I8.x)
- Create all pages with MVP implementations
- Focus on high-priority pages first

### Phase 3: Polish (I9.x)
- Format utilities
- A11y improvements
- Light mode support
- E2E tests
- README

## Key Decisions
- Use MVP approach over perfect code
- Reuse existing hooks from hooks/useData.ts
- Reuse existing API client from services/apiClient.ts
- Follow existing component patterns
- Keep token budget in mind
