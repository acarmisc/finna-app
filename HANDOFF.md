# OIDC SSO Integration — Handoff Notes

**Date:** 2026-05-16  
**Status:** 80% complete (PR-1 through PR-5 in progress)  
**Context:** Claude Haiku 4.5 at 76% token usage when paused

---

## Summary

OIDC (OpenID Connect) SSO integration for Finna app is largely complete. Backend fully functional, frontend ~90% done. Ready for final assembly and deployment.

**What's merged to main:**
- ✅ PR-1: auth_providers table + provider CRUD routes (6d7e1b)
- ✅ PR-2: OIDC client module (discovery, JWKS, token exchange, ID token verification) (95f10ce)
- ✅ PR-3: OIDC login/callback routes + comprehensive E2E tests (43a2a56)
- ✅ PR-4: Settings UI for managing OIDC providers (46b981e)

**In progress:**
- 🟡 PR-5: Login page with OIDC provider buttons (branch: `feat/oidc-pr5-login-page`)
- ⏳ PR-6: Documentation + Keycloak setup guide (not started)

---

## Generated Secrets

**Store these in `.env.local` or GKE secrets immediately:**

```env
JWT_SECRET=kKuqugJUBEYy7RXB1JYdR8OxDXbKQq2whx12cHjdfQo
ENCRYPTION_KEY=TOe6oe5eAn9S6Y6QBQqYelCFBrFnFJJyJDy1Bu3X-T4=
AUTO_MIGRATE=true
```

> ⚠️ **Critical:** These are single-use generated keys. **Do NOT** commit to git. Set via:
> - Local: `.env.local`
> - Docker: `docker-compose.yml` env vars
> - GKE: `kubectl create secret generic finops-secrets --from-literal=...`
> - GitHub Actions: `GITHUB_ENVIRONMENT` secrets

---

## PR-5 (Login Page) — What's Left

**Branch:** `feat/oidc-pr5-login-page`

**Completed files:**
- `ui/src/components/auth/OIDCCallbackHandler.tsx` — New callback handler for OIDC redirect
- `ui/src/components/auth/LoginComponent.tsx` — Updated with:
  - `fetchOidcProviders()` — GET /api/v1/auth/oidc/providers
  - `oidcLogin(providerId)` — POST /auth/oidc/login, redirect to IdP
  - Render loop adding OIDC buttons below GitHub button

**Remaining work (< 5 min):**

1. **Register callback route in `ui/src/App.tsx`:**
   ```tsx
   import { OIDCCallbackHandler } from '@/components/auth/OIDCCallbackHandler'
   
   // In router config, add:
   <Route path="/auth/oidc/callback" element={<OIDCCallbackHandler />} />
   ```

2. **Commit PR-5:**
   ```bash
   git add ui/src/components/auth/{OIDCCallbackHandler.tsx,LoginComponent.tsx}
   git commit -m "feat: Login page with OIDC provider buttons (PR-5 of 6)
   
   - OIDC providers fetched from GET /auth/oidc/providers (public endpoint)
   - Post-login redirect handler for OIDC callback
   - Integration with sessionStorage for provider_id during flow
   - Buttons render below GitHub OAuth button
   - Error handling for invalid/failed callbacks
   
   Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
   ```

3. **Merge to main:**
   ```bash
   git checkout main
   git merge feat/oidc-pr5-login-page
   git push origin main
   ```

---

## PR-6 (Documentation) — Tasks

**Files to create:**

### `docs/oidc-setup.md` — Provider walkthroughs

Template structure:
```markdown
# OIDC Setup Guide

## Keycloak (Recommended for testing)

1. Create realm: `finna`
2. Create client: `finna-app` (confidential)
   - Client secret: generate
   - Valid redirect URI: `http://localhost:5173/auth/oidc/callback` (or prod URL)
3. Create mapper: `groups` (audience-based, add to ID token)
4. Create users and assign to role/group `finna-admins`
5. Provider config in Finna Settings:
   - Issuer: `https://keycloak.example.com/realms/finna`
   - Client ID/Secret: from step 2
   - Claim mappings: username=preferred_username, email=email, is_admin={claim:groups, match:finna-admins}

## Okta Setup

[Similar 5-step guide]

## Azure AD

[Similar guide]
```

### Update `README.md` Authentication section

Add subsection:
```markdown
### OIDC / Single Sign-On

Finna supports OpenID Connect for enterprise SSO with:
- Keycloak, Okta, Auth0, Azure AD, Google, or any spec-compliant IdP
- Claim-based role mapping (auto-admin from IdP groups)
- Email domain filtering (restrict to org domain)
- Auto-provisioning of users on first login

**Setup:** See [docs/oidc-setup.md](docs/oidc-setup.md) for provider walkthroughs.

**Admin UI:** Settings → Authentication → Add Provider
```

---

## Architecture Notes

### Backend (Complete ✅)

**Files:**
- `alembic/versions/005_add_oidc_auth_providers.py` — Migration (auth_providers table, oidc_* columns on auth_users)
- `backend/app/api/oidc.py` — OIDC client (discovery, JWKS, token exchange, ID token verification)
- `backend/app/api/routes/auth_providers.py` — CRUD for providers (gated by `require_admin`)
- `backend/app/api/routes/oidc_auth.py` — Login/callback/test endpoints
- `backend/app/api/auth.py` — Added `require_admin` dependency

**Routes:**
- `GET /api/v1/auth/oidc/providers` — Public, list enabled providers
- `POST /api/v1/auth/oidc/login` — Returns `{authorization_url, state}`
- `POST /api/v1/auth/oidc/callback` — Code exchange, user provisioning, JWT issuance
- `POST /api/v1/auth/oidc/test` — Admin-only discovery + JWKS test
- `POST /api/v1/auth/providers` — CRUD (requires `require_admin`)

**Security:** PKCE S256, state/nonce one-time use, ID token signature + claims validation, config encrypted at rest (Fernet), secrets masked in API responses.

### Frontend (PR-5 in progress)

**Files:**
- `ui/src/features/settings/components/OIDCProvidersSection.tsx` — Settings tab for provider management (PR-4 ✅)
- `ui/src/components/auth/LoginComponent.tsx` — Updated with OIDC providers (PR-5 in progress)
- `ui/src/components/auth/OIDCCallbackHandler.tsx` — New callback page (PR-5 in progress)

**Flow:**
1. User clicks "Sign in with [Keycloak]" on login page
2. `oidcLogin(providerId)` calls `POST /auth/oidc/login`
3. Redirect to IdP authorization URL (with PKCE, state, nonce)
4. User authenticates at IdP, redirected to `/auth/oidc/callback?code=...&state=...`
5. `OIDCCallbackHandler` calls `POST /auth/oidc/callback`
6. Backend verifies state, exchanges code, validates ID token, upserts user, issues Finna JWT
7. Client stores JWT in sessionStorage, navigates to dashboard

### Tests (Complete ✅)

**Files:**
- `tests/test_auth_providers.py` — CRUD endpoint tests (24 tests)
- `tests/test_oidc.py` — Client module unit tests (20 tests)
- `tests/test_oidc_auth_integration.py` — Integration tests for login/callback (11 tests)
- `tests/test_oidc_e2e.py` — End-to-end scenarios with mock OAuth2 server (5 scenarios)

All tests use mocked `httpx.AsyncClient` (no real network calls). Coverage: happy path, error cases, PKCE defense, concurrent sessions, state/nonce validation.

---

## Deployment Checklist

- [ ] Set `JWT_SECRET` and `ENCRYPTION_KEY` env vars
- [ ] Set `AUTO_MIGRATE=true` on first deploy (runs migration 005)
- [ ] Build API image: `docker build -f Dockerfile.api -t ghcr.io/acarmisc/finna-app/finops-api:v0.X.Y .`
- [ ] Push to registry: `docker push ghcr.io/acarmisc/finna-app/finops-api:v0.X.Y`
- [ ] Update GKE: `kubectl set image deployment/finops-api finops-api=ghcr.io/acarmisc/finna-app/finops-api:v0.X.Y`
- [ ] Verify: `GET /api/v1/healthz` returns 200
- [ ] Test: Create provider in Settings → sign in → verify JWT issued
- [ ] Merge PR-5, PR-6 to main after testing

---

## Known Constraints

1. **Multi-instance deployment:** In-memory state store (`_state_store` dict) means OIDC only works with single API replica. Deferred: `oidc_state` table for Redis/distributed cache.

2. **Token lifetime:** Uses Finna's `JWT_EXPIRATION_MINUTES` (default 60), not IdP token exp. Users re-authenticate when JWT expires.

3. **Email collision:** No auto-link if OIDC email matches password user. Manual merge required (prevents account takeover via IdP user enum).

4. **Refresh tokens:** Not in v1. Users re-authenticate on JWT expiry. v2 can add silent refresh via hidden iframe.

---

## Next Steps (In Order)

1. **Finish PR-5 (< 5 min):**
   - Add callback route to `ui/src/App.tsx`
   - Commit and merge to main

2. **Create PR-6 (< 10 min):**
   - Write `docs/oidc-setup.md` with provider walkthroughs
   - Update `README.md` auth section
   - Commit and merge to main

3. **Test end-to-end:**
   - Local: `docker-compose up`, create provider in Settings, sign in
   - Or: GKE staging with real Keycloak container

4. **Deploy to GKE:**
   - Follow deployment checklist above
   - Monitor for migration 005 to complete
   - Test provider creation + sign-in flow

5. **Post-deploy (v2):**
   - Implement `oidc_state` table for multi-replica
   - Add refresh token flow
   - Add audit logging (auth_audit table schema in OIDC-PLAN.md 3.3)
   - Add RP-initiated logout (end_session_endpoint)

---

## Files Modified This Session

### Backend
- `backend/app/api/auth.py` — Added `require_admin` dependency
- `backend/app/api/main.py` — Registered `oidc_auth`, `auth_providers` routers
- `backend/app/api/oidc.py` — New OIDC client module (421 lines)
- `backend/app/api/routes/auth_providers.py` — New provider CRUD (296 lines)
- `backend/app/api/routes/oidc_auth.py` — New login/callback routes (370 lines)
- `alembic/versions/005_add_oidc_auth_providers.py` — New migration (64 lines)

### Frontend
- `ui/src/features/settings/SettingsPage.tsx` — Import + render OIDCProvidersSection
- `ui/src/features/settings/components/OIDCProvidersSection.tsx` — New settings tab (300+ lines)
- `ui/src/components/auth/LoginComponent.tsx` — Add OIDC provider buttons
- `ui/src/components/auth/OIDCCallbackHandler.tsx` — New callback handler (43 lines)

### Tests
- `tests/test_auth_providers.py` — New (326 lines)
- `tests/test_oidc.py` — New (501 lines)
- `tests/test_oidc_auth_integration.py` — New (666 lines)
- `tests/test_oidc_e2e.py` — New (603 lines)

### Documentation
- `OIDC-PLAN.md` — Complete implementation spec (346 lines)

---

## Branches

- **main** — All merged PRs (1-4), secrets generated, ready for PR-5/6 merge
- **feat/oidc-pr5-login-page** — PR-5 work in progress (callback handler + LoginComponent updates staged, needs route registration + commit)
- **feat/oidc-pr4-settings-ui** — PR-4 branch (can be deleted, merged to main)

---

## Questions for Next Session

1. **Provider setup UI:** Is PR-4's OIDCProvidersSection sufficient, or do you want:
   - Standalone provider creation wizard (non-Settings flow)?
   - Onboarding guide for first-time setup?
   - In-app Keycloak quick-start container?

2. **Documentation:** Should `docs/oidc-setup.md` include:
   - Docker Compose for local Keycloak testing?
   - Video walkthrough links?
   - Troubleshooting matrix?

3. **Deployment:** When ready to deploy:
   - Staging (test OIDC flow) or production?
   - Real IdP (Keycloak, Okta) or mock for testing?

---

## Contact/Context

- **Last paused:** 2026-05-16, 76% token usage
- **Model:** Claude Haiku 4.5
- **Working directory:** `/Users/andrea/Projects/personal/finna-app`
- **Git user:** Fix Bot

---

**Status: Ready to merge PR-5 + PR-6 and deploy. No blockers.**
