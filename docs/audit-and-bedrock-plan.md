# Finna — Codebase Audit & AWS Bedrock Implementation Plan

**Date:** 2026-08-15
**Commit audited:** `243a5c5` (`main` == `claude/codebase-audit-bedrock-plan-9o5qv2`)
**Method:** static review plus a live reproduction environment — PostgreSQL 16 initialised from
`sql/init_docker.sql`, `alembic upgrade head`, and the full `pytest` suite run exactly as
`.github/workflows/ci.yml` does. Every P0/P1 finding below was reproduced, not inferred.

---

## 1. Verdict

The architecture is sound and the surrounding engineering is unusually good for a project this
size: a genuinely normalised cross-provider cost schema, a clean extractor/API/rule-engine split,
enforced secrets validation at boot, CORS wildcard rejection, log sanitisation, a rule registry
with real tests, and a documented price-catalog pattern.

But **the core data path does not work.** Three of the four cost extractors cannot write a single
row to the database, and OIDC single sign-on is broken twice over — every ID token is rejected, and
every provider read path returns 500. All three failures are invisible to the test suite, because
it asserts against mocks rather than a real database, a real token, or a real response body. A
reader of the test report would conclude the system is healthy; it is not.

The headline items are small, surgical fixes — roughly a day of work for the P0s. They should land
before any Bedrock work begins, because the Bedrock extractor would inherit the same broken insert
path and the same unencrypted-credential storage.

Baseline on a pristine database, run exactly as CI does: **24 failed, 478 passed, 5 skipped, 7
errors** — plus 4 `mypy` errors that fail the typecheck gate outright.

---

## 2. Findings

Severity: **P0** — core feature broken in production · **P1** — correctness/security risk or
blocked pipeline · **P2** — maintainability and hygiene.

### P0-1 — Every batch insert is malformed; Azure, AWS and LiteLLM ingestion fails 100% of the time

`_INSERT_SQL_BATCH` in three extractors lists more columns than it supplies placeholders for:

| Module | Columns | `%s` placeholders | Status |
|---|---:|---:|---|
| `extractors/azure_cost.py` | 31 | 29 | **broken** |
| `extractors/litellm_cost.py` | 26 | 24 | **broken** |
| `extractors/aws_cost.py` | 20 | 19 | **broken** |
| `extractors/gcp_billing.py` | 20 | 20 | correct |

`insert_records()` → `_insert_batch()` → `cur.executemany()` is the live path in all three, so the
failure is unconditional. Reproduced against the live database:

```
litellm: ProgrammingError: the query has 24 placeholders but 26 parameters were passed
aws:     ProgrammingError: the query has 19 placeholders but 20 parameters were passed
azure:   ProgrammingError: the query has 29 placeholders but 31 parameters were passed
```

Because `extract_costs()` wraps the insert in `try/except → _mark_health_failure() → raise`, every
run marks itself failed in `extractor_health` and exits non-zero. The platform ingests nothing from
Azure, AWS or LiteLLM.

**Why tests missed it.** Every insert test passes a `MagicMock()` connection, which accepts any
argument count. `tests/test_litellm_cost.py::test_insert_batch_invokes_cursor` and
`tests/test_aws_cost.py::TestInsertRecords::test_multiple_batches` both exercise this code and
both fail for *unrelated* reasons (stale assertions, see P2-1) — the SQL defect is never reached.

**Introduced by** `a0ee962` ("fix: asyncio deprecation, batch inserts, DRY window resolver") and
`f804320`, which converted named-parameter SQL to positional and dropped placeholders in the
translation. The original named-parameter constants (`_INSERT_SQL`, `INSERT_SQL`) are still present,
still correct, and now dead.

**Fix.** Don't hand-maintain two parallel lists. Derive the `VALUES` clause from the column tuple:

```python
_COLUMNS = ("record_id", "provider", ..., "tags")
_INSERT_SQL_BATCH = (
    f"INSERT INTO cost_records ({', '.join(_COLUMNS)}) "
    f"VALUES ({', '.join(['%s'] * len(_COLUMNS))}) "
    "ON CONFLICT (record_id) DO NOTHING"
)
```

and build each row with a comprehension over `_COLUMNS` so the ordering cannot drift. Then delete
the dead named-parameter constants.

**Regression guard (required).** Add one `@pytest.mark.integration` test per extractor that inserts
a real `NormalizedCostRecord` against the CI PostgreSQL service and asserts the row is readable
back. A mock-only test cannot catch an arity bug by construction. This single test would have
caught all three.

### P0-2 — OIDC ID-token verification rejects every valid token; SSO cannot succeed

`backend/app/api/oidc.py:314`:

```python
claims = jwt.decode(id_token, key, algorithms=[alg], options={"verify_signature": True})
```

`python-jose` validates the `aud` claim by default. With no `audience=` argument supplied, any token
carrying an `aud` claim — which every spec-compliant OIDC ID token does — raises
`JWTClaimsError: Invalid audience`. Reproduced standalone with a freshly signed RS256 token, outside
the test suite's mocks:

```
as oidc.py calls it   → FAILED: JWTClaimsError: Invalid audience
with audience= passed → OK: user123
```

So `verify_id_token()` raises `OIDCError` for every real login. OIDC/SSO — Keycloak, Okta, Auth0,
Entra ID, Google — is entirely non-functional. Five tests in `tests/test_oidc.py` fail on this in
isolation and have presumably been red since the feature merged.

A second, smaller defect compounds it: the `except JWTError` wraps *all* claim errors as
`"Signature verification failed: {e}"`, so an operator debugging this is told the signature is bad
when the signature is fine. It also masks the `exp` / `iss` / `nonce` checks immediately below,
which can never be reached.

**Fix.** Pass the expected claims to the decoder and let it do the work it already knows how to do:

```python
claims = jwt.decode(
    id_token, key, algorithms=[alg],
    audience=client_id, issuer=issuer,
    options={"verify_signature": True, "verify_aud": True, "verify_iss": True},
)
```

then narrow the handler so `JWTClaimsError` reports a claim failure distinctly from a signature
failure. The manual `exp`/`iss`/`aud`/`nonce` checks below become belt-and-braces; keep the `nonce`
check (jose does not validate it) and keep the `alg` allowlist above (it correctly rejects `none`
and `HS*` before any key material is chosen).

### P0-3 — Every OIDC provider *read* path returns 500 (raw UUID into a `str` field)

Three sites pass psycopg's `uuid.UUID` straight into a Pydantic field declared `str`:

| Site | Endpoint |
|---|---|
| `routes/auth_providers.py:89` | `GET /api/v1/auth/providers` (admin list) |
| `routes/auth_providers.py:122` | `GET /api/v1/auth/providers/{provider_id}` |
| `routes/oidc_auth.py:132` | provider list used by the login flow |

Pydantic v2 does not coerce `UUID` → `str`, so each raises `ValidationError` → **500**:

```
pydantic_core.ValidationError: 1 validation error for AuthProviderResponse
id
  Input should be a valid string [type=string_type,
   input_value=UUID('0b271ff0-dd03-468e-8773-3c7468dc260b'), input_type=UUID]
```

The create path escapes it (it stringifies), so **a provider can be created and then never read
back** — not in the admin list, not individually, and not by the login flow. Reproduced directly
against a pristine database:

```
CREATE:        200  0b271ff0-dd03-468e-8773-3c7468dc260b
GET  by id:    500
LIST (admin):  500
```

This is the second, independent break in OIDC: even with P0-2 fixed, the login flow cannot enumerate
providers. It is also the true cause of most of the OIDC test noise — the `KeyError: 'state'`
failures in `test_oidc_e2e.py` are downstream of a 500 from the login endpoint, not the test-data
residue they superficially resemble (see the correction in P2-3).

Commit `f804320` ("fix OIDC UUID crash") fixed one instance of this class; three remain.

**Fix.** `id=str(row["id"])` at all three sites, matching what the create path already does. Better,
declare the field as `uuid.UUID` and let Pydantic serialise it, so the next endpoint cannot
reintroduce the bug. A response-model test that actually asserts on a 200 body would have caught it —
the existing tests assert on status codes that were already failing.

### P1-1 — CI is red on `main`

`backend-typecheck` is a hard gate and `mypy` fails:

```
backend/app/api/routes/oidc_device_auth.py:38: error: Returning Any from function declared to return "str"
backend/app/api/routes/oidc_device_auth.py:41: error: Returning Any from function declared to return "str"
backend/app/api/routes/oidc_auth.py:33: error: Returning Any from function declared to return "str"
backend/app/api/routes/oidc_auth.py:36: error: Returning Any from function declared to return "str"
```

(`ruff` passes cleanly.) Combined with the failing tests, no commit on `main` can currently produce
a container build. Fix with explicit `str(...)` coercion or a `cast(str, ...)` at those four returns.

### P1-2 — AWS Cost Explorer group keys are parsed wrongly; multi-account costs are silently dropped

`normalize_aws_cost_records()` assumes the two `GroupBy` dimensions arrive tilde-joined in a single
key:

```python
identity = keys[0]
parts = identity.split("~")
service_code = parts[0] if len(parts) > 0 else None
account_id   = parts[1] if len(parts) > 1 else "unknown"
```

Cost Explorer returns **one list element per `GroupBy` dimension** — `"Keys": ["AmazonEC2", "123456789012"]`
— not `["AmazonEC2~123456789012"]`. In production `parts` therefore has length 1, and:

- `account_id` and `project_id` are always `"unknown"`, so per-account attribution is lost entirely;
- `_generate_record_id("unknown", service_code, date)` collides across every linked account, so
  `ON CONFLICT (record_id) DO NOTHING` **discards all but the first account's cost** for each
  service/day.

For an AWS Organization this is not a cosmetic bug — reported AWS spend would be a fraction of
actual spend, with no error surfaced.

The unit test encodes the wrong shape and so passes: `tests/test_aws_cost.py:64` builds
`"Keys": [f"{service}~{account_id}"]`.

**Fix.** Index the list positionally, matching the `GroupBy` order declared in `get_cost_and_usage()`:

```python
service_code = keys[0] if len(keys) > 0 else None
account_id   = keys[1] if len(keys) > 1 else "unknown"
```

and correct the fixture to `"Keys": [service, account_id]`. Note this changes `record_id` for
already-ingested AWS rows; plan a one-off re-ingest of the affected window.

### P1-3 — AWS credentials are stored unencrypted (blocks the Bedrock work)

`utils/encryption.py` encrypts a fixed allowlist:

```python
sensitive_fields = ["client_secret", "key_file_base64", "key_file_content"]
```

Azure's `client_secret` and GCP's key material are covered. **AWS is not** — an
`aws_secret_access_key` (or `secret_access_key`, `session_token`, `external_id`) submitted through
`POST /api/v1/config` is persisted to `cloud_config` in plaintext, and returned in plaintext by the
read path. Any Bedrock connection added on top of the current code inherits this.

**Fix before Bedrock.** Invert the allowlist to a denylist-by-pattern, or at minimum extend it:

```python
SENSITIVE_FIELDS = {
    "client_secret", "key_file_base64", "key_file_content",
    "aws_secret_access_key", "secret_access_key", "session_token",
    "external_id", "password", "api_key", "master_key",
}
```

A defensive complement: treat any key matching `(secret|password|token|key)` case-insensitively as
sensitive, so a future provider cannot silently opt out of encryption by naming a field differently.
`scripts/migrate_config_encryption.py` already exists as the backfill vehicle for existing rows.

### P1-4 — `decrypt_config` swallows all errors and silently redacts

```python
except (InvalidToken, json.JSONDecodeError, Exception):
```

The bare `Exception` makes the preceding tuple members redundant and, more importantly, converts a
**rotated or wrong `ENCRYPTION_KEY`** into a config that looks merely credential-less. An extractor
then fails with "credentials not configured" rather than "cannot decrypt", sending operators down
the wrong path. Log the exception type at `error` level and let a decryption failure be
distinguishable from an absent credential.

### P1-5 — `/api/v1/db/stats` is unauthenticated

`main.py:190` exposes connection-pool internals with no `Depends(require_auth)`, unlike every
router endpoint. Low severity on its own, but it is free reconnaissance and trivially fixed.

### P2-1 — Four tests have drifted from the implementation they cover

| Test | Reality |
|---|---|
| `test_aws_cost.py::TestInsertRecords::test_multiple_batches` | asserts `execute.call_count == 5`; implementation uses `executemany`, so `execute` is never called |
| `test_db_main_runner.py::test_get_connection_all_invalid` | supplies 2 `side_effect` values to a 3-attempt retry loop → `StopIteration` instead of the expected `OperationalError` |
| `test_db_main_runner.py::test_close_pools_with_async_running_loop` | patches `asyncio.get_event_loop`; `close_pools()` calls `asyncio.get_running_loop()` |
| `test_litellm_cost.py::test_insert_batch_invokes_cursor` | same `execute`/`executemany` drift |

These are stale assertions, not product bugs — but they are the noise that let P0-1 hide.

### P2-2 — A test performs live network calls to AWS

`TestExtractCosts::test_missing_credentials_returns_zero` calls `extract_costs()` with no
`monkeypatch.delenv`, so it only passes when the environment happens to have no AWS credentials.
In an environment that does have them (as this audit sandbox did), it authenticates against the real
Cost Explorer API and burns ~7s in `tenacity` retries:

```
WARNING extractors.aws_cost: Retrying ... ClientError: UnrecognizedClientException ...
```

A unit test must never depend on ambient credentials, and must never reach the network. Add
`monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)` (and the secret key) to pin the intent.

### P2-3 — The suite is not database-isolated and is not idempotent

`tests/test_oidc_e2e.py` and `tests/test_auth_providers.py` `POST` providers with fixed names and
never clean up. On a second run against the same database the create returns `409 Conflict` and the
tests fail with `KeyError: 'id'`. Auto-provisioned `auth_users` rows also hold a foreign key to
`auth_providers`, so a naive cleanup is blocked.

Measured on those two files, recreating the database between the two runs:

| Run | Result |
|---|---|
| 1 — pristine database | 7 failed, 7 passed |
| 2 — same database, immediately after | 10 failed, 4 passed |

So residue accounts for **3 extra failures**, not the bulk of them. The other 7 are genuine product
bugs — P0-3 (UUID→`str`) and P0-2 (audience). This is a real hygiene problem worth fixing, but it is
a P2, and it should not be used to explain away the OIDC failures: those are real.

**Fix.** Wrap each test in a transaction that rolls back, or add a fixture that truncates
`auth_users, auth_providers RESTART IDENTITY CASCADE` between tests, and randomise provider names.
This matters more than it looks: it is the difference between a suite that is trustworthy on the
second run and one that is only ever green on fresh CI.

### P2-4 — Dev dependency lists have diverged; local `pytest` can hang forever

Two dev dependency sets disagree:

- `[project.optional-dependencies].dev` — used by CI (`pip install -e ".[dev]"`) — includes `mypy`
  and `pytest-timeout`.
- `[dependency-groups].dev` — used by `uv sync`, which `AGENTS.md` instructs developers to run —
  includes neither.

So the documented local workflow produces an environment where `timeout = 30` in
`[tool.pytest.ini_options]` is inert:

```
PytestConfigWarning: Unknown config option: timeout
```

A test that blocks on a database connection then hangs indefinitely rather than failing at 30s —
observed here before `pytest-timeout` was installed manually. Consolidate on one list (the
`[dependency-groups]` one, since `uv` is the documented tool) and include `mypy` + `pytest-timeout`
so contributors can reproduce the CI gate locally.

### P2-5 — Smaller items

- **Dead code:** the correct named-parameter `_INSERT_SQL` / `INSERT_SQL` constants in
  `aws_cost.py`, `litellm_cost.py` and `azure_cost.py` are unused. Delete them with the P0-1 fix.
- **`latency_ms` is never populated.** The column exists in `cost_records` and the LLM dashboards
  chart `avg_latency_ms`, but no extractor writes it — LiteLLM's `_insert_batch` omits it despite
  the data being available in `/spend/logs`. Bedrock invocation logs carry latency too (see §3).
- **No AWS credential test path.** `POST /api/v1/config/{id}/test` implements `azure` and `gcp`
  only; an AWS config silently has no verification path. Worth adding alongside Bedrock (§3.6).
- **Retry semantics:** `@retry` on `get_cost_and_usage` wraps the *entire* pagination loop, so a
  failure on page 9 replays pages 1–8. Harmless (results are rebuilt in a local list) but wasteful
  against a rate-limited API; retry the single `client.get_cost_and_usage(**kwargs)` call instead.
- **Python version drift:** `pyproject.toml` declares `>=3.11`, Dockerfiles and CI pin 3.12. The
  `AGENTS.md` gotcha about `python3.12` COPY paths is a symptom. Pin `requires-python = ">=3.12"`
  if 3.12 is the real floor.

### What is genuinely good

Worth stating plainly, because the findings above are concentrated in a few files:

- The normalised `cost_records` schema is well designed and already carries the LLM-specific columns
  (`model_name`, `input_tokens`, `output_tokens`, `total_tokens`, `latency_ms`, `trace_id`) that make
  the Bedrock work mostly additive.
- Boot-time refusal of placeholder/short `JWT_SECRET` and `ENCRYPTION_KEY`, and rejection of CORS
  `*` with credentials, are the right defaults and are rare to see done properly.
- `gcp_billing.py` is the model the other extractors should follow — explicit column/value pairing,
  `RETURNING` to count real inserts rather than assuming, `Json()` adaptation.
- The wastage rule registry, its `data/prices/` catalog with a documented refresh procedure, and its
  test coverage are a good foundation — and the direct precedent for the Bedrock price book.
- `_safe_ts_col()`'s explicit allowlist for an interpolated identifier is exactly the right way to
  keep dynamic SQL auditable.

---

## 3. AWS Bedrock Implementation Plan

### 3.1 Goal and the core design decision

Two different questions need answering, and they need two different data sources:

1. **"What did Bedrock cost?"** — the invoice. Only AWS billing can answer this.
2. **"Who spent it, on which model, on what?"** — attribution. Billing data alone cannot answer it
   at model/team/request granularity.

The plan therefore has two tracks, and **the single most important decision is that only one of them
writes money.**

| | Track A — Billing | Track B — Usage |
|---|---|---|
| Source | Cost Explorer (`ce:GetCostAndUsage`), grouped by `SERVICE` + `USAGE_TYPE` | Bedrock model invocation logs (CloudWatch Logs or S3) |
| Granularity | Daily, per usage type | Per invocation |
| Cost | **Authoritative** — real billed USD | **Estimated** — tokens × price book |
| Tokens | No | Yes (input/output/cache, latency, model, region) |
| Provider | `Provider.AWS`, `ServiceCategory.LLM` | `Provider.LLM`, `ServiceCategory.LLM` |
| Latency | ~24h | Minutes |

**Double-counting is the trap.** `GET /api/v1/costs/totals` aggregates per provider, so Bedrock
spend appearing as both `aws` and `llm` would inflate any cross-provider sum. Mitigation, using
columns that already exist:

- Track B writes `charge_type = 'Estimated'` and `tags.cost_source = 'bedrock_invocation_logs'`.
- All money aggregations exclude `charge_type = 'Estimated'` by default (a `WHERE` clause change in
  `routes/costs.py` and the Grafana panels), so Track B contributes tokens and attribution without
  contributing dollars.
- A reconciliation panel plots Track A actual vs Track B estimated per day; sustained divergence >5%
  means the price book is stale.

This also retro-fixes an existing latent issue: LiteLLM records already land under `Provider.LLM`
and may overlap the underlying cloud bill in exactly the same way.

### 3.2 Track A — Bedrock line items from Cost Explorer

Smallest possible change, and it depends on P0-1 and P1-2 being fixed first.

**`extractors/aws_cost.py`**

- Add `{"Type": "DIMENSION", "Key": "USAGE_TYPE"}` to `GroupBy`. Cost Explorer permits two
  dimensions per call, so run a second, Bedrock-filtered query rather than widening the existing one:

  ```python
  Filter={"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Bedrock"]}}
  GroupBy=[{"Type": "DIMENSION", "Key": "USAGE_TYPE"},
           {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}]
  ```

- Map `"AmazonBedrock"` → `ServiceCategory.LLM` in `SERVICE_CODE_MAP` (note `get_service_category()`
  does a substring match, so the existing `"AmazonES"`/`"AmazonMQ"` entries are already fragile —
  order the map most-specific-first while touching it).
- Parse the usage type (e.g. a region prefix plus `InputTokenCount` / `OutputTokenCount` /
  `CacheReadInputTokenCount`) into `usage_unit = "tokens"` and `tags.usage_type`, and derive
  `region` from the usage-type prefix.
- Include `"UsageQuantity"` alongside `"UnblendedCost"` in `METRICS` so `usage_quantity` carries the
  billed token count — that is what makes the Track A/Track B reconciliation possible.

**Cost allocation tags are the highest-leverage AWS-side lever.** Bedrock supports *application
inference profiles*, which wrap a model with an ARN that accepts cost allocation tags. If callers
invoke a tagged application inference profile instead of a bare model ID, Cost Explorer can group by
that tag and Track A alone yields per-team/per-project attribution. Recommend this in
`docs/tagging-strategy.md` — it is an infrastructure change on the consuming side, not something the
extractor can do, but it is the difference between estimated and billed attribution.

### 3.3 Track B — per-invocation usage from Bedrock invocation logs

New module `extractors/bedrock_usage.py`, modelled closely on `litellm_cost.py` (same shape: fetch →
normalise → price → batch insert → health tracking) so it lands in the existing LLM dashboards
beside LiteLLM data with no dashboard changes.

**Prerequisite (customer-side).** Bedrock model invocation logging is **off by default**. It is
enabled per-region via `PutModelInvocationLoggingConfiguration`, delivering to CloudWatch Logs
and/or S3. Document this in the setup guide; without it Track B has no input. The extractor should
call `GetModelInvocationLoggingConfiguration` at startup and fail with a clear, actionable message
rather than silently returning zero records — a mistake the existing extractors make.

**Ingestion.** Support both sinks behind one interface:

- **CloudWatch Logs** (`logs:FilterLogEvents` / `StartQuery`) — simplest, good for moderate volume,
  supports incremental pulls by timestamp.
- **S3** (`s3:ListObjectsV2` / `GetObject`) — required at high volume; JSON-lines, partitioned by
  date. Stream and parse incrementally rather than loading whole objects.

Select with `BEDROCK_LOG_SOURCE=cloudwatch|s3`, defaulting to whatever
`GetModelInvocationLoggingConfiguration` reports.

**Normalisation → `NormalizedCostRecord`.** Every field maps onto existing columns:

| Bedrock log field | Column |
|---|---|
| `requestId` | `trace_id`, and the `record_id` hash input |
| `modelId` | `model_name`, `service_name` |
| `input.inputTokenCount` | `input_tokens` |
| `output.outputTokenCount` | `output_tokens` |
| sum | `total_tokens`, `usage_quantity` (`usage_unit="tokens"`) |
| `timestamp` | `usage_start` / `usage_end` |
| `region` | `region` |
| `accountId` | `account_id` |
| latency | `latency_ms` — **fills the column nothing currently populates** |
| inference profile / tags | `project_id`, `team`, `environment`, `tags` |

`record_id = sha256(f"bedrock:{request_id}")[:32]`, giving idempotent re-ingestion through the
existing `ON CONFLICT DO NOTHING`, exactly as LiteLLM does.

**Model ID handling — do not treat the ID as opaque.** Cross-region inference prefixes the model ID
with a geography (`us.`, `eu.`, `apac.` — e.g. `us.anthropic.claude-…`), and application inference
profiles substitute an ARN entirely. Normalise before pricing:

- strip a leading geography prefix into `tags.inference_geo`, keeping the base model ID for the
  price lookup;
- for an ARN, resolve it via `bedrock:GetInferenceProfile` (cache the result) to recover the
  underlying model, and carry the profile ARN in `tags.inference_profile` — that is also where the
  cost allocation tags live.

Without this, every cross-region invocation misses the price book and is costed at zero.

### 3.4 Price book

Extend the existing catalog rather than inventing a mechanism — `data/prices/aws_list_prices.json`
already exists, is sourced from the AWS Price List API, and has a documented refresh procedure.

```jsonc
"bedrock": {
  "_unit": "USD per 1K tokens",
  "us-east-1": {
    "anthropic.claude-…": { "input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0 }
  }
}
```

**Do not hardcode prices from memory.** Bedrock is partner-operated and its rates are set by AWS
independently of first-party Anthropic API pricing; they also vary by region. Populate the file from
the Price List API (`pricing:GetProducts`, service code `AmazonBedrock`) via a refresh script beside
the existing one, and record `_meta.refreshed`.

Reuse `backend/app/wastage/pricing.py`'s contract — `lookup()` returns `Decimal("0")` on a miss and
never raises. Add one deliberate deviation: **count and log price-book misses per run** and surface
the count in `extractor_health`. Silent zero-costing is the failure mode that would make Track B
quietly useless, and it is precisely what a never-raises lookup invites.

Cover the non-on-demand modes explicitly, since they break a naive tokens × rate model:

- **Batch inference** — discounted relative to on-demand; key off the log's invocation mode.
- **Provisioned Throughput** — billed hourly per model unit, *not* per token. Invocations against a
  provisioned model must be costed at zero in Track B (Track A carries the real hourly charge) or
  they will double-count against themselves.
- **Prompt caching** — cache-read and cache-write tokens price differently from ordinary input.

### 3.5 Wiring

| File | Change |
|---|---|
| `extractors/entrypoint.py` | add `"bedrock_usage": "extractors.bedrock_usage"` to `EXTRACTOR_MAP`; document env vars in the module docstring |
| `models/__init__.py` | no change — `Provider.LLM` / `ServiceCategory.LLM` already fit. Resist adding `Provider.BEDROCK`: it would fragment the LLM dashboards and force changes across every query |
| `utils/encryption.py` | **P1-3 first** — AWS secrets must encrypt before a Bedrock connection is storable |
| `backend/app/api/routes/config.py` | add an `aws` branch to `/config/{id}/test`: STS `GetCallerIdentity`, then `GetModelInvocationLoggingConfiguration`, returning which sink is configured |
| `sql/init_docker.sql` + a new Alembic migration | seed `extractor_health` / extractor registry rows for `bedrock_usage` |
| `grafana/llm-cost-v2.json` | add an `llm_provider = bedrock` filter value; add the Track A vs Track B reconciliation panel |
| `docs/` | setup guide (enabling invocation logging, IAM policy, inference profiles) and a `docs/tagging-strategy.md` section on application inference profiles |

### 3.6 IAM — least privilege

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "TrackABilling", "Effect": "Allow",
      "Action": ["ce:GetCostAndUsage"], "Resource": "*" },
    { "Sid": "TrackBLogsCloudWatch", "Effect": "Allow",
      "Action": ["logs:FilterLogEvents", "logs:StartQuery", "logs:GetQueryResults",
                 "logs:DescribeLogGroups"],
      "Resource": "arn:aws:logs:*:*:log-group:<bedrock-log-group>:*" },
    { "Sid": "TrackBLogsS3", "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::<bucket>", "arn:aws:s3:::<bucket>/*"] },
    { "Sid": "BedrockMetadata", "Effect": "Allow",
      "Action": ["bedrock:GetModelInvocationLoggingConfiguration",
                 "bedrock:GetInferenceProfile", "bedrock:ListInferenceProfiles"],
      "Resource": "*" },
    { "Sid": "PriceBookRefresh", "Effect": "Allow",
      "Action": ["pricing:GetProducts"], "Resource": "*" }
  ]
}
```

All read-only. Prefer an IAM role with `sts:AssumeRole` + `external_id` over long-lived access keys;
the config schema should accept `role_arn` / `external_id` as an alternative to key material — which
is also the cleanest way to sidestep storing a secret at all.

### 3.7 Testing

Mirroring the existing extractor test layout, plus the gap that let P0-1 through:

- `tests/test_bedrock_usage.py` — normalisation against recorded log fixtures for CloudWatch and S3;
  model-ID normalisation (bare, `us.`-prefixed, ARN); price lookup including a deliberate miss;
  `record_id` stability and idempotency; batch/paging.
- **An integration test that inserts against the real CI database** (`@pytest.mark.integration`).
  Non-negotiable — this is the test class that all three broken extractors lack.
- A cheap unit test asserting `len(_COLUMNS) == _INSERT_SQL_BATCH.count("%s")` for *every* extractor,
  so P0-1 can never recur.
- Reconciliation test: a fixture day of invocation logs priced against a fixed price book must land
  within tolerance of a matching Cost Explorer fixture.
- All AWS calls stubbed; `monkeypatch.delenv` on every AWS env var (see P2-2).

### 3.8 Sequencing

| Phase | Work | Depends on |
|---|---|---|
| **0 — unblock** | P0-1 insert fix + arity guard test; P0-2 OIDC audience; P0-3 UUID→`str` at three sites; P1-1 mypy; P1-2 CE key parsing; P1-3 AWS secret encryption | — |
| **1 — billing** | Track A: Bedrock-filtered CE query, usage-type parsing, `UsageQuantity` metric | Phase 0 |
| **2 — price book** | `bedrock` section in `aws_list_prices.json` + Price List API refresh script + miss counting | — (parallel with 1) |
| **3 — usage** | `bedrock_usage.py`, entrypoint wiring, model-ID/inference-profile normalisation, tests | 0, 2 |
| **4 — surface** | `charge_type='Estimated'` exclusion in cost queries; Grafana filter + reconciliation panel; docs; AWS branch in `/config/{id}/test` | 1, 3 |

Phase 0 is the gate. Building Bedrock ingestion on top of an insert path that cannot write a row,
and a credential store that would hold the AWS secret in plaintext, would multiply both problems.

---

## Appendix — reproduction environment

```bash
initdb -D $PGDATA -U finna --auth=trust && pg_ctl -D $PGDATA start
psql -v ON_ERROR_STOP=1 -U finna -d finna -f sql/init_docker.sql   # exit 0
alembic stamp 001_baseline && alembic upgrade head                  # 001 → 006, clean
uv run pytest -q --timeout=60                                       # see §2
uv run ruff check backend/ extractors/ models/                      # passes
uv run mypy backend/ extractors/ models/ --ignore-missing-imports --explicit-package-bases  # 4 errors
```

Schema creation and all six migrations apply cleanly — the database layer itself is in good shape.
