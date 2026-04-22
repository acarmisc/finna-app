# FinOps Operational Guide

This guide covers common operational tasks for the FinOps multi-cloud monitoring platform.

---

## Adding a New Extractor Type

1. **Create the extractor module** in `extractors/<name>.py`. It must:
   - Define a `main()` function as the Cloud Run Job entrypoint.
   - Read configuration from environment variables (see existing extractors for the pattern).
   - Normalize raw data into `NormalizedCostRecord` instances.
   - Insert records into `cost_records` using `ON CONFLICT (record_id) DO NOTHING` for idempotency.
   - Track health in the `extractor_health` table (mark running/success/failed).

2. **Register the extractor** in `extractors/entrypoint.py` by adding it to `EXTRACTOR_MAP`:
   ```python
   EXTRACTOR_MAP = {
       ...
       "<name>": "extractors.<name>",
   }
   ```

3. **Add required env vars** to the client's `extractor_config.yaml` (update `onboarding/setup_client.py` if the extractor should be auto-configured for new clients).

4. **Deploy** by rebuilding the Docker image:
   ```bash
   docker build -f Dockerfile.extractor -t finops-extractor .
   ```

5. **Create a Cloud Run Job** that sets `EXTRACTOR_TYPE=<name>` and the required environment variables.

6. **Verify** by running the job manually and checking `extractor_health`:
   ```sql
   SELECT * FROM extractor_health WHERE extractor_name = '<name>';
   ```

---

## Queries & Insights

Ready-to-run SQL queries for metrics, trends, and anomaly detection are in [`queries/QUERIES.md`](../queries/QUERIES.md).

Connect any SQL client or BI tool directly to the PostgreSQL database:

```bash
psql $PG_DSN
```

---

## Adding a New Client

Use the onboarding script for idempotent client setup:

```bash
python -m onboarding.setup_client <client_id> \
    --providers gcp azure \
    --projects proj-1 proj-2
```

This generates:
- `clients/<client_id>/extractor_config.yaml` -- Env var config per extractor
- `clients/<client_id>/aggregation_config.yaml` -- Per-client aggregation settings
- `clients/<client_id>/test_connectivity.py` -- Connectivity test script
- `clients/registry.yaml` -- Updated registry entry

After running the script:
1. Fill in real values for placeholders (subscription IDs, tenant IDs, secrets) in the generated config files.
2. Deploy Cloud Run Jobs for each enabled extractor type.
4. Run the connectivity test:
   ```bash
   PG_DSN="postgresql://finops:...@host/finops" python clients/<client_id>/test_connectivity.py
   ```

Re-running the script is safe; it updates existing configs without errors.

---

## Updating Seed Data

Seed data is defined in `sql/init.sql` and loaded on first PostgreSQL startup via the Docker entrypoint.

### To modify seed data

1. Edit `sql/init.sql`. The seed section is clearly labeled.
2. For a fresh database, drop and recreate:
   ```bash
   docker compose down -v   # removes pg_data volume
   docker compose up -d postgres
   ```
3. For an existing database without losing real data, run incremental inserts manually:
   ```bash
   psql "$PG_DSN" -f sql/init.sql  # only safe on a fresh DB
   ```
   For incremental changes, write targeted INSERT statements and run them directly.

### To add a new seed project

Add a new entry to the project arrays in the `INSERT INTO cost_records` blocks for each provider. Follow the existing pattern of array indexing.

---

## Backup Procedures

### Cloud SQL Automated Backups

Google Cloud SQL for PostgreSQL provides automated backups:

- **Enabled by default** on production instances.
- **Retention**: 7 days (configurable up to 365 days).
- **Location**: Same region as the instance (configure cross-region for DR).

Verify automated backups:
```bash
gcloud sql backups list --instance=finops-prod
```

Restore from a backup:
```bash
gcloud sql backups restore <backup-id> --restore-instance=finops-prod
```

### Manual pg_dump

For point-in-time snapshots or offsite backups:

```bash
# Full database dump
pg_dump "$PG_DSN" --no-owner --no-privileges -Fc > backup_$(date +%Y%m%d).dump

# Restore
pg_restore --dbname="$PG_DSN" --no-owner --no-privileges backup_20260412.dump
```

For local Docker environments:
```bash
docker compose exec postgres pg_dump -U finops finops -Fc > backup_$(date +%Y%m%d).dump
```

### Recommended Backup Schedule

| Method         | Frequency   | Retention | Notes                          |
|----------------|-------------|-----------|--------------------------------|
| Cloud SQL auto | Daily       | 7 days    | Production only                |
| pg_dump        | Weekly      | 30 days   | Store in GCS, all environments |
| pg_dump        | Before migrations | 90 days | On-demand, before schema changes |

---

## Scaling Extractors

Extractors run as Cloud Run Jobs. Scaling is achieved by adjusting concurrency and resource allocation.

### Increase Cloud Run Concurrency

Each Cloud Run Job executes in a single container. To process data faster:

1. **Increase parallelism** within the extractor by reducing the date range per job and running multiple jobs:
   ```bash
   # Run 4 jobs in parallel, each covering a week
   gcloud run jobs execute gcp-billing-extractor \
       --env-set DATE_FROM=2026-03-01,DATE_TO=2026-03-08
   gcloud run jobs execute gcp-billing-extractor \
       --env-set DATE_FROM=2026-03-08,DATE_TO=2026-03-15
   # ... etc
   ```

2. **Increase CPU/memory** for the Cloud Run Job:
   ```bash
   gcloud run jobs update gcp-billing-extractor \
       --cpu 4 --memory 2Gi
   ```

3. **Increase batch size** via the `BATCH_SIZE` env var (default: 500):
   ```bash
   gcloud run jobs update gcp-billing-extractor \
       --env-set BATCH_SIZE=2000
   ```

4. **Schedule more frequent runs** via Cloud Scheduler if the job is triggered on a cron schedule.

### Considerations

- BigQuery and Azure Cost Management APIs have their own rate limits. Increasing parallelism beyond those limits will result in throttling.
- PostgreSQL connection count is limited by the Cloud SQL instance size. Monitor `pg_stat_activity` for connection saturation.
- The `ON CONFLICT DO NOTHING` pattern ensures idempotency when running overlapping date ranges.