# Finna-App — Code Review Action Plan

**Date:** 2026-05-16
**Sources:** [`SECURITY-REVIEW.md`](./SECURITY-REVIEW.md) (11 CRITICAL, 12 HIGH, 13 MEDIUM, 7 LOW, 4 INFO) · [`QUALITY-REVIEW.md`](./QUALITY-REVIEW.md) (9 HIGH, 28 MEDIUM, 15 LOW, 6 NIT)
**Status:** unactioned — no code changes made by this review

> Numbered prefix = sequence. **P0** = stop-the-bleed, do today. **P1** = this week. **P2** = next sprint. **P3** = backlog.

---

## P0 — Stop the bleed (today)

### P0.1 — Rotate leaked cloud credentials NOW
- **Why:** `gcp-sa.json` and `azure-sp.txt` exist in working tree with real-looking secrets (SEC C-01, C-02). Even if `.gitignore`d now, they may already be in git history, shell history, backups, or another agent's context.
- **Do:**
  1. `git log --all -- gcp-sa.json azure-sp.txt` — confirm not in history. If present → BFG / `git filter-repo` purge.
  2. GCP console → revoke service account, regenerate key, redistribute via secret manager.
  3. Azure portal → reset client secret on the SP, redistribute.
  4. `git rm` the local files; verify `.gitignore` entries (INFO I-01 says already covered — re-verify).
  5. Audit `azure-sp.txt` / `gcp-sa.json` for the tenant/project/subscription IDs — those don't rotate, treat as compromised metadata.

### P0.2 — Kill the `admin:admin` seed
- **File:** `sql/seed_*.sql`, `utils/encryption.py` admin hash (SEC C-03, M-01).
- **Do:** delete the seed insert; require operator to bootstrap first admin via CLI (`python -m backend.app.cli create-admin`). Block app start if zero users exist on a non-dev env.

### P0.3 — Strip dev defaults from `docker-compose.yml`
- **File:** `docker-compose.yml` (SEC C-04).
- **Do:** remove `JWT_SECRET=dev`, `ENCRYPTION_KEY=dev`, weak `POSTGRES_PASSWORD`, `ALLOWED_ORIGINS=*`. Replace with `env_file: .env.local` (gitignored). Add `.env.example` with placeholders.

### P0.4 — Encrypt credentials on every write path
- **Files:** `backend/app/api/routes/config.py` (GCP, Azure registration endpoints) (SEC C-06).
- **Bug:** AWS path encrypts; GCP and Azure paths store **plaintext** in DB.
- **Do:** route every cred dict through `encrypt_config` before insert/update. Add a unit test asserting `SELECT config FROM cloud_connections` is opaque base64 for all providers.

### P0.5 — Fix `_mask_secrets` allow-list
- **File:** `backend/app/api/routes/config.py` `_mask_secrets` (SEC C-07).
- **Bug:** misses `key_file_base64` (GCP) and `master_key` (LiteLLM) → API returns real secrets to clients.
- **Do:** convert from deny-list to **allow-list** of safe-to-return keys (`provider`, `name`, `created_at`, …). Add test that no value matching `(secret|key|password|token)` is in `GET /config/{id}` response.

---

## P1 — This week

### P1.1 — Rate-limit `/auth/token` and `/auth/login`
- **Files:** `backend/app/api/routes/auth.py`, `pyproject.toml` already has `slowapi` (SEC C-08, INFO I-04).
- **Do:** wire `slowapi` Limiter → `@limiter.limit("5/minute")` on login. Per-IP + per-username key. Return 429 with `Retry-After`.

### P1.2 — Validate OAuth `state` + GitHub allow-list
- **Files:** OAuth callback (SEC C-09, C-10).
- **Do:** store `state` in signed cookie or short-TTL Redis on init; reject if missing/mismatched on callback. Add `GITHUB_ALLOWED_USERS` env var; if empty, deny all OAuth signups (no anonymous account creation).

### P1.3 — Enforce `is_admin` claim
- **Files:** routes that mutate config, run extractors, or hit `/db/*` (SEC H-05, H-02).
- **Do:** add `require_admin` dependency. Apply to all `POST /config*`, `POST /extractors/run`, all `/db/*`. Mount `/db/*` only if `FINNA_DEV_ROUTES=1`.

### P1.4 — Tighten encryption KDF
- **File:** `utils/encryption.py` (SEC C-05).
- **Bug:** falls back to unsalted SHA-256 of arbitrary string when key isn't valid Fernet.
- **Do:** require `ENCRYPTION_KEY` be 32 url-safe base64 bytes; refuse to start if not. Delete the SHA-256 fallback.

### P1.5 — Decrypt failure must raise, not redact
- **File:** `utils/encryption.py` `decrypt_config` (SEC C-11, M-13).
- **Bug:** on InvalidToken returns `{"_decryption_error": "..."}`; runner then runs extractor with empty creds.
- **Do:** raise `EncryptionError`; runner catches and marks run failed. Drop the legacy base64 fallback.

### P1.6 — Async-route blocking-DB time bomb
- **Files:** `backend/app/api/db.py`, every async route (QUAL HIGH-01, HIGH-02).
- **Bug:** routes declared `async def` call sync `query_one/query_all` → event loop blocked. Middleware swallows exceptions and double-invokes `call_next`.
- **Do:** either (a) switch routes to `async` + `AsyncConnectionPool` + `await cur.execute(...)`, or (b) wrap sync DB calls in `await asyncio.to_thread(...)`. Delete the swallowing middleware. Pick one DB pool, not two.

### P1.7 — Naive `datetime.now()` vs `timestamptz`
- **Files:** `routes/costs.py`, `routes/config.py` `_resolve_window` (QUAL HIGH-03, MED-05).
- **Do:** replace every `datetime.now()` and `datetime.utcnow()` with `datetime.now(timezone.utc)`. Add ruff rule `DTZ` to lint catch new occurrences. Dedupe `_resolve_window` into single utility.

### P1.8 — Allow-list extractor module path
- **File:** `backend/app/api/runner.py` `start_extractor` (QUAL HIGH-05).
- **Bug:** `extractor_type` flows into module import path → arbitrary code load via PYTHONPATH.
- **Do:** `ALLOWED = {"azure_cost","gcp_billing","gcp_csv","aws_cost","litellm_cost","exchange_rates"}` + 400 on miss.

---

## P2 — Next sprint

### P2.1 — Tenant scoping (IDOR)
- **All data routes** (SEC H-01). Currently any authenticated user reads any tenant's costs/configs/alerts.
- **Do:** add `tenant_id` column on all data tables; resolve from JWT claim; `WHERE tenant_id = :current_tenant` on every query. Large refactor — gate behind feature flag, migrate, then turn on.

### P2.2 — Subprocess hardening
- **File:** `backend/app/api/runner.py` (SEC M-05, QUAL HIGH-04, HIGH-06, MED-06, MED-12).
- **Do:**
  - Filter env: pass only `PG_DSN`, `ENCRYPTION_KEY`, provider-specific creds. Whitelist, not full `os.environ` inherit.
  - Switch monitor thread → `asyncio.create_subprocess_exec` with streaming reads (fixes unbounded stdout OOM, unreachable-error path).
  - Bounded stdout buffer (e.g., 10 MB rotation to file).
  - `_running_processes` global dict → DB-backed run state (kills horizontal scaling now).
  - Reap on `cancel_run` (M-10): `proc.wait(timeout=5)`; if timeout → `proc.kill()` + `proc.wait()`.

### P2.3 — Extractor base class
- **Files:** `extractors/azure_cost.py` (916 LOC), `gcp_billing.py` (525), `aws_cost.py` (475), `litellm_cost.py` (504) (QUAL MED-09, MED-10).
- **Bug:** ~80% duplication: env load, DB connect, batch insert, log setup, exit codes.
- **Do:** `extractors/base.py:CostExtractor` ABC with hooks `fetch_records()`, `normalize(row)`; common `run()` handles batching, retry, exit. Reduces 3.4k LOC by est. ~60%.

### P2.4 — Batched inserts (`executemany`)
- **Files:** all extractors `_insert_batch` (QUAL HIGH-07, MED-08).
- **Bug:** N round-trips per batch despite name; one bad row aborts whole batch.
- **Do:** `cur.executemany("INSERT ... ON CONFLICT DO UPDATE ...", rows)` or `psycopg.copy`. Wrap each row in SAVEPOINT to isolate failures.

### P2.5 — XML / SSRF / leak hardening
- `exchange_rates.py` `xml.etree.ElementTree.fromstring` → use `defusedxml.ElementTree` (SEC H-09).
- `_fetch_ecb_xml` → require `https://`, restrict host allow-list (SEC H-12).
- `generic_exception_handler` → `logger.exception(...)`; return generic message (SEC H-10, H-11, M-11).
- `config_test` Azure → swallow inner error, return boolean + error code only (SEC H-06).

### P2.6 — Frontend dead-code purge (huge clarity win)
- **Files:** `ui/src/pages/`, `ui/src/api/`, `ui/src/data.js`, `ui/src/data/mock_api_data.json` (QUAL HIGH-08, HIGH-09, MED-19, MED-20, MED-22).
- **Do:**
  - Delete duplicate page implementations (3 parallel sets for same routes).
  - Delete unused HTTP client; keep the one with token refresh.
  - Delete `data.js` + JSON mocks now that real API exists.
  - Pick one router strategy: `BrowserRouter` *or* hash; delete `window.location.hash` writes from `main.tsx:74`.
  - Pick one auth storage: `sessionStorage` *or* `localStorage`, not both (MED-21).

### P2.7 — Frontend type discipline
- **QUAL MED-23, NIT-05.**
- **Do:** generate types from `docs/openapi.yaml` (`openapi-typescript`); replace `any` on data path; dedupe `format_*` helpers into `ui/src/lib/format.ts`.

### P2.8 — Mypy + ruff tightening
- **Files:** `pyproject.toml`, `ruff.toml` (QUAL MED-16, LOW-01).
- **Do:** mypy → `strict = true`, `disallow_untyped_defs = true`, `check_untyped_defs = true`. Ruff add: `B, S, UP, SIM, RUF, DTZ, ASYNC, TRY`. Expect ~50 fresh findings — fix incrementally.

---

## P3 — Backlog (do when touching the area)

- **Container hardening** (SEC L-04): nginx security headers (CSP, X-Frame-Options, HSTS, Referrer-Policy).
- **Python 3.14 in Dockerfile** (QUAL MED-27): align with `pyproject.toml` `>=3.11`; pin to 3.13.
- **Dockerfile layer caching** (QUAL LOW-09): copy `pyproject.toml` + `uv.lock` first, install deps, then copy source.
- **Multi-stage Docker, drop nginx-in-api** (QUAL NIT-02): nginx and uvicorn in separate containers.
- **Structured logging + correlation IDs** (QUAL LOW-03): `structlog` or `python-json-logger`; request-id middleware.
- **Frontend a11y** (QUAL LOW-05): semantic landmarks, button/link discipline, aria-labels on icon buttons.
- **Frontend test stack consolidation** (QUAL LOW-06): pick Vitest, drop Jest. Keep Playwright for e2e.
- **Bundle audit** (QUAL LOW-07): `npx depcheck` + `vite-bundle-visualizer`; drop unused deps.
- **Repo hygiene** (QUAL LOW-12, LOW-13, LOW-14, LOW-15):
  - Move `COMPLETION_REPORT.md`, `MVP_COMPLETE.md`, `STATUS_UPDATE.md`, `E2E_TEST_RESULTS.md`, `TODO_AWS.md`, `INTEGRATION.md`, `README_INTEGRATION.md`, `GITHUB_ISSUES_TEMPLATE.md` → `docs/archive/`.
  - `.gitignore`: `htmlcov/`, `.coverage`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `*.egg-info/`, empty `node_modules/` at root.
  - Decide whether `.planning/`, `.opencode/`, `.hermes/`, `.playwright-mcp/`, `graphify-out/`, `gap-analysis/` belong in-repo or moved to a sibling dir.
- **CLI vs UUID route split** (QUAL MED-11): split `routes/config.py` (675 LOC) into `routes/config_admin.py` (UUID CRUD) + `routes/config_cli.py` (name-based).
- **Module-level `os.getenv`** in extractors (QUAL MED-13): move to function scope so test env overrides take effect.
- **`Provider` enum missing AWS** (SEC M-12): add `AWS = "aws"` to enum in `models.py`.
- **Audit logging** for credential CRUD, extractor runs, admin actions. Persist to immutable table.
- **Bcrypt timing-safety across user-existence** (SEC M-07): always run `checkpw` against a static dummy hash on miss.
- **NIT cleanups:** `print()` → `logger`; remove dead `_alert_responses`, `USERS_TABLE`; collapse `# noqa: E402` import patterns.

---

## What is NOT a problem (already fixed — don't re-flag)

- `JWT_SECRET` env var required (commit 715ff2f)
- `ENCRYPTION_KEY` env var required (f817da1)
- CORS explicit origins (d69dcac)
- OAuth state uses `secrets.token_urlsafe` (a814f9f)
- Claude Code Review workflow removed (86d1718)

---

## Suggested PR sequence

1. **PR-A (P0, single commit, urgent):** rotate creds + remove seed admin + strip compose defaults + encrypt-all-providers + mask allow-list + `_mask_secrets` test.
2. **PR-B (P1 auth):** rate limit + OAuth state/allow-list + `require_admin` + KDF tighten + decrypt-raise.
3. **PR-C (P1 async):** event-loop fix + datetime UTC + extractor allow-list. Has integration-test risk — separate PR.
4. **PR-D (P2 runner):** subprocess refactor.
5. **PR-E (P2 frontend):** dead-code purge — ~1k LOC delete, low risk if tests pass.
6. **PR-F (P2 extractor base):** ABC refactor + executemany. Bigger but pays back per extractor.
7. **PR-G (P2 hardening):** XML/SSRF/leaks/headers.
8. **PR-H (P2 types):** mypy strict + openapi-typescript.
9. **PR-I+ (P3):** drip-feed as touched.

Verify after each PR: `pytest`, `ruff check .`, `mypy backend/ extractors/`, `cd ui && pnpm typecheck && pnpm test`.
