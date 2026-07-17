# FinOps Troubleshooting Runbook

## Extractor Failures

### Check Health

```sql
SELECT extractor_name, status, last_run_start, last_run_end, 
       records_extracted, error_message, updated_at
FROM extractor_health 
ORDER BY updated_at DESC;
```

Status: `running` | `success` | `failed`

### Common Errors

**Authentication failure (401/403)**
- **GCP**: Verify service account has `roles/bigquery.dataViewer`
- **Azure**: Verify service principal has `Cost Management Reader` role
- Check credentials haven't expired/rotated

**Network connectivity**
- **GCP**: Ensure VPC connector has BigQuery/Cloud SQL access
- **Azure**: Ensure outbound internet access for Cost Management API
- Verify PostgreSQL is running: `docker compose ps postgres`

**API quota exceeded (429)**
- **GCP**: Reduce query frequency or request quota increase
- **Azure**: Space out extractor runs or reduce date range
- Increase `wait_exponential` backoff settings

**Extractor stuck in "running"**
Container was killed without cleanup. Reset manually:

```sql
UPDATE extractor_health 
SET status = 'failed', 
    error_message = 'Container killed without cleanup',
    last_run_end = now(),
    updated_at = now()
WHERE extractor_name = '<name>' AND status = 'running';
```

Prevent by increasing memory or reducing `BATCH_SIZE`.

## Data Gaps

### Identify Missing Data

```sql
SELECT date_trunc('day', usage_start)::date AS day, count(*) 
FROM cost_records 
WHERE provider = 'gcp' 
  AND project_id = 'ml-platform'
  AND usage_start >= '2026-03-01'
GROUP BY 1 ORDER BY 1;
```

### Re-run Extractors

```bash
# GCP
gcloud run jobs execute gcp-billing-extractor \
    --env-set DATE_FROM=2026-03-10,DATE_TO=2026-03-17

# Azure
gcloud run jobs execute azure-cost-extractor \
    --env-set DATE_FROM=2026-03-10,DATE_TO=2026-03-17
```

Extractors use `ON CONFLICT DO NOTHING` - safe to re-run over existing data.

### Refresh Materialized Views

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY daily_costs;
```

## Dashboard Issues

### Grafana Datasource Connection Problems

1. Test datasource in Grafana: Connections > Data sources > PostgreSQL > Save & Test
2. Verify PostgreSQL is accessible
3. Check SSL settings: add `?sslmode=require` to connection URI

### Dashboard Not Showing Data

- Open panel editor, click "Query", verify SQL runs directly
- Check table/column names match database schema
- Re-import dashboards:

```bash
cd grafana
./import-dashboards.sh http://localhost:3000 <your-grafana-api-key>
```

## PostgreSQL Issues

### Connection Pool Exhaustion

```sql
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
```

Fix: Reduce concurrent jobs, add connection timeouts, or increase `max_connections`.

### Cloud SQL Proxy

```bash
# Start proxy
./cloud-sql-proxy <PROJECT>:<REGION>:<INSTANCE> --port 5432 &

# Connect
psql "postgresql://finops:change-me-set-real-password@localhost:5432/finops"
```

Common issues:
- Proxy not installed or not in PATH
- Service account lacks `roles/cloudsql.client`
- Port conflict

### VPC Connector

Verify connector exists and is configured:

```bash
# Check connector
gcloud compute networks vpc-access connectors describe finops-connector --region=<REGION>

# Check Cloud Run Job uses connector
gcloud run jobs describe <job-name> --format='value(template.vpcAccess.connector)'
```

## Exchange Rate Gaps

Missing rates cause non-USD costs to be treated as USD=1.

### Check Missing Rates

```sql
SELECT DISTINCT rate_date FROM exchange_rates 
WHERE rate_date >= '2026-03-01' ORDER BY rate_date;
```

### Verify ECB API

```bash
curl -s "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml" | head -20
```

### Re-run Extractor

```bash
gcloud run jobs execute exchange-rates-extractor
```

For historical gaps, use the 90-day feed temporarily:
```bash
gcloud run jobs execute exchange-rates-extractor \
    --env-set ECB_URL="https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
```
