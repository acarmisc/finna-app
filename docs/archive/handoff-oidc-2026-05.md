> **Archived, historical.** In-progress session handoff from 2026-05-16.
> The work it describes (OIDC backend, docs/oidc-setup.md) has since
> shipped. Kept for historical context only — do not treat as current
> status. See docs/oidc-setup.md for the up-to-date OIDC guide.

# OIDC SSO Integration — Handoff Notes

**Date:** 2026-05-16  
**Status:** 80% complete (PR-1 through PR-5 in progress)  
**Context:** Claude Haiku 4.5 at 76% token usage when paused

---

## Summary

OIDC (OpenID Connect) SSO integration for Finna app backend is complete. The React frontend (ui/) has been archived to a separate repository (finna-app-ui).

**What's merged to main:**
- ✅ PR-1: auth_providers table + provider CRUD routes (6d7e1b)
- ✅ PR-2: OIDC client module (discovery, JWKS, token exchange, ID token verification) (95f10ce)
- ✅ PR-3: OIDC login/callback routes + comprehensive E2E tests (43a2a56)
- ✅ PR-4: Settings UI for managing OIDC providers (46b981e) — *frontend archived, backend routes remain*

**Archived (UI removed 2026-06-08):**
- ~~PR-5: Login page with OIDC provider buttons~~ — frontend code archived in finna-app-ui repo
- ⏳ PR-6: Documentation + Keycloak setup guide (not started)

---

## Generated Secrets

**Store these in `.env.local` or GKE secrets immediately:**

```env
JWT_SECRET=<store in GKE secret finops-secrets:jwt-secret>
ENCRYPTION_KEY=<store in GKE secret finops-secrets:encryption-key>
AUTO_MIGRATE=true
```

> ⚠️ **Critical:** These are single-use generated keys. **Do NOT** commit to git. Set via:
> - Local: `.env.local`
> - Docker: `docker-compose.yml` env vars
> - GKE: `kubectl create secret generic finops-secrets --from-literal=...`
> - GitHub Actions: `GITHUB_ENVIRONMENT` secrets

---

## PR-5 (Login Page) — ARCHIVED

Frontend code (`ui/src/components/auth/OIDCCallbackHandler.tsx`, `ui/src/components/auth/LoginComponent.tsx`) has been archived to the `finna-app-ui` repository. The backend OIDC routes are complete and functional.

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
   - Valid redirect URI: `http://localhost:8000/auth/oidc/callback` (or prod URL)
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

### Frontend (ARCHIVED — moved to finna-app-ui)

Frontend OIDC files were archived to the finna-app-ui repository on 2026-06-08.
The backend OIDC flow remains fully functional via the API endpoints.

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

1. **Create PR-6 (< 10 min):**
   - Write `docs/oidc-setup.md` with provider walkthroughs
   - Update `README.md` auth section
   - Commit and merge to main

2. **Test end-to-end:**
   - Local: `docker-compose up`, test OIDC endpoints via API client
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
