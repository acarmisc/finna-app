-- Wastage demo seed data — run with: psql $PG_DSN -f sql/seed/wastage_demo.sql
-- Creates a handful of representative wastage findings across providers + a sample scan run.
-- Safe to run multiple times (ON CONFLICT DO NOTHING).

-- ─────────────────────────────────────────────────────────────────────────────
-- Wastage findings
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO resource_wastage (
    finding_id, provider, account_id, resource_group, region,
    resource_id, resource_type, rule_id, severity, category,
    estimated_monthly_usd, currency, evidence, first_seen_at, last_seen_at,
    status, tags
) VALUES

-- Orphaned managed disk (Azure)
(
    'demo-azure-disk-orphan-001',
    'azure',
    'demo-sub-001',
    'rg-dev-platform',
    'westeurope',
    '/subscriptions/demo-sub-001/resourceGroups/rg-dev-platform/providers/Microsoft.Compute/disks/datadisk-old-01',
    'Microsoft.Compute/disks',
    'azure.disk.orphan',
    'high',
    'storage',
    18.43,
    'USD',
    '{"size_gb": 128, "sku": "Premium_LRS", "managed_by": null, "created": "2025-09-15T10:00:00Z"}'::jsonb,
    now() - interval '14 days',
    now() - interval '1 hour',
    'open',
    '{"environment": "dev"}'::jsonb
),

-- Unattached Standard Static public IP (Azure)
(
    'demo-azure-pip-unattached-001',
    'azure',
    'demo-sub-001',
    'rg-dev-platform',
    'westeurope',
    '/subscriptions/demo-sub-001/resourceGroups/rg-dev-platform/providers/Microsoft.Network/publicIPAddresses/pip-old-staging',
    'Microsoft.Network/publicIPAddresses',
    'azure.public_ip.unattached',
    'medium',
    'network',
    3.65,
    'USD',
    '{"sku": "Standard", "allocation_method": "Static", "ip_configuration": null}'::jsonb,
    now() - interval '30 days',
    now() - interval '2 hours',
    'open',
    '{"environment": "staging"}'::jsonb
),

-- Old snapshot > 180 days (Azure)
(
    'demo-azure-snapshot-old-001',
    'azure',
    'demo-sub-001',
    'rg-prod-backups',
    'westeurope',
    '/subscriptions/demo-sub-001/resourceGroups/rg-prod-backups/providers/Microsoft.Compute/snapshots/snap-2025-01-15',
    'Microsoft.Compute/snapshots',
    'azure.snapshot.old',
    'low',
    'storage',
    4.10,
    'USD',
    '{"size_gb": 200, "age_days": 222, "source_disk": "/subscriptions/demo-sub-001/resourceGroups/rg-prod/providers/Microsoft.Compute/disks/osdisk-vm-prod-01"}'::jsonb,
    now() - interval '60 days',
    now() - interval '3 hours',
    'open',
    '{}'::jsonb
),

-- Oversized App Service Plan in dev (Azure)
(
    'demo-azure-asp-oversized-001',
    'azure',
    'demo-sub-001',
    'rg-dev-apps',
    'westeurope',
    '/subscriptions/demo-sub-001/resourceGroups/rg-dev-apps/providers/Microsoft.Web/serverfarms/asp-dev-s2',
    'Microsoft.Web/serverfarms',
    'azure.asp.oversized_nonprod',
    'high',
    'compute',
    146.00,
    'USD',
    '{"sku_tier": "Standard", "sku_name": "S2", "number_of_workers": 1, "resource_group_pattern": "*dev*"}'::jsonb,
    now() - interval '7 days',
    now() - interval '30 minutes',
    'open',
    '{"environment": "dev", "team": "platform"}'::jsonb
),

-- Unattached EBS volume (AWS)
(
    'demo-aws-ebs-unattached-001',
    'aws',
    '123456789012',
    null,
    'eu-west-1',
    'vol-0abc1234def56789a',
    'AWS::EC2::Volume',
    'aws.ebs.unattached',
    'medium',
    'storage',
    12.29,
    'USD',
    '{"size_gb": 100, "volume_type": "gp3", "state": "available", "create_time": "2025-10-20T08:30:00Z"}'::jsonb,
    now() - interval '21 days',
    now() - interval '1 hour',
    'open',
    '{"team": "backend"}'::jsonb
),

-- Idle static External IP (GCP)
(
    'demo-gcp-static-ip-idle-001',
    'gcp',
    'demo-prod-platform-001',
    null,
    'europe-west1',
    'projects/demo-prod-platform-001/regions/europe-west1/addresses/legacy-lb-ip',
    'compute#address',
    'gcp.static_ip.unattached',
    'low',
    'network',
    7.30,
    'USD',
    '{"status": "RESERVED", "address_type": "EXTERNAL", "users": []}'::jsonb,
    now() - interval '45 days',
    now() - interval '5 hours',
    'acked',
    '{}'::jsonb
)

ON CONFLICT (finding_id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Sample scan run
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO wastage_scan_runs (id, provider, started_at, finished_at, status, findings_count, error)
VALUES (
    gen_random_uuid(),
    'azure',
    now() - interval '1 hour',
    now() - interval '55 minutes',
    'done',
    4,
    null
)
ON CONFLICT DO NOTHING;
