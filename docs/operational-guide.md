# FinOps Operational Guide

## Adding a New Extractor

1. Create `extractors/<name>.py` with a `main()` entrypoint
2. Normalize data to `NormalizedCostRecord`
3. Insert into `cost_records` with `ON CONFLICT DO NOTHING`
4. Track status in `extractor_health`
5. Register in `extractors/entrypoint.py`:

```python
EXTRACTOR_MAP = {
    "<name>": "extractors.<name>",
}
```

6. Build and deploy:

```bash
docker build -f Dockerfile.extractor -t finna-extractor .
```

## Adding a New Client

```bash
python -m onboarding.setup_client <client_id> \
    --providers gcp azure \
    --projects proj-1 proj-2
```

This generates:
- `clients/<client_id>/extractor_config.yaml`
- `clients/<client_id>/aggregation_config.yaml`
- `clients/registry.yaml` (updated)

Then:
1. Fill in real values in the generated configs
2. Deploy Cloud Run Jobs for each extractor
3. Test connectivity:

```bash
PG_DSN="postgresql://..." python clients/<client_id>/test_connectivity.py
```

## Backup Procedures

### Cloud SQL (Automated)
- Enabled by default, 7-day retention
- Verify: `gcloud sql backups list --instance=finops-prod`
- Restore: `gcloud sql backups restore <backup-id> --restore-instance=finops-prod`

### Manual pg_dump

```bash
# Full dump
pg_dump "$PG_DSN" --no-owner --no-privileges -Fc > backup_$(date +%Y%m%d).dump

# Restore
pg_restore --dbname="$PG_DSN" --no-owner --no-privileges backup_20260412.dump

# Docker environment
docker compose exec postgres pg_dump -U finops finops -Fc > backup.dump
```

**Recommended Schedule:**
- Cloud SQL auto: Daily, 7-day retention
- pg_dump: Weekly, 30-day retention
- Before migrations: On-demand, 90-day retention

## Scaling Extractors

Extractors run as Cloud Run Jobs. To scale:

1. **Increase parallelism** - Run multiple jobs with split date ranges
2. **Increase resources** - More CPU/memory for the job
3. **Increase batch size** - Set `BATCH_SIZE` env var (default: 500)
4. **Schedule more frequently** - Adjust Cloud Scheduler cron

**Note:** Respect cloud API rate limits (BigQuery, Azure Cost Management).

## Updating Seed Data

Seed data is in `sql/init.sql`. To modify:

1. Edit `sql/init.sql`
2. For fresh DB: `docker compose down -v && docker compose up -d postgres`
3. For existing DB: Run targeted INSERT statements manually

To add a project, add entries to the `INSERT INTO cost_records` blocks following existing patterns.
