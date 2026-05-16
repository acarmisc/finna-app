# OIDC SSO Integration — Implementation Plan

**Goal:** Add standards-compliant OpenID Connect login to Finna, configurable from the Settings UI, so the app can bind to Keycloak, Auth0, Okta, Azure AD, Google, or any spec-compliant IdP.

**Approach:** Authorization Code flow + PKCE. Configuration stored encrypted in `cloud_config`-style table. JWT validation against the provider's JWKS. Local `auth_users` rows are created/linked on first successful login via deterministic mapping from OIDC `sub` claim.

---

## Architecture overview

```
┌─────────┐      ┌─────────────┐      ┌───────────┐
│ Browser │ ──→  │  Finna API  │ ──→  │ OIDC IdP  │
└─────────┘      └─────────────┘      └───────────┘
     │                  │                    │
     │  1. GET /auth/oidc/login              │
     │  ───────────────→│                    │
     │                  │ Build authz URL    │
     │                  │ with PKCE+state    │
     │ ←────────────────│                    │
     │  2. Redirect to IdP authorize         │
     │  ─────────────────────────────────────→
     │  3. User logs in at IdP               │
     │                                       │
     │ ←─────────────────────────────────────│
     │  4. Redirect /auth/oidc/callback?code=…&state=…
     │  ───────────────→│                    │
     │                  │ Validate state     │
     │                  │ Exchange code      │
     │                  │  ─────────────────→│
     │                  │ ←─────────────────│ id_token + access_token
     │                  │ Verify id_token via JWKS
     │                  │ Upsert auth_users  │
     │                  │ Issue Finna JWT    │
     │ ←────────────────│                    │
     │  5. {token: …}                        │
```

---

## Phase 1 — Backend foundation (3-4 hours)

### 1.1 Dependencies

Add to `pyproject.toml`:
```toml
"authlib>=1.3",            # OIDC client (well-maintained, spec-compliant)
"httpx>=0.27",             # already present, for JWKS fetch
"cryptography>=42.0",      # already present, for ID token verification
```

Why `authlib` over rolling our own: it handles JWKS rotation, `id_token` validation, nonce/state, PKCE, and all the spec edge cases (mismatched issuer, expired keys, alg confusion attacks). Battle-tested.

### 1.2 Storage: new `auth_providers` table

`alembic/versions/00X_add_auth_providers.py`:
```sql
CREATE TABLE auth_providers (
    id           UUID PRIMARY KEY,
    name         TEXT NOT NULL,             -- "Keycloak prod", "Okta corp"
    kind         TEXT NOT NULL,             -- 'oidc'
    enabled      BOOLEAN NOT NULL DEFAULT false,
    config       BYTEA NOT NULL,            -- encrypted JSON (see schema below)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by   TEXT,
    last_test_at TIMESTAMPTZ,
    last_test_ok BOOLEAN
);
CREATE UNIQUE INDEX auth_providers_name_idx ON auth_providers (lower(name));

-- Add OIDC fields to auth_users
ALTER TABLE auth_users
    ADD COLUMN oidc_provider_id UUID REFERENCES auth_providers(id),
    ADD COLUMN oidc_subject     TEXT,
    ADD COLUMN oidc_claims      JSONB DEFAULT '{}'::jsonb;
CREATE UNIQUE INDEX auth_users_oidc_idx
    ON auth_users (oidc_provider_id, oidc_subject)
    WHERE oidc_subject IS NOT NULL;
```

**Encrypted config JSON schema:**
```json
{
  "issuer": "https://keycloak.example.com/realms/finna",
  "client_id": "finna-app",
  "client_secret": "…",
  "redirect_uri": "https://finna.example.com/api/v1/auth/oidc/callback",
  "scopes": ["openid", "profile", "email"],
  "claim_mappings": {
    "username": "preferred_username",
    "email": "email",
    "is_admin": {"claim": "groups", "match": "finna-admins"}
  },
  "auto_provision": true,
  "allowed_email_domains": ["example.com"]
}
```

Reuse existing `utils/encryption.encrypt_config` / `decrypt_config`. Add `_mask_secrets` allow-list for `auth_providers.config` so `client_secret` never leaks via API responses (apply lessons from P0.5 fix).

### 1.3 OIDC client module — `backend/app/api/oidc.py`

```python
# Public surface
async def discover_provider(issuer: str) -> ProviderMetadata
    # GET {issuer}/.well-known/openid-configuration
    # Cache with TTL 1h. Validates required endpoints.

async def get_jwks(provider_id: UUID) -> JWKSet
    # Fetch + cache JWKS from metadata.jwks_uri. TTL 5min.

def build_authorization_url(provider, state, nonce, code_challenge) -> str
async def exchange_code(provider, code, code_verifier) -> TokenResponse
async def verify_id_token(provider, id_token, nonce) -> Claims
async def fetch_userinfo(provider, access_token) -> Claims  # optional
```

**Security requirements (non-negotiable):**
- PKCE S256 always (even for confidential clients — defense in depth).
- `state` and `nonce` generated with `secrets.token_urlsafe(32)`, stored server-side with 10-min TTL, single-use.
- Validate ID token: signature via JWKS, `iss` exact match, `aud` exact match, `exp` not expired, `iat` not far future, `nonce` matches.
- Reject `alg: none` and HS* if JWKS only has RS*/ES*.
- Strict redirect_uri match — no wildcards, no path traversal.

### 1.4 Routes — `backend/app/api/routes/oidc_auth.py`

```
GET  /api/v1/auth/oidc/providers             # list enabled providers (public, no secrets)
GET  /api/v1/auth/oidc/login?provider_id=X   # returns {authorization_url, state}
POST /api/v1/auth/oidc/callback              # body: {provider_id, code, state}
POST /api/v1/auth/oidc/test                  # admin-only, validate config end-to-end
```

Rate-limit `login` and `callback` with the in-memory limiter built in P1.1 (10/min per IP).

**Callback logic:**
1. Validate `state` (consume, reject if missing/expired/used).
2. Exchange `code` for tokens via `exchange_code`.
3. Verify `id_token` claims. Reject on any mismatch.
4. Look up `auth_users` by `(oidc_provider_id, oidc_subject)`.
5. If not found and `auto_provision: true`:
   - Apply `allowed_email_domains` gate.
   - Insert new `auth_users` row with mapped claims. Default `is_admin=false`.
6. Else if not found and `auto_provision: false`: 403 with "User not provisioned. Contact admin."
7. Re-apply `claim_mappings.is_admin` rule on each login (so group changes in IdP propagate).
8. Issue Finna JWT exactly as today's `/auth/token`. Same JWT, same expiry.

### 1.5 Provider CRUD — `backend/app/api/routes/auth_providers.py`

```
GET    /api/v1/auth/providers              # admin-only, masked secrets
POST   /api/v1/auth/providers              # admin-only, create+encrypt
PUT    /api/v1/auth/providers/{id}         # admin-only
DELETE /api/v1/auth/providers/{id}         # admin-only, reject if users linked
POST   /api/v1/auth/providers/{id}/test    # admin-only, dry-run discovery + JWKS fetch
```

All gated behind `Depends(require_admin)` (from P1.3).

### 1.6 Testing

`tests/test_oidc.py`:
- Mock IdP discovery endpoint with `httpx.MockTransport`.
- Fixture: ephemeral RSA keypair → sign test ID tokens → mock JWKS endpoint.
- Tests:
  - Happy path: discovery → authz URL build → callback → JWT issued.
  - State tampering rejected.
  - Nonce mismatch rejected.
  - Expired ID token rejected.
  - Wrong `iss` rejected.
  - Wrong `aud` rejected.
  - `alg: none` rejected.
  - JWKS rotation (kid mismatch → refetch).
  - `auto_provision=false` blocks new user.
  - `allowed_email_domains` enforced.
  - `claim_mappings.is_admin` group match works.
  - Re-login updates is_admin if IdP group changed.

---

## Phase 2 — Frontend: Settings UI (2-3 hours)

### 2.1 Settings page: new "Authentication" tab

`ui/src/features/settings/components/OIDCProvidersSection.tsx`:

**List view:**
| Name | Issuer | Status | Last test | Actions |
|------|--------|--------|-----------|---------|
| Keycloak prod | https://kc.example.com/realms/finna | ● Enabled | 2 min ago ✓ | [Test] [Edit] [Disable] [Delete] |

**Add/edit modal:**
- Name (required)
- **Quick-fill dropdown:** Keycloak / Okta / Auth0 / Azure AD / Google / Custom
  - Each preset fills issuer URL template, scopes, claim mappings
- Issuer URL (required, validated against `^https://`)
- Client ID (required)
- Client Secret (required, write-only field — empty input means "keep existing")
- Redirect URI (auto-filled from current origin, copyable, with one-click "copy for IdP setup")
- Scopes (chips, default `openid profile email`)
- Claim mappings (collapsible advanced section)
  - Username claim (default `preferred_username`)
  - Email claim (default `email`)
  - Admin rule: claim name + match value (e.g., `groups` contains `finna-admins`)
- Auto-provision users (toggle, default off)
- Allowed email domains (chips, optional)

**Discovery validation:**
- Live "Test discovery" button that hits `POST /auth/providers/test` with the issuer URL alone — shows which endpoints were discovered and whether JWKS is reachable, before saving.

**Test button:**
- "Test login" → opens `authorization_url` in a popup → user authenticates → callback closes popup → success/failure shown inline. No JWT issued during test.

### 2.2 Login page changes

`ui/src/features/auth/LoginPage.tsx`:
- Below username/password form: "or sign in with" divider.
- Render `<ProviderButton>` per enabled provider from `GET /auth/oidc/providers`.
- Click → call `GET /auth/oidc/login` → redirect browser to returned `authorization_url`.

### 2.3 Callback handler

`ui/src/features/auth/OIDCCallbackPage.tsx` mounted at `/auth/oidc/callback`:
- Parse `code` and `state` from query string.
- POST to `/api/v1/auth/oidc/callback`.
- On success: store JWT (use the single storage chosen in QUAL MED-21 — `sessionStorage` recommended), navigate to dashboard.
- On error: redirect to `/login?error=oidc_failed&detail=…` with non-leaky message.

### 2.4 TypeScript types

Generate from OpenAPI:
```bash
npx openapi-typescript http://localhost:8000/openapi.json -o ui/src/types/api.ts
```
Hand-write `OIDCProvider`, `OIDCProviderInput`, `OIDCLoginResponse` until the generator picks up the new routes.

### 2.5 Frontend tests

- Vitest: form validation (issuer must be https, name required).
- Vitest: redirect URI auto-populates and is read-only.
- Playwright: full login flow against a mock IdP container (use the `mock-oauth2-server` image — drops into docker-compose for test profile only).

---

## Phase 3 — Operational concerns (1-2 hours)

### 3.1 Multi-instance state store

Phase 1 uses in-memory dicts for state/nonce — same constraint as P1.2's OAuth state. For multi-replica deploys this breaks.

**Mitigation path (deferred but documented):**
- Add `oidc_state` table: `(state PK, provider_id, nonce, code_verifier, expires_at)`.
- Cleanup job: `DELETE WHERE expires_at < now()` on a 5-minute schedule (use `apscheduler`, already a viable add).
- Or swap to Redis later — same interface.

**Acceptance:** for now, document "single API replica required for OIDC until oidc_state table lands." Add to README.

### 3.2 Logout / session

Add `POST /api/v1/auth/logout` that:
- Invalidates the Finna JWT (token blacklist? or rely on short expiry — see "JWT_EXPIRATION_MINUTES").
- If provider supports RP-initiated logout (`end_session_endpoint` in discovery), construct logout URL and return to client.

Out of scope for v1: front-channel and back-channel logout. v1 is best-effort logout.

### 3.3 Audit logging

Log to a new `auth_audit` table:
- provider_id, user_id, action (login/logout/login_failed/provision), ip, user_agent, ts, error_code.
- Surface in admin UI under Settings → Audit.

Useful for compliance and "who provisioned this account?" debugging.

### 3.4 Migration / backout

- Feature flag: `OIDC_ENABLED=true` env var gates the routes and Settings section.
- No data loss if disabled: existing users with `hashed_password` still log in via `/auth/token`.
- Two auth paths can coexist indefinitely.

---

## Phase 4 — Documentation (1 hour)

- `docs/oidc-setup.md`:
  - Keycloak walkthrough: realm → client → mapper → roles.
  - Okta walkthrough.
  - Azure AD walkthrough.
  - Troubleshooting matrix: most common errors and root cause.
- Update `README.md` Authentication section.
- Update `docs/openapi.yaml` with new routes.

---

## Test plan (acceptance)

End-to-end against real Keycloak in a CI container:
1. Bring up `quay.io/keycloak/keycloak:25` in docker-compose.test.yml with seeded realm.
2. Admin creates OIDC provider in Settings UI pointing at the Keycloak realm.
3. Click "Test discovery" → green.
4. Click "Test login" → popup → enter test user → success.
5. Log out, click "Sign in with Keycloak" on login page → land on dashboard as test user.
6. Verify `auth_users` row created with correct `oidc_subject`.
7. Add user to `finna-admins` group in Keycloak → re-login → `is_admin=true` in JWT.
8. Disable provider → login button disappears, callback returns 403.
9. Delete provider with linked user → 409 (must reassign users first).

---

## Effort & sequencing

| Phase | Effort | Depends on |
|-------|--------|------------|
| 1 — Backend | 3-4h | nothing |
| 2 — Frontend | 2-3h | Phase 1.5 (provider CRUD) |
| 3 — Ops | 1-2h | Phase 1 |
| 4 — Docs | 1h | Phase 1, 2 |
| **Total** | **7-10h** | one focused day |

### Suggested commit / PR sequence

1. **PR-1 — Migration + provider CRUD:** `auth_providers` table, alembic migration, CRUD routes with `require_admin`, encrypted config, tests for CRUD only.
2. **PR-2 — OIDC client:** `oidc.py` module with discovery, JWKS, token exchange, ID token validation. Unit tests with mocked IdP. No routes yet.
3. **PR-3 — OIDC routes:** `/auth/oidc/login` + `/auth/oidc/callback`, integration with `auth_users` upsert, rate limiting, audit logging. End-to-end tests against `mock-oauth2-server`.
4. **PR-4 — Settings UI:** OIDCProvidersSection component, form, test buttons. Vitest coverage.
5. **PR-5 — Login UI + callback page:** provider buttons on login, callback handler.
6. **PR-6 — Docs + Keycloak walkthrough:** `docs/oidc-setup.md`, README update, OpenAPI spec.

Each PR is independently mergeable. PR-3 is the riskiest — gate it behind `OIDC_ENABLED=false` until verified in staging.

---

## Open decisions to lock before coding

1. **Single provider at a time vs. multiple enabled simultaneously?**
   - Recommendation: support multiple enabled. UI shows one button per provider. Cost is low, adds Keycloak-dev + Okta-prod scenarios.
2. **What happens if an OIDC user's email collides with an existing password user?**
   - Recommendation: by default, do NOT auto-link. Force admin to manually merge accounts. Auto-link is dangerous (account takeover via IdP user enum).
3. **Token lifetime — match IdP `exp` or use Finna's `JWT_EXPIRATION_MINUTES`?**
   - Recommendation: use Finna's. ID token is consumed once at login; the session token is ours.
4. **Refresh tokens?**
   - Recommendation: v1 = no refresh. User re-authenticates when Finna JWT expires (default 60min). v2 can add silent refresh via hidden iframe + prompt=none if needed.
5. **Where does redirect_uri point during local dev?**
   - Recommendation: `http://localhost:5173/auth/oidc/callback` for SPA, proxy to API. Document both.

Lock these before writing the migration so the schema and routes don't need rework.
