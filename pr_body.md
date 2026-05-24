## Summary

This PR addresses the security issue described in #190 where localStorage token access was scattered across multiple pages (CostsPage, ConfigCreatePage, ProjectDetailPage), creating duplication of auth logic and maintenance risks.

## Changes

### 1. Added `getAuthToken()` helper in auth store
- Created centralized `getAuthToken()` function that pulls token from Zustand state via `useAuthStore.getState().token`
- This routes access through the existing axios interceptor for consistent token handling
- Added ESLint exception marker at the bottom of `auth.ts` to allow localStorage access in the auth store only

### 2. Refactored affected pages
- **CostsPage.tsx**: Replaced `localStorage.getItem('finna_token')` with `getAuthToken()` in `exportCsv` function
- **ConfigCreatePage.tsx**: Replaced 2 occurrences of `localStorage.getItem('finna_token')` with `getAuthToken()` in useEffect and `handleSubmit`
- **ProjectDetailPage.tsx**: Replaced `localStorage.getItem('finna_token')` with `getAuthToken()` in `handleDelete` function

### 3. Added ESLint rule to prevent regressions
- Added `no-restricted-globals` rule in `eslint.config.mjs` to ban `localStorage` access outside of the auth store
- Error message guides developers to use `getAuthToken()` from `@/store/auth` instead

## Security Impact

This change ensures:
- All token access goes through the auth store (centralized)
- Token retrieval routes through axios interceptor (consistent auth header injection)
- Prevents future security issues from scattered localStorage access
- Makes token management more maintainable and auditable

## Testing

- [x] Type check passes (`npx tsc --noEmit`)
- [x] Build succeeds (`npm run build`)
- [x] ESLint validates no localStorage access outside auth store

Closes #190
