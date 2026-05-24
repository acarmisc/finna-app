## PR #190: Centralize getAuthToken to prevent scattered localStorage access

**Branch**: `fix/issue-190-auth-centralization`

**Issue**: #190

### Summary

This PR addresses a high-priority security vulnerability where `localStorage.getItem('finna_token')` was being accessed directly in multiple pages instead of going through the centralized auth store.

### Changes Made

1. **Added `getAuthToken()` helper** in `/ui/src/store/auth.ts`
   - Centralized function that retrieves token from Zustand state
   - Routes through axios interceptor for consistent auth header handling

2. **Refactored pages** to use `getAuthToken()`:
   - `ui/src/pages/CostsPage.tsx` - 1 replacement in `exportCsv`
   - `ui/src/pages/ConfigCreatePage.tsx` - 2 replacements (useEffect + handleSubmit)
   - `ui/src/pages/ProjectDetailPage.tsx` - 1 replacement in `handleDelete`

3. **Added ESLint rule** in `eslint.config.mjs`
   - Bans `localStorage` access outside the auth store
   - Prevents future security issues from scattered access

### Security Impact

- ✅ Token access now goes through centralized auth store
- ✅ Routes through axios interceptor for consistent auth
- ✅ Prevents future regressions with ESLint rule
- ✅ Improves maintainability and auditability

### Testing

- [x] All localStorage access replaced with `getAuthToken()` from auth store
- [x] ESLint validation added to prevent future issues
- [x] Commit pushed to branch `fix/issue-190-auth-centralization`
