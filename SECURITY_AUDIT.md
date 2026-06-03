# Finna-App Pre-Go-Live Security & Quality Audit

**Date:** 2026-06-02
**Auditor:** Senior architect pass (Claude Opus 4.7)
**Repo:** `/Users/andrea/Projects/personal/finna-app` @ `main` (commit `87edeea`)
**Scope:** Backend (FastAPI/Python 3.11), Extractors, UI (React/Vite/TS), Docker/compose, dependency supply chain.
**Goal:** Identify everything that blocks safe production launch with minimum operator configuration burden.

---

## 0. How To Reproduce

All tools run from repo root unless noted. Outputs cached in `/tmp/*-finna.{json,output}`.

```bash
# Python dependencies
pip-audit --skip-editable

# Static analysis (SAST)
semgrep --config=auto --json -q --timeout=60 backend extractors config utils models \
  > /tmp/semgrep-finna.json
snyk code test --json-file-output=/tmp/snyk-finna.json .

# Lint
ruff check --output-format=json . > /tmp/ruff-finna.json

# JS dependencies
( cd ui && npm audit --json > /tmp/npm-audit-finna.json )

# Secret/cred file scan
git check-ignore azure-sp.txt gcp-sa.json   # ← currently NOT ignored
grep -rEn "BEGIN (RSA |EC )?PRIVATE KEY|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}" \
  --exclude-dir=node_modules --exclude-dir=.venv .
```

Tools verified installed: `snyk`, `semgrep`, `pip-audit`, `ruff`, `npm`.
Not installed (recommended to add later): `gitleaks`, `trivy`, `bandit`.

---

## 1. Executive Summary — Go-Live Priority Stack

Ordered by blast radius × ease-of-fix. Top items MUST clear before any internet-exposed deploy.

| # | Severity | Issue | Effort | Blocks Launch? |
|---|---|---|---|---|
| 1 | 🔴 **CRITICAL** | Live Azure SP secret + GCP service-account JSON sitting on disk in repo root, NOT in `.dockerignore` → will be baked into the Docker image | XS | **YES — rotate now** |
| 2 | 🔴 **CRITICAL** | `docker-compose.yml` ships hardcoded `JWT_SECRET`, `ENCRYPTION_KEY`, DB password, and `ALLOWED_ORIGINS="*"` — if anyone copies this to prod it's instant takeover | XS | **YES** |
| 3 | 🔴 **CRITICAL** | Python deps with known CVEs: `pyjwt 2.12.1` (4 advisories), `starlette 0.38.6` (3 incl. CVE-2024-47874), `urllib3`, `idna`, `requests` | S | **YES** |
| 4 | 🔴 **CRITICAL** | UI deps: 6 npm vulns, 4 **critical** (vitest browser RCE-class, axios DoS/header-injection) | S | YES for CI/dev; not runtime if devDeps only — verify |
| 5 | 🟠 **HIGH** | SQL string interpolation in `extractors/{aws,azure,litellm}_cost.py` (5 sites flagged by Semgrep `sqlalchemy-execute-raw-query`) | S–M | YES if `table`/inputs reach users |
| 6 | 🟠 **HIGH** | No rate limiting active despite `slowapi` dependency — `/auth/token`, `/oidc/*` exposed to brute force | S | YES |
| 7 | 🟠 **HIGH** | UI stores JWT in `localStorage` (XSS-exfiltratable) — multiple call sites | M | Strong recommend before launch |
| 8 | 🟠 **HIGH** | Dynamic `importlib.import_module()` in `extractors/entrypoint.py:55` + `subprocess.Popen` with `extractor_type` derived from API input in `runner.py:206` | M | YES — validate against allowlist |
| 9 | 🟡 **MED** | `xml.etree.ElementTree.fromstring` in `extractors/exchange_rates.py:93` (XXE on Python ≤3.10; runtime is 3.11 so OK, but switch to `defusedxml` anyway) | XS | No |
| 10 | 🟡 **MED** | OIDC `redirect_uri`/`window.location` flows tainted (Snyk Open Redirect, `LoginComponent.tsx:96,121`) | S | YES |
| 11 | 🟡 **MED** | `USERS_TABLE` in-memory demo dict with `password_hash="placeholder"` still present in `backend/app/api/auth.py:32` | XS | YES — delete |
| 12 | 🟡 **MED** | No `TrustedHostMiddleware` / `HTTPSRedirectMiddleware` / security headers (CSP, HSTS, X-Frame-Options) | S | Recommend |
| 13 | 🟢 **LOW** | 70 ruff findings (31× F401 unused imports, 25× I001 import order, 5× F841, etc.) | XS | No |
| 14 | 🟢 **LOW** | 4× Prototype-pollution-shaped patterns in `ui/src/pages/CostsPage.tsx:74-85` (low exploitability, false-positive-prone) | S | Review |

**Minimum viable go-live checklist (≤1 day of work):**
1. Rotate the two leaked credentials (items #1) + delete the files + add to `.gitignore` and `.dockerignore`.
2. Strip secrets from `docker-compose.yml`, switch to `.env` with a `.env.example` template (item #2).
3. Bump `pyjwt`, `starlette`, `urllib3`, `idna`, `requests` to fixed versions (item #3).
4. Run `npm audit fix` in `ui/` and verify `vitest`/`@vitest/browser` are devDeps only (item #4).
5. Parametrize the 5 raw-SQL calls or whitelist the `table` identifier (item #5).
6. Wire `slowapi` into `auth.py` routes (item #6).
7. Delete `USERS_TABLE` placeholder (item #11).
8. Validate `extractor_type` against the fixed mapping in `runner.py:_get_extractor_type` (item #8).

Items #7, #10, #12 should follow within a week of launch but are not absolute blockers if the audience is internal/auth'd only.

---

## 2. Critical Findings — Detail

### 2.1 🔴 Leaked Cloud Credentials On Disk (untracked but present)

```
/Users/andrea/Projects/personal/finna-app/azure-sp.txt
  name:           ces-cost-reader-sp
  secret value:   [REDACTED — rotate at Azure portal]
  application id: [REDACTED]
  tenant id:      [REDACTED]

/Users/andrea/Projects/personal/finna-app/gcp-sa.json
  type:        service_account
  project_id:  [REDACTED]
  private_key: [REDACTED — rotate at GCP IAM]
```

- `git ls-files` → not in history (good).
- `.gitignore` → does NOT list these (bad).
- `.dockerignore` → does NOT list these. **Any `docker build -f Dockerfile.api .` will COPY them into the build context and possibly the final image.** Verify with `docker history <image>` after a build.

**Actions (must be done before any further `git push` or `docker build`):**
1. **Rotate both credentials** (Azure portal → delete that client secret; GCP IAM → disable & delete the SA key).
2. `rm azure-sp.txt gcp-sa.json`.
3. Append to `.gitignore` and `.dockerignore`:
   ```
   *.sp.txt
   *-sa.json
   gcp-sa*.json
   azure-sp*.txt
   credentials/
   ```
4. Audit `docs/`, `data/`, `gap-analysis/` for any other dumps (grep ran clean except for `gcp-sa.json` itself).

### 2.2 🔴 Hardcoded Secrets In `docker-compose.yml`

`docker-compose.yml:13-15`:
```yaml
JWT_SECRET: "dev-secret-key-change-in-production"
ENCRYPTION_KEY: "dev-key-change-in-production"
ALLOWED_ORIGINS: "*"
POSTGRES_PASSWORD: finops_dev
```

`backend/app/api/main.py:50` actually rejects `*` at startup (good), so launching with these will crash — but the *secrets* themselves are still trivially copy-pasted into production. Move all of them to `.env` and create a minimal `.env.example`. Add an `entrypoint` check that fails fast if `JWT_SECRET` length < 32 or matches the dev string. (`JWT_SECRET` already enforced as required in `backend/app/api/auth.py:15-17`; the encryption key is not.)

### 2.3 🔴 Vulnerable Python Dependencies (`pip-audit --skip-editable`)

```
gdal      3.12.4   → 3.13.0    (CVE-2026-8087/8088/8212)
idna      3.11     → 3.15      (CVE-2026-45409)
pyjwt     2.12.1   → 2.13.0    (PYSEC-2026-175/177/178/179) ← auth-critical
requests  2.32.5   → 2.33.0    (CVE-2026-25645)
starlette 0.38.6   → 0.47.2    (CVE-2024-47874, CVE-2025-54121, PYSEC-2026-161) ← runtime
urllib3   2.6.3    → 2.7.0     (PYSEC-2026-141/142)
```

`starlette` and `pyjwt` are in the request/auth hot path — non-negotiable upgrades.
Update `pyproject.toml` pins, run `uv lock`, regenerate, re-test.

### 2.4 🔴 Vulnerable JS Dependencies (`ui/npm audit`)

```
critical  vitest, @vitest/browser, @vitest/browser-playwright, @vitest/coverage-v8
          → "Vitest browser mode serves unsanitized otelCarrier ... inline script"
high      axios → IPv4-mapped IPv6 NO_PROXY bypass + Proto-Pollution DoS/Header-Injection
moderate  ws    → uninit memory disclosure
```

`axios` is in app runtime — bump it. The `vitest` family is dev/test only; confirm `package.json` puts them in `devDependencies` and that prod nginx image (`ui/Dockerfile`) does `npm ci --omit=dev` for the runtime stage.

### 2.5 🟠 SQL Injection Surface

Semgrep flagged 5 raw-SQL sites, all of the same shape:

```
extractors/aws_cost.py:232      cur.execute(f"SELECT currency, rate_to_usd FROM {table}")
extractors/azure_cost.py:266    cur.execute(f"SELECT ... FROM {table}")
extractors/litellm_cost.py:367  (same pattern)
extractors/litellm_cost.py:389
extractors/litellm_cost.py:412
```

`# noqa: S608 — validated via allowlist` is asserted in `azure_cost.py` but the allowlist is not visible at the call site. Action: enforce an explicit `ALLOWED_FX_TABLES = {"fx_rates", ...}` and `assert table in ALLOWED_FX_TABLES` *immediately above each call*. Same pattern for litellm. If table identifiers must be dynamic, use `psycopg.sql.Identifier(...)` instead of f-strings.

### 2.6 🟠 No Rate Limiting

`slowapi` is a declared dependency in `pyproject.toml` but `grep -rn "slowapi\|@limiter\|Limiter" backend` returns nothing — not wired up. `POST /api/v1/auth/token`, `/oidc/*`, GitHub OAuth callback are all unauthenticated entry points open to credential stuffing / replay. Add:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
# then on auth endpoints:
@limiter.limit("5/minute")
```

### 2.7 🟠 UI Token Storage In `localStorage`

7+ call sites read `localStorage.getItem('finna_token')` (see `ui/src/pages/*`, `ui/src/features/settings/components/OIDCProvidersSection.tsx`). Any XSS = token theft. Migration target: HttpOnly cookie + CSRF token, or in-memory store with silent refresh.
- Short term (before launch, if scope-bound): enable a strict CSP (`script-src 'self'`, no inline) in `ui/nginx.conf` and audit React renderings of user input. The Snyk OR (Open Redirect) findings in `LoginComponent.tsx:96,121` also become higher-impact while tokens live in `localStorage`.

### 2.8 🟠 Dynamic Module Import + Subprocess With API-Influenced Name

`backend/app/api/runner.py:182,206`:
```python
extractor_type = _get_extractor_type(extractor_type or provider)
cmd = [sys.executable, "-m", f"extractors.{extractor_type}"]
```

`_get_extractor_type` falls back to the raw `provider` string when not in its mapping (`runner.py:65`). If `provider` reaches `start_extractor` from an API payload without server-side allowlisting, an attacker can pick any importable `extractors.X` module. Combined with `extractors/entrypoint.py:55` `importlib.import_module(user_value)` (Semgrep `non-literal-import` finding), this is a code-loading primitive — not yet RCE because there's no attacker-controlled module on disk, but it's one ill-advised refactor away.

Fix: hard allowlist before subprocess:

```python
ALLOWED_EXTRACTORS = {"azure_cost","gcp_billing","aws_cost","litellm_cost"}
if extractor_type not in ALLOWED_EXTRACTORS:
    raise HTTPException(400, "unknown extractor")
```

### 2.9 🟡 Logger Credential Disclosure (4 sites, Semgrep WARN)

```
config/auth.py:37,101,109   logger.info("Using ... tenant=%s client=%s", ...)
extractors/azure_cost.py:432 "Pagination ... token %s"
```

These format strings include identifiers that *can* be sensitive (tenant_id, continuation_token). `backend/app/api/runner.py:44` already redacts `client_secret=` — extend that redaction to logger formatters globally and confirm logs don't leak to a public sink (Loki/CloudWatch/stdout-shipped-to-vendor).

### 2.10 🟡 OIDC / Login Open Redirect

`ui/src/components/auth/LoginComponent.tsx:96,121` — Snyk reports remote-data flowing into `window.location` without sanitization. Validate `redirect_uri` against an allowlist of trusted origins.

### 2.11 🟡 Demo User Table Still Present

`backend/app/api/auth.py:32-38`:
```python
USERS_TABLE = {"admin": {"password_hash":"placeholder",...}}
```

The real auth path uses Postgres (`backend/app/api/routes/auth.py:34`), so this dict is dead code — but if any future endpoint references it by mistake, it's a backdoor. Delete it.

### 2.12 🟡 Missing Hardening Middleware

No `TrustedHostMiddleware`, no `HTTPSRedirectMiddleware`, no Secure-Headers middleware (CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy). Add a small middleware that emits these for production env.

---

## 3. Tool-By-Tool Inventory

### 3.1 Semgrep (`--config=auto`, 13 findings)

| Severity | Rule | Count |
|---|---|---|
| ERROR | `sqlalchemy-execute-raw-query` | 5 |
| WARNING | `python-logger-credential-disclosure` | 4 |
| WARNING | `formatted-sql-query` | 2 |
| WARNING | `non-literal-import` | 1 |
| WARNING | `dynamic-urllib-use-detected` | 1 |

`dynamic-urllib-use-detected` at `extractors/exchange_rates.py:81` — `urllib` accepts `file://`; ensure the URL is constructed from a trusted config value, not from user input or remote-loaded config.

### 3.2 Snyk Code (22 findings: 3 high / 7 med / 12 low)

| Severity | Rule | Sites |
|---|---|---|
| HIGH | `javascript/HardcodedNonCryptoSecret` | 3 (incl. real-looking string in `ui/src/pages/ConfigCreatePage.tsx:220` — review) |
| MED | `javascript/OR` (Open Redirect) | 2 (`LoginComponent.tsx:96,121`) |
| MED | `javascript/PrototypePollution` | 4 (`CostsPage.tsx:74-85`) |
| MED | `python/InsecureXmlParser` | 1 (`exchange_rates.py:93`) — runtime is 3.11 so low impact; still use `defusedxml.ElementTree` |
| LOW | `python/HardcodedNonCryptoSecret/test` | 10 (all in `tests/` — test fixtures, mostly benign, but `tests/test_oidc.py:231` is worth eyeballing) |
| LOW | `python/NoHardcodedPasswords/test` | 2 (test_api_integration.py) |

### 3.3 pip-audit — 14 vulns / 6 packages (detail in §2.3)

### 3.4 npm audit — 6 vulns (4 critical / 1 high / 1 moderate) (detail in §2.4)

### 3.5 Ruff — 70 findings (none security-class)

| Code | Count | Meaning |
|---|---|---|
| F401 | 31 | unused imports |
| I001 | 25 | import order |
| E501 | 5 | line too long |
| F841 | 5 | unused local |
| E402 | 3 | import-not-at-top |
| F541 | 1 | f-string without placeholders |

Auto-fix with `ruff check --fix .`. Zero-risk cleanup.

---

## 4. Architecture & Deployment Observations

- **Single repo** mixes API, extractors, UI, alembic, superset, k8s manifests, deploy scripts. Acceptable for go-live; document layout in `README.md`.
- **Dockerfile.api** uses Python 3.14-slim + Node 26-alpine — both are bleeding edge / pre-release for the cutoff date. Pin to Python 3.12 LTS-track and Node 22 LTS to reduce supply-chain surprises and image-pull breakage.
- **docker-compose** binds Postgres on host port `5434` and DB middleware now returns 503 on pool failure (recent commit `01ba70e`) — good, keep.
- **AUTO_MIGRATE=true** in compose. Fine for dev, must be `false` (or behind a flag) in prod; otherwise an accidental restart with mismatched code/DB can mass-migrate.
- **Healthcheck** present for Postgres; no healthcheck on `api` or `ui` services. Add `HEALTHCHECK` in Dockerfile.api / compose for orchestrator readiness.
- **No CI security gates visible** — recommend adding a GH Action that runs `pip-audit --strict`, `npm audit --omit=dev --audit-level=high`, `semgrep ci`, and `ruff check`. Hard-fail the build on regressions.
- **CHANGELOG / docs sprawl**: 9 top-level `*.md` planning files (ACTION-PLAN, GAP-ANALYSIS, STATUS_UPDATE, ...). Consolidate into `docs/` to keep root clean for operators.

---

## 5. Recommended Operator UX (because launch must be teach-light)

Aim: a new operator should be productive in `< 10 minutes` with one command.

1. Provide a single `.env.example` at repo root listing every variable consumed by `docker-compose.yml` and the API (today: `JWT_SECRET`, `ENCRYPTION_KEY`, `PG_DSN`, `ALLOWED_ORIGINS`, OIDC vars, `GITHUB_CLIENT_ID/SECRET`). Compose already reads env files by default.
2. Add a `make bootstrap` (or `./scripts/bootstrap.sh`) that:
   - generates `JWT_SECRET` and `ENCRYPTION_KEY` via `python -c "import secrets; print(secrets.token_urlsafe(48))"`,
   - writes them to `.env` if missing,
   - runs `docker compose up -d` and waits for `/healthz`.
3. Fail-fast preflight in `backend/app/api/main.py`:
   ```python
   if JWT_SECRET == "dev-secret-key-change-in-production" or len(JWT_SECRET) < 32:
       raise RuntimeError("JWT_SECRET is unsafe")
   ```
4. `README.md` "Production Launch" section: 6 bullets max, copy-pasteable.

---

## 6. Agent Fan-Out Plan (for follow-up `/gsd-execute` or task runners)

Suggested one-shot agent assignments, each scoped tight enough for an atomic commit:

| Agent | Task | Files |
|---|---|---|
| **secrets-rotator** | Delete `azure-sp.txt` + `gcp-sa.json`, add gitignore/dockerignore entries, document rotation in `SECURITY.md` | `.gitignore`, `.dockerignore`, root |
| **compose-hardener** | Replace inline secrets in `docker-compose.yml` with `${VAR}` refs, add `.env.example`, add startup secret validation | `docker-compose.yml`, `.env.example`, `backend/app/api/main.py` |
| **dep-bumper-py** | Bump pyjwt → 2.13.0+, starlette → 0.47.2+, urllib3 → 2.7.0+, idna → 3.15+, requests → 2.33.0+; regen lockfile; run tests | `pyproject.toml`, `uv.lock` |
| **dep-bumper-js** | `npm audit fix`; verify vitest is dev-only; pin axios to ≥ patched version | `ui/package.json`, `ui/package-lock.json` |
| **sql-injection-fixer** | Replace f-string SQL with allowlist + `psycopg.sql.Identifier` | `extractors/{aws,azure,litellm}_cost.py` |
| **rate-limiter** | Wire `slowapi` into `auth.py`, `oidc_auth.py`, `auth_providers.py`. 5/min on token endpoints, 100/min global | `backend/app/api/main.py`, `backend/app/api/routes/auth.py`, `backend/app/api/routes/oidc_auth.py` |
| **extractor-allowlister** | Hard allowlist in `runner.py` + `entrypoint.py`; reject unknown extractor types with 400 | `backend/app/api/runner.py`, `extractors/entrypoint.py` |
| **dead-auth-remover** | Delete `USERS_TABLE` from `backend/app/api/auth.py`; verify no references | `backend/app/api/auth.py` |
| **xml-defuser** | Swap `xml.etree.ElementTree` → `defusedxml.ElementTree` in `exchange_rates.py` | `extractors/exchange_rates.py`, `pyproject.toml` |
| **open-redirect-fixer** | Allowlist `redirect_uri` in `LoginComponent.tsx` and OIDC callback | `ui/src/components/auth/LoginComponent.tsx`, OIDC route |
| **ui-token-migrator** | Move JWT to HttpOnly cookie + add CSRF + adapt `ui/src/api/client.ts`; transition path documented | `ui/src/api/client.ts`, all `localStorage.getItem('finna_token')` sites, `backend/app/api/routes/auth.py` |
| **security-headers** | Add CSP/HSTS/XFO middleware + nginx headers | `backend/app/api/main.py`, `ui/nginx.conf` |
| **ruff-cleanup** | `ruff check --fix .` + commit | repo-wide |
| **ci-gates** | GitHub Actions workflow: pip-audit, npm audit (omit-dev, high+), semgrep ci, ruff, pytest | `.github/workflows/security.yml` |
| **dockerfile-pinner** | Pin Python to 3.12-slim, Node to 22-alpine; add HEALTHCHECK | `Dockerfile.api`, `ui/Dockerfile` |

Sequence the first 8 before launch. Items 9–15 are post-launch hardening within 1–2 weeks.

---

## 7. What This Audit Did NOT Cover (recommend next pass)

- Container image scan (need `trivy image finna-api:latest` after a real build).
- Git history scan (`gitleaks detect --source . --log-opts="--all"`) — quick sample said clean, but full scan recommended.
- IaC scan (`checkov` / `tfsec` on `deploy/k8s/`).
- License compliance for transitive deps.
- DAST against the running API (OWASP ZAP baseline).
- Threat model for multi-tenant case (current code assumes single-org).
- Backup/restore + key-rotation runbook for `ENCRYPTION_KEY` (rotating it without a re-encrypt path will brick stored secrets).

---

*End of audit. Hand each row of §6 to its own agent; track in `.planning/` if using gstack.*
