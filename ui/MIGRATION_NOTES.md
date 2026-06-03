# UI Token Storage Migration Plan

## Current State (Interim Defense-in-Depth)

As of June 2026, token storage is centralized in `ui/src/lib/tokenStorage.ts`. This module wraps `localStorage` and `sessionStorage` access, storing `finna_token` in both locations:

- **sessionStorage** (primary): Session-scoped, cleared on browser close
- **localStorage** (fallback): Persistent across sessions for recovery

All direct `localStorage.getItem('finna_token')` calls have been replaced with `getToken()`, `setToken()`, and `clearToken()` from this module.

## Full Migration Path: HttpOnly Cookies + CSRF

The next phase (deferred) requires:

1. **Backend Changes**
   - Add `/auth/refresh-token` endpoint that issues HttpOnly, Secure, SameSite cookies
   - Implement CSRF token generation (`/auth/csrf-token`) and validation middleware
   - Update token refresh logic to issue fresh CSRF tokens

2. **Frontend Changes**
   - Remove all calls to `tokenStorage.ts` (now unused)
   - Update `api/client.ts` to rely on automatic cookie transmission (`withCredentials: true`)
   - Add CSRF token from cookie to request headers (e.g., `X-CSRF-Token`)
   - Update `useAuthStore.checkAuth()` to call `/auth/csrf-token` on init

3. **Security Benefits**
   - Tokens no longer readable by XSS (browser cannot access HttpOnly cookies via JS)
   - CSRF protection prevents cross-site form submissions
   - Shorter cookie expiry with automatic refresh via `/auth/refresh`

4. **Migration Checklist**
   - [ ] Define `/auth/refresh-token` endpoint
   - [ ] Implement `/auth/csrf-token` endpoint
   - [ ] Add CSRF validation middleware to protected routes
   - [ ] Update frontend to omit manual `Authorization` header (use cookie instead)
   - [ ] Update tests to mock cookie jar behavior
   - [ ] Deploy with backward compatibility (support both old and new auth)

## References

- SECURITY_AUDIT.md §2.7 — XSS & Token Storage
- https://owasp.org/www-community/attacks/csrf
- https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
