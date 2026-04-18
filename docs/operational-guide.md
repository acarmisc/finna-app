# FinOps Operational Guide

This guide covers common operational tasks for the FinOps multi-cloud monitoring platform.

---

## Adding a New Extractor Type

Finna now uses a **Plugin-based system**.

1.  **Create the extractor plugin** in `extractors/`. See [Extractor Plugin Guide](./plugins-guide.md) for implementation details.
2.  **Register the plugin**: 
    -   Add it to `extractors/plugins.py` for built-in support.
    -   Or set the `EXTRACTOR_PLUGINS` env var for external modules.

The legacy method of modifying `extractors/entrypoint.py` still works for standalone job execution but is being phased out in favor of the registry-driven orchestrator.

---

## Updating Seed Data

There are two ways to manage seed data:

### 1. Simple Seeding (Recommended for Dev)
Use the JSON-based seeding script. This is the fastest way to populate the UI.
1.  Edit `fixtures/sample_data.json`.
2.  Run `make seed`.

### 2. SQL-based Seeding (Legacy/Bulk)
Seed data can also be defined in `sql/init.sql`. Note that this file is currently excluded from the default Docker Compose startup to avoid conflicts with Alembic migrations.

To load it manually:
```bash
psql "$PG_DSN" -f sql/init.sql
```


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