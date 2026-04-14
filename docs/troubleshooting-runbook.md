# FinOps Troubleshooting Runbook

This runbook covers common failure scenarios and their resolution steps for the FinOps multi-cloud monitoring platform.

---

## Extractor Failures

### Check Extractor Health

All extractors write their status to the `extractor_health` table. Start here:

```sql
SELECT
    extractor_name,
    status,
    last_run_start,
    last_run_end,
    records_extracted,
    error_message,
    updated_at
FROM extractor_health
ORDER BY updated_at DESC;
```

Status values: `running` | `success` | `failed`

### Common Errors and Fixes

**Authentication failure**

- **Symptoms**: `error_message` contains "401", "403", "Unauthorized", or "credential".
- **GCP**: Verify the service account key or Workload Identity is properly configured. Check that `GOOGLE_APPLICATION_CREDENTIALS` is set or the Cloud Run Job's service account has `roles/bigquery.dataViewer`.
- **Azure**: Verify `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_CLIENT_SECRET`. Secrets may have rotated. Check that the service principal has `Cost Management Reader` on the target subscription.

**Network connectivity failure**

- **Symptoms**: "Connection refused", "timeout", "could not connect", or `psycopg.OperationalError`.
- **GCP**: Ensure the Cloud Run Job is in a VPC connector with access to BigQuery and Cloud SQL. Check VPC connector egress rules.
- **Azure**: Ensure the Cloud Run container has outbound internet access. Azure Cost Management API is a public endpoint; verify no egress firewall rules block it.

**API quota exceeded**

- **Symptoms**: "429", "rate limit", "quota exceeded" in `error_message`.
- **GCP**: BigQuery has a per-project query quota. Reduce query frequency or request a quota increase. Check BigQuery quotas in the GCP Console.
- **Azure**: Cost Management API has per-subscription rate limits. Space out extractor runs or reduce the date range per call.
- **Resolution**: Increase the `wait_exponential` backoff or schedule extractions at wider intervals.

**Extractor stuck in "running" status**

- **Symptoms**: `status = 'running'` but `last_run_start` is hours ago.
- **Cause**: The container was killed (OOM, preemption) without a chance to update `extractor_health`.
- **Fix**: Manually reset the status:
  ```sql
  UPDATE extractor_health
  SET status = 'failed',
      error_message = 'Container killed without cleanup',
      last_run_end = now(),
      updated_at = now()
  WHERE extractor_name = '<name>' AND status = 'running';
  ```
- **Prevention**: Increase memory allocation for the Cloud Run Job or reduce `BATCH_SIZE`.

---

## Data Gaps

### Identify a Gap

Check for missing dates in `cost_records` for a given provider and project:

```sql
SELECT
    date_trunc('day', usage_start)::date AS day,
    count(*) AS records
FROM cost_records
WHERE provider = 'gcp'
  AND project_id = 'ml-platform'
  AND usage_start >= '2026-03-01'
  AND usage_start < '2026-04-01'
GROUP BY 1
ORDER BY 1;
```

Missing days indicate a gap. Cross-reference with `extractor_health` to see if the extractor ran on those days.

### Re-run Extractors for a Date Range

Re-execute the Cloud Run Job with the specific date range:

```bash
# GCP billing re-run for a specific week
gcloud run jobs execute gcp-billing-extractor \
    --env-set DATE_FROM=2026-03-10,DATE_TO=2026-03-17

# Azure cost re-run
gcloud run jobs execute azure-cost-extractor \
    --env-set DATE_FROM=2026-03-10,DATE_TO=2026-03-17
```

Extractors use `ON CONFLICT (record_id) DO NOTHING`, so re-running over already-ingested dates is safe and idempotent.

### Refresh Materialized Views

After backfilling data, refresh the `daily_costs` materialized view:

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY daily_costs;
```

In production, the pg_cron job refreshes this every 15 minutes. For urgent updates, run it manually.

---

## Dashboard Issues

### Superset Datasource Problems

1. **Check datasource status** in Superset: Navigate to Data > Databases. Click "Test Connection" on the finops-pg database. If it fails:
   - Verify the PostgreSQL host, port, database, user, and password in the connection URI.
   - For Cloud SQL, ensure the Superset instance can reach the database (VPC connector, authorized networks, or Cloud SQL Auth Proxy).
   - For local development, ensure `docker compose up` has started the postgres service and it is healthy: `docker compose ps postgres`.

2. **Connection refused**: The PostgreSQL instance may not be running. Check:
   ```bash
   docker compose ps postgres
   gcloud sql instances describe finops-prod  # production
   ```

3. **SSL errors**: Cloud SQL requires SSL by default. Ensure the connection URI includes `?sslmode=require` or the correct CA certificate.

### Dashboard Provisioning Problems

1. **Dashboard not appearing**: Re-run the bootstrap script to create or update dashboards:
   ```bash
   export SUPERSET_BASE_URL=http://your-superset:8088
   export SUPERSET_ADMIN_USERNAME=admin
   export ADMIN_PASSWORD=your-password
   export FINOPS_PG_URI=postgresql://finops:finops_dev@postgres:5432/finops
   python3 superset/bootstrap.py
   ```
   The script is idempotent — it checks by name before creating resources.

2. **Dashboard shows "No data"**: The underlying query may reference a table or column that does not exist. Open the panel editor in Superset, click "Query", and verify the SQL runs directly against PostgreSQL.

3. **Bootstrap script fails to connect**: Ensure `SUPERSET_BASE_URL` points to a running Superset instance and that the admin credentials are correct.

---

## PostgreSQL Connection Issues

### Cloud SQL Proxy

Production Cloud SQL instances are not directly reachable. Use the Cloud SQL Auth Proxy:

```bash
# Start the proxy (runs in background)
./cloud-sql-proxy <PROJECT>:<REGION>:<INSTANCE> --port 5432 &

# Then connect via localhost
psql "postgresql://finops:password@localhost:5432/finops"
```

Common issues:
- Proxy binary not installed or not in PATH
- Service account lacks `roles/cloudsql.client`
- Proxy port conflict with another service

### VPC Connector

If Cloud Run Jobs need private IP access to Cloud SQL:

1. Verify the VPC connector exists and is in the same region:
   ```bash
   gcloud compute networks vpc-access connectors describe finops-connector --region=<REGION>
   ```

2. Verify the Cloud Run Job is configured to use the connector:
   ```bash
   gcloud run jobs describe <job-name> --format='value(template.vpcAccess.connector)'
   ```

3. Check that the connector's subnet has enough IP addresses (each Cloud Run revision consumes one IP).

### Connection Pool Exhaustion

If `psycopg.OperationalError: connection pool exhausted` or `FATAL: sorry, too many clients already`:

```sql
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
```

If too many idle connections:
- Reduce the number of concurrent extractor jobs.
- Add connection timeout settings to `PG_DSN`: `?connect_timeout=10&options=-c idle_in_transaction_session_timeout=60000`.
- Increase Cloud SQL `max_connections` flag (requires instance restart).

---

## Exchange Rate Gaps

Missing exchange rates cause Azure costs in non-USD currencies to be treated as USD=1, producing inaccurate cost data.

### Identify Missing Rates

```sql
SELECT DISTINCT rate_date
FROM exchange_rates
WHERE rate_date >= '2026-03-01'
ORDER BY rate_date;
```

Missing weekdays (ECB publishes Monday through Friday) indicate a gap.

### Manual ECB API Check

Fetch the ECB feed directly to verify it is available:

```bash
curl -s "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml" | head -20
```

If the API is down, wait for it to recover and re-run the exchange_rates extractor.

### Re-run Exchange Rate Extractor

```bash
gcloud run jobs execute exchange-rates-extractor
```

The extractor always fetches the latest daily rates. For historical gaps, the ECB daily feed only provides the current day's rates. To backfill, use the ECB's 90-day historical feed:

```
https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml
```

Update the `ECB_URL` env var temporarily, run the extractor, then revert to the daily URL.