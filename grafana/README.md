# FinOps Grafana Dashboards

This folder contains ready-to-import Grafana dashboards for the finna-app FinOps platform.

## Quick Start (Bash)

The simplest way to import all dashboards:

```bash
cd grafana
./import-dashboards.sh http://localhost:3000 <your-grafana-api-key>
```

Or import manually via the Grafana UI (see instructions below).

## Dashboards

### 1. Cost Overview (`cost-overview.json`)
- Daily costs by provider (last 3 months)
- MTD cost comparison
- Month-over-month growth
- Top 10 projects by cost
- Cost breakdown by service category
- Cost heatmaps

### 2. Alerts Dashboard (`alerts-dashboard.json`)
- Alert status monitoring (firing/ack/resolved)
- Alerts by severity and provider trends
- Recent alerts table
- Cost impact tracking

### 3. Projects & Budgets (`projects-budgets.json`)
- Project registry overview
- Budget cap vs actual MTD spending
- Budget status indicators (OK/warning/over)
- Projects by provider and owner
- Budget utilization heatmap

### 4. Configurations & Extractors (`configurations-extractors.json`)
- Cloud configuration status (GCP/Azure/LLM)
- Configuration testing history
- Extractor association per configuration
- Test status heatmaps

### 5. Extractors & Runs (`extractors-runs.json`)
- Extractor registry (all providers)
- Enabled/idle/extraction status
- Run counts and success rates
- Schedule monitoring

### 6. Wastage Dashboard (`wastage-dashboard.json`)
- Resource wastage findings
- Status tracking (open/acked/resolved)
- Potential savings by category
- Provider-specific wastage breakdowns

## Import Instructions

### Option 1: Use the Import Script (Recommended)
```bash
./import-dashboards.sh <grafana-url> <api-key>

# Example:
./import-dashboards.sh http://localhost:3000 gfr_xxxxxxxxxxxxxxxx
```

### Option 2: Import via Grafana UI
1. Login to your Grafana instance
2. Go to **Dashboards** → **New** → **Import**
3. Upload each JSON file or paste the content
4. Select your PostgreSQL datasource when prompted
5. Click **Import**

### Option 3: Import via Dashboard API (Manual)
```bash
for dashboard in *.json; do
  curl -s -X POST http://localhost:3000/api/dashboard/import \
    -H "Content-Type: application/json" \
    -d @<($dashboard | sed "s|\\$DS_POSTGRES|$YOUR_DATASOURCE_UID|")
done
```

### Option 3: Import via Dashboard API (Manual)
```bash
for dashboard in *.json; do
  curl -s -X POST http://localhost:3000/api/dashboard/import \
    -H "Authorization: Bearer YOUR_API_KEY" \
    -H "Content-Type: application/json" \
    -d @($dashboard | jq -c '{dashboard: ., overwrite: true, message: "Imported from finna-app"}')
done
```

## Environment Variables

Before importing, ensure you have:
- PostgreSQL datasource configured in Grafana
- Network access to your finna-app PostgreSQL database

## Database Schema Dependencies

All dashboards depend on the finna-app schema:
- `cost_records` - cost data with provider/project/service dimensions
- `alerts` - budget and anomaly alerts
- `fin_projects` - project budgets and metadata
- `cloud_config` - cloud provider configurations
- `extractors` - extractor registry
- `extractor_runs` - extraction history
- `resource_wastage` - wastage findings

## Customization

You can customize any dashboard by:
1. Editing JSON directly
2. Using Grafana UI after import
3. Modifying query parameters
4. Adjusting alert thresholds

## Support

For issues or questions:
- Check finna-app documentation
- Review PostgreSQL logs
- Verify datasource connectivity in Grafana
