# Local Testing Guide: Azure Cost Extraction via OAuth

This guide walks you through testing finna-app locally using **your personal Azure account** — no service principal or service account required.

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker & Docker Compose
- An Azure account with at least one subscription
- (Optional) `az` CLI installed — not required, but useful for verification

## Step 1: Install dependencies

```bash
uv sync
```

## Step 2: Start PostgreSQL

```bash
docker compose up -d postgres
```

Verify it's running:
```bash
docker compose ps postgres
```

Wait until status shows "healthy". The database is auto-initialized with schema + 90 days of seed data.

## Step 3: Authenticate and select subscriptions/resource groups

```bash
uv run python -m config.auth azure
```

The TUI will walk you through the full setup:

1. **Tenant ID**: Enter your Azure AD tenant ID, or use `organizations` for multi-tenant
2. **Authentication method**: Select "OAuth device code (browser login — recommended)"
3. **Browser login**: A panel will appear with:
   ```
   ┌─ Device Login ───────────────────────────────┐
   │ 1. Open: https://microsoft.com/devicelogin   │
   │ 2. Enter code: ABCDEFG                        │
   │                                                │
   │ Code expires at 14:35:22                       │
   └───────────────────────────────────────────────┘
   ```
   Open the URL in any browser, enter the code, and sign in.

4. **Subscription selection**: After authentication, the system lists all accessible subscriptions:
   ```
   Available Azure Subscriptions
   ─┬──────────────────────┬──────────────────────┬───────┐
   # │ Subscription ID      │ Name                  │ State │
   ─┼──────────────────────┼──────────────────────┼───────┤
   1 │ xxxxxxxx-xxxx-...    │ Production            │ ...   │
   2 │ yyyyyyyy-yyyy-...    │ Staging               │ ...   │
   ─┴──────────────────────┴──────────────────────┴───────┘
   ```
   Select which subscriptions to extract (space to toggle, enter to confirm).

5. **Resource group selection**: For each subscription, the system shows resource groups:
   ```
   Resource Groups — Production (xxxxxxxx-xxxx-...)
   ──────────────────────┐
   │ Resource Group      │
   ├─────────────────────┤
   │ rg-app-services     │
   │ rg-data             │
   │ rg-networking       │
   └─────────────────────┘
   Extract ALL resource groups in this subscription? (3 found) [Y/n]:
   ```
   Press Enter for all, or selectively choose which resource groups to include.

On success, you'll see:
```
Azure authentication successful!
Configured 2 subscription(s) for extraction.
```

**Everything is saved in OS keyring** — no env vars, no plaintext files. Next time you run the extractor, it auto-discovers your selections.

## Step 4: Run the Azure Cost Extractor

```bash
export PG_DSN="postgresql://finops:finops_dev@localhost:5432/finops"

# That's it! No AZURE_SUBSCRIPTION_ID needed — it reads from keyring
uv run python -m extractors.azure_cost
```

The extractor will:
1. **Auto-discover** your OAuth credentials and subscription selections from keyring
2. Iterate over every selected subscription
3. Filter to selected resource groups (if any)
4. Call the Azure Cost Management API
5. Normalize rows into `cost_records`
6. Batch-insert into PostgreSQL

You should see output like:
```
Starting Azure cost extractor: scope=subscription, subscription=xxxx, from=2026-03-15, to=2026-04-14
Fetched 47 cost rows from Azure API
Inserted 45 of 45 records into PostgreSQL
```

## Step 5: Verify the Data

```bash
psql "postgresql://finops:finops_dev@localhost:5432/finops" \
  -c "SELECT provider, count(*) FROM cost_records GROUP BY provider;"
```

You should see `azure` alongside the seed data providers (`gcp`, `llm`).

Check extractor health:
```bash
psql "postgresql://finops:finops_dev@localhost:5432/finops" \
  -c "SELECT * FROM extractor_health ORDER BY updated_at DESC LIMIT 5;"
```

## Step 6: (Optional) Refresh Materialized View

```bash
psql "postgresql://finops:finops_dev@localhost:5432/finops" \
  -c "REFRESH MATERIALIZED VIEW CONCURRENTLY daily_costs;"
```

## Troubleshooting

### "No token found" / "AuthenticationRequiredError"

```bash
# Re-authenticate (will re-discover subscriptions)
uv run python -m config.auth azure

# Or clear cached credentials and start fresh
uv run python -m config.auth azure --clear
uv run python -m config.auth azure
```

### "Insufficient privileges" / 403 error

Your Azure account needs **Cost Management Reader** role on the target subscription. Ask your Azure admin to assign it, or use a subscription where you're an Owner/Contributor.

### Token expired

OAuth access tokens expire in ~60 minutes, but the `DeviceCodeCredential` auto-refreshes silently using the refresh token stored in keyring. If the refresh token itself expired (>90 days), re-run Step 3.

### Change subscription/resource group selection

Just re-run the auth command — it will re-authenticate and let you pick again:
```bash
uv run python -m config.auth azure
```

### Keyring not available (headless / Docker)

In containers, the OS keyring is unavailable. Fall back to explicit env vars:
```bash
export AZURE_TENANT_ID="<tenant>"
export AZURE_CLIENT_ID="<app-id>"
export AZURE_CLIENT_SECRET="<secret>"
export AZURE_SUBSCRIPTION_ID="<sub-id>"
uv run python -m extractors.azure_cost
```

Or disable keyring:
```bash
export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
```

## Next Steps

- **Superset dashboards**: Run `uv run python superset/bootstrap.py` to visualize your Azure cost data
- **Full wizard**: Run `uv run python -m config.wizard` for end-to-end multi-cloud setup
- **GCP**: Run `uv run python -m config.auth gcp` to set up GCP credentials via `gcloud auth login`