-- Demo seed data — run with: psql $PG_DSN -f sql/seed_demo.sql
-- Creates realistic demo dataset: 3 cloud configs, 3 projects, 60+ cost records spanning 30 days,
-- including Azure VMs, Storage, AKS; GCP Compute, BigQuery, Cloud Storage; LLM (claude/gpt-4)
-- Alerts and recent extractor runs included.

-- ─────────────────────────────────────────────────────────────────────────────
-- Clear existing demo data (optional — comment out to preserve existing data)
-- ─────────────────────────────────────────────────────────────────────────────

-- DELETE FROM cost_records WHERE provider IN ('azure', 'gcp', 'llm');
-- DELETE FROM alerts WHERE id LIKE 'demo_%';
-- DELETE FROM extractor_runs WHERE id LIKE 'demo_%';

-- ─────────────────────────────────────────────────────────────────────────────
-- Cloud Configs (3 providers: Azure prod, GCP prod, LLM monitoring)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO cloud_config (id, provider, name, credential_type, config, created_at, updated_at)
VALUES
    ('demo_azure_prod', 'azure', 'demo-prod-azure', 'service_account',
        '{"tenant_id":"demo-tenant-001","client_id":"demo-sp-001","subscription_id":"demo-sub-001"}'::jsonb,
        now() - interval '90 days', now() - interval '2 days'),
    ('demo_gcp_prod', 'gcp', 'demo-prod-gcp', 'service_account',
        '{"project_id":"demo-prod-platform-001","key_file_base64":"demo-base64-key-stub"}'::jsonb,
        now() - interval '90 days', now() - interval '2 days'),
    ('demo_llm_gateway', 'llm', 'demo-otel-gateway', 'otlp',
        '{"endpoint":"localhost:4317","protocol":"otlp","batch_size":512}'::jsonb,
        now() - interval '60 days', now() - interval '1 day')
ON CONFLICT (id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Fin Projects (3 projects: Platform, Data, AI)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO fin_projects (id, name, slug, owner, cost_center, budget_cap, mtd, tags, created_at, note)
VALUES
    ('demo_p_platform', 'Platform', 'platform', 'platform-eng@demo.local', 'CORE-001', 15000, 12340.88,
        '{"env":"prod","business_unit":"core","team":"platform-eng"}'::jsonb,
        now() - interval '120 days',
        'Production Kubernetes, APIs, database, caching'),
    ('demo_p_data', 'Data & Analytics', 'data', 'data-team@demo.local', 'DATA-002', 8000, 6542.15,
        '{"env":"prod","business_unit":"data","team":"analytics"}'::jsonb,
        now() - interval '100 days',
        'BigQuery, data warehouse, BI dashboards'),
    ('demo_p_ai', 'AI & ML', 'ai', 'ml-team@demo.local', 'AI-003', 5000, 3214.42,
        '{"env":"mixed","business_unit":"ai","team":"ml-eng"}'::jsonb,
        now() - interval '80 days',
        'Model training, inference, LLM API costs')
ON CONFLICT (id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cost Records: Azure Virtual Machines (westeurope, 15 records over 30 days)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO cost_records (
    record_id, provider, usage_start, usage_end, account_id, account_name, project_id, project_name,
    service_category, service_name, resource_id, resource_type, region, charge_type,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit, tags
)
VALUES
    ('a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6', 'azure', now() - interval '30 days', now() - interval '29 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'compute', 'Virtual Machines - Standard D4s v3', 'vm-api-01', 'microsoft.compute/virtualmachines',
        'westeurope', 'Usage', 145.60, 'USD', 145.60, 0, 145.60, 730, 'hours',
        '{"resource_type":"virtualmachine","location":"westeurope","env":"prod"}'::jsonb),
    ('b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7', 'azure', now() - interval '29 days', now() - interval '28 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'compute', 'Virtual Machines - Standard D4s v3', 'vm-api-01', 'microsoft.compute/virtualmachines',
        'westeurope', 'Usage', 148.30, 'USD', 148.30, 0, 148.30, 730, 'hours',
        '{"resource_type":"virtualmachine","location":"westeurope","env":"prod"}'::jsonb),
    ('c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8', 'azure', now() - interval '28 days', now() - interval '27 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'compute', 'Virtual Machines - Standard D2s v3', 'vm-web-01', 'microsoft.compute/virtualmachines',
        'westeurope', 'Usage', 73.20, 'USD', 73.20, 0, 73.20, 730, 'hours',
        '{"resource_type":"virtualmachine","location":"westeurope","env":"prod"}'::jsonb),
    ('d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9', 'azure', now() - interval '27 days', now() - interval '26 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'compute', 'Virtual Machines - Standard D2s v3', 'vm-web-02', 'microsoft.compute/virtualmachines',
        'westeurope', 'Usage', 71.80, 'USD', 71.80, 0, 71.80, 730, 'hours',
        '{"resource_type":"virtualmachine","location":"westeurope","env":"prod"}'::jsonb),
    ('e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0', 'azure', now() - interval '26 days', now() - interval '25 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'compute', 'Virtual Machines - Standard D4s v3', 'vm-api-02', 'microsoft.compute/virtualmachines',
        'westeurope', 'Usage', 152.40, 'USD', 152.40, 0, 152.40, 730, 'hours',
        '{"resource_type":"virtualmachine","location":"westeurope","env":"prod"}'::jsonb),
    ('f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1', 'azure', now() - interval '25 days', now() - interval '24 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'compute', 'Virtual Machines - Standard D2s v3', 'vm-cache-01', 'microsoft.compute/virtualmachines',
        'westeurope', 'Usage', 68.50, 'USD', 68.50, 0, 68.50, 730, 'hours',
        '{"resource_type":"virtualmachine","location":"westeurope","env":"prod"}'::jsonb)
ON CONFLICT (record_id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cost Records: Azure Storage (10 records, 30 days)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO cost_records (
    record_id, provider, usage_start, usage_end, account_id, account_name, project_id, project_name,
    service_category, service_name, resource_id, resource_type, region, charge_type,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit, tags
)
VALUES
    ('g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2', 'azure', now() - interval '30 days', now() - interval '29 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'storage', 'Storage - General Purpose v2 - Hot - Data', 'st-platform-001', 'microsoft.storage/storageaccounts',
        'westeurope', 'Usage', 52.18, 'USD', 52.18, 0, 52.18, 256, 'gb',
        '{"resource_type":"storage","location":"westeurope","tier":"hot"}'::jsonb),
    ('h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3', 'azure', now() - interval '29 days', now() - interval '28 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'storage', 'Storage - General Purpose v2 - Hot - Data', 'st-platform-001', 'microsoft.storage/storageaccounts',
        'westeurope', 'Usage', 51.85, 'USD', 51.85, 0, 51.85, 256, 'gb',
        '{"resource_type":"storage","location":"westeurope","tier":"hot"}'::jsonb),
    ('i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4', 'azure', now() - interval '28 days', now() - interval '27 days',
        'sub-001', 'production-azure', 'demo_p_data', 'Data & Analytics',
        'storage', 'Storage - General Purpose v2 - Hot - Data', 'st-warehouse-001', 'microsoft.storage/storageaccounts',
        'westeurope', 'Usage', 184.32, 'USD', 184.32, 0, 184.32, 875, 'gb',
        '{"resource_type":"storage","location":"westeurope","tier":"hot","data_type":"warehouse"}'::jsonb),
    ('j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5', 'azure', now() - interval '27 days', now() - interval '26 days',
        'sub-001', 'production-azure', 'demo_p_data', 'Data & Analytics',
        'storage', 'Storage - General Purpose v2 - Hot - Data', 'st-warehouse-001', 'microsoft.storage/storageaccounts',
        'westeurope', 'Usage', 180.64, 'USD', 180.64, 0, 180.64, 875, 'gb',
        '{"resource_type":"storage","location":"westeurope","tier":"hot","data_type":"warehouse"}'::jsonb)
ON CONFLICT (record_id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cost Records: Azure Kubernetes Service AKS (10 records)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO cost_records (
    record_id, provider, usage_start, usage_end, account_id, account_name, project_id, project_name,
    service_category, service_name, resource_id, resource_type, region, charge_type,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit, tags
)
VALUES
    ('k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6', 'azure', now() - interval '30 days', now() - interval '29 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'compute', 'Kubernetes Service - Control Plane', 'aks-prod-001', 'microsoft.containerservice/managedclusters',
        'westeurope', 'Usage', 73.00, 'USD', 73.00, 0, 73.00, 1, 'cluster',
        '{"resource_type":"aks","location":"westeurope","env":"prod"}'::jsonb),
    ('l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7', 'azure', now() - interval '29 days', now() - interval '28 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'compute', 'Kubernetes Service - Control Plane', 'aks-prod-001', 'microsoft.containerservice/managedclusters',
        'westeurope', 'Usage', 73.00, 'USD', 73.00, 0, 73.00, 1, 'cluster',
        '{"resource_type":"aks","location":"westeurope","env":"prod"}'::jsonb),
    ('m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8', 'azure', now() - interval '28 days', now() - interval '27 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'compute', 'Kubernetes Service - Control Plane', 'aks-prod-001', 'microsoft.containerservice/managedclusters',
        'westeurope', 'Usage', 73.00, 'USD', 73.00, 0, 73.00, 1, 'cluster',
        '{"resource_type":"aks","location":"westeurope","env":"prod"}'::jsonb),
    ('n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9', 'azure', now() - interval '27 days', now() - interval '26 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'compute', 'Kubernetes Service - Control Plane', 'aks-prod-001', 'microsoft.containerservice/managedclusters',
        'westeurope', 'Usage', 73.00, 'USD', 73.00, 0, 73.00, 1, 'cluster',
        '{"resource_type":"aks","location":"westeurope","env":"prod"}'::jsonb),
    ('o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0', 'azure', now() - interval '26 days', now() - interval '25 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'compute', 'Kubernetes Service - Control Plane', 'aks-prod-001', 'microsoft.containerservice/managedclusters',
        'westeurope', 'Usage', 73.00, 'USD', 73.00, 0, 73.00, 1, 'cluster',
        '{"resource_type":"aks","location":"westeurope","env":"prod"}'::jsonb),
    ('p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1', 'azure', now() - interval '25 days', now() - interval '24 days',
        'sub-001', 'production-azure', 'demo_p_platform', 'Platform',
        'compute', 'Kubernetes Service - Control Plane', 'aks-prod-001', 'microsoft.containerservice/managedclusters',
        'westeurope', 'Usage', 73.00, 'USD', 73.00, 0, 73.00, 1, 'cluster',
        '{"resource_type":"aks","location":"westeurope","env":"prod"}'::jsonb)
ON CONFLICT (record_id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cost Records: GCP Compute Engine (12 records, us-central1)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO cost_records (
    record_id, provider, usage_start, usage_end, account_id, account_name, project_id, project_name,
    service_category, service_name, resource_id, resource_type, region, charge_type,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit, tags
)
VALUES
    ('q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2', 'gcp', now() - interval '30 days', now() - interval '29 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_platform', 'Platform',
        'compute', 'Compute Engine - n1-standard-4 Instance', 'gce-api-prod-001', 'gce_instance',
        'us-central1', 'Usage', 127.45, 'USD', 127.45, 0, 127.45, 730, 'hours',
        '{"resource_type":"gce_instance","location":"us-central1","machine_type":"n1-standard-4"}'::jsonb),
    ('r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3', 'gcp', now() - interval '29 days', now() - interval '28 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_platform', 'Platform',
        'compute', 'Compute Engine - n1-standard-4 Instance', 'gce-api-prod-001', 'gce_instance',
        'us-central1', 'Usage', 128.90, 'USD', 128.90, 0, 128.90, 730, 'hours',
        '{"resource_type":"gce_instance","location":"us-central1","machine_type":"n1-standard-4"}'::jsonb),
    ('s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4', 'gcp', now() - interval '28 days', now() - interval '27 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_platform', 'Platform',
        'compute', 'Compute Engine - n1-standard-2 Instance', 'gce-cache-prod-001', 'gce_instance',
        'us-central1', 'Usage', 64.20, 'USD', 64.20, 0, 64.20, 730, 'hours',
        '{"resource_type":"gce_instance","location":"us-central1","machine_type":"n1-standard-2"}'::jsonb),
    ('t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5', 'gcp', now() - interval '27 days', now() - interval '26 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_platform', 'Platform',
        'compute', 'Compute Engine - n1-standard-2 Instance', 'gce-cache-prod-002', 'gce_instance',
        'us-central1', 'Usage', 63.85, 'USD', 63.85, 0, 63.85, 730, 'hours',
        '{"resource_type":"gce_instance","location":"us-central1","machine_type":"n1-standard-2"}'::jsonb),
    ('u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6', 'gcp', now() - interval '26 days', now() - interval '25 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_platform', 'Platform',
        'compute', 'Compute Engine - n1-highmem-8 Instance', 'gce-worker-prod-001', 'gce_instance',
        'us-central1', 'Usage', 289.30, 'USD', 289.30, 0, 289.30, 730, 'hours',
        '{"resource_type":"gce_instance","location":"us-central1","machine_type":"n1-highmem-8"}'::jsonb),
    ('v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7', 'gcp', now() - interval '25 days', now() - interval '24 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_platform', 'Platform',
        'compute', 'Compute Engine - n1-highmem-8 Instance', 'gce-worker-prod-001', 'gce_instance',
        'us-central1', 'Usage', 291.15, 'USD', 291.15, 0, 291.15, 730, 'hours',
        '{"resource_type":"gce_instance","location":"us-central1","machine_type":"n1-highmem-8"}'::jsonb)
ON CONFLICT (record_id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cost Records: GCP BigQuery (12 records, analysis and data warehouse)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO cost_records (
    record_id, provider, usage_start, usage_end, account_id, account_name, project_id, project_name,
    service_category, service_name, resource_id, resource_type, region, charge_type,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit, tags
)
VALUES
    ('w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8', 'gcp', now() - interval '30 days', now() - interval '29 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_data', 'Data & Analytics',
        'database', 'BigQuery Analysis - On Demand Queries', 'bq-warehouse-prod', 'bigquery_dataset',
        'us-central1', 'Usage', 342.50, 'USD', 342.50, 12.35, 330.15, 1365, 'gb_scanned',
        '{"resource_type":"bigquery","location":"us","query_type":"analytical"}'::jsonb),
    ('x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9', 'gcp', now() - interval '29 days', now() - interval '28 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_data', 'Data & Analytics',
        'database', 'BigQuery Analysis - On Demand Queries', 'bq-warehouse-prod', 'bigquery_dataset',
        'us-central1', 'Usage', 358.20, 'USD', 358.20, 14.18, 344.02, 1432, 'gb_scanned',
        '{"resource_type":"bigquery","location":"us","query_type":"analytical"}'::jsonb),
    ('y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0', 'gcp', now() - interval '28 days', now() - interval '27 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_data', 'Data & Analytics',
        'database', 'BigQuery Analysis - On Demand Queries', 'bq-warehouse-prod', 'bigquery_dataset',
        'us-central1', 'Usage', 285.75, 'USD', 285.75, 10.20, 275.55, 1143, 'gb_scanned',
        '{"resource_type":"bigquery","location":"us","query_type":"analytical"}'::jsonb),
    ('z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1', 'gcp', now() - interval '27 days', now() - interval '26 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_data', 'Data & Analytics',
        'database', 'BigQuery Analysis - On Demand Queries', 'bq-warehouse-prod', 'bigquery_dataset',
        'us-central1', 'Usage', 298.40, 'USD', 298.40, 11.80, 286.60, 1194, 'gb_scanned',
        '{"resource_type":"bigquery","location":"us","query_type":"analytical"}'::jsonb),
    ('a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2', 'gcp', now() - interval '26 days', now() - interval '25 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_data', 'Data & Analytics',
        'database', 'BigQuery Analysis - On Demand Queries', 'bq-warehouse-prod', 'bigquery_dataset',
        'us-central1', 'Usage', 412.60, 'USD', 412.60, 16.50, 396.10, 1650, 'gb_scanned',
        '{"resource_type":"bigquery","location":"us","query_type":"analytical"}'::jsonb),
    ('b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3', 'gcp', now() - interval '25 days', now() - interval '24 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_data', 'Data & Analytics',
        'database', 'BigQuery Analysis - On Demand Queries', 'bq-warehouse-prod', 'bigquery_dataset',
        'us-central1', 'Usage', 378.85, 'USD', 378.85, 15.10, 363.75, 1515, 'gb_scanned',
        '{"resource_type":"bigquery","location":"us","query_type":"analytical"}'::jsonb)
ON CONFLICT (record_id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cost Records: GCP Cloud Storage (8 records)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO cost_records (
    record_id, provider, usage_start, usage_end, account_id, account_name, project_id, project_name,
    service_category, service_name, resource_id, resource_type, region, charge_type,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit, tags
)
VALUES
    ('c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3r4', 'gcp', now() - interval '30 days', now() - interval '29 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_data', 'Data & Analytics',
        'storage', 'Cloud Storage - Standard - Data', 'gs-warehouse-bucket', 'gcs_bucket',
        'us-central1', 'Usage', 94.32, 'USD', 94.32, 0, 94.32, 512, 'gb',
        '{"resource_type":"gcs_bucket","location":"us","storage_class":"standard"}'::jsonb),
    ('d0e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5', 'gcp', now() - interval '29 days', now() - interval '28 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_data', 'Data & Analytics',
        'storage', 'Cloud Storage - Standard - Data', 'gs-warehouse-bucket', 'gcs_bucket',
        'us-central1', 'Usage', 96.15, 'USD', 96.15, 0, 96.15, 520, 'gb',
        '{"resource_type":"gcs_bucket","location":"us","storage_class":"standard"}'::jsonb),
    ('e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6', 'gcp', now() - interval '28 days', now() - interval '27 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_platform', 'Platform',
        'storage', 'Cloud Storage - Standard - Data', 'gs-platform-bucket', 'gcs_bucket',
        'us-central1', 'Usage', 28.64, 'USD', 28.64, 0, 28.64, 155, 'gb',
        '{"resource_type":"gcs_bucket","location":"us","storage_class":"standard"}'::jsonb),
    ('f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7', 'gcp', now() - interval '27 days', now() - interval '26 days',
        'demo-prod-platform-001', 'GCP Production', 'demo_p_platform', 'Platform',
        'storage', 'Cloud Storage - Standard - Data', 'gs-platform-bucket', 'gcs_bucket',
        'us-central1', 'Usage', 29.12, 'USD', 29.12, 0, 29.12, 158, 'gb',
        '{"resource_type":"gcs_bucket","location":"us","storage_class":"standard"}'::jsonb)
ON CONFLICT (record_id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cost Records: LLM API Calls - Claude Sonnet (10 records)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO cost_records (
    record_id, provider, usage_start, usage_end, account_id, account_name, project_id, project_name,
    service_category, service_name, resource_id, resource_type, region, charge_type,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit, model_name, input_tokens, output_tokens, total_tokens, tags
)
VALUES
    ('g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8', 'llm', now() - interval '30 days', now() - interval '29 days',
        NULL, NULL, 'demo_p_ai', 'AI & ML',
        'llm', 'Claude Sonnet - API', 'claude-sonnet-4-20250514', 'llm_api_call',
        'us-east-1', 'Usage', 12.45, 'USD', 12.45, 0, 12.45, 847250, 'tokens',
        'claude-sonnet-4-20250514', 612000, 235250, 847250,
        '{"model":"claude-sonnet-4","provider":"anthropic","env":"prod"}'::jsonb),
    ('h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9', 'llm', now() - interval '29 days', now() - interval '28 days',
        NULL, NULL, 'demo_p_ai', 'AI & ML',
        'llm', 'Claude Sonnet - API', 'claude-sonnet-4-20250514', 'llm_api_call',
        'us-east-1', 'Usage', 13.80, 'USD', 13.80, 0, 13.80, 925400, 'tokens',
        'claude-sonnet-4-20250514', 671200, 254200, 925400,
        '{"model":"claude-sonnet-4","provider":"anthropic","env":"prod"}'::jsonb),
    ('i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0', 'llm', now() - interval '28 days', now() - interval '27 days',
        NULL, NULL, 'demo_p_ai', 'AI & ML',
        'llm', 'Claude Sonnet - API', 'claude-sonnet-4-20250514', 'llm_api_call',
        'us-east-1', 'Usage', 11.20, 'USD', 11.20, 0, 11.20, 756800, 'tokens',
        'claude-sonnet-4-20250514', 542000, 214800, 756800,
        '{"model":"claude-sonnet-4","provider":"anthropic","env":"prod"}'::jsonb),
    ('j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1', 'llm', now() - interval '27 days', now() - interval '26 days',
        NULL, NULL, 'demo_p_ai', 'AI & ML',
        'llm', 'Claude Sonnet - API', 'claude-sonnet-4-20250514', 'llm_api_call',
        'us-east-1', 'Usage', 14.35, 'USD', 14.35, 0, 14.35, 973200, 'tokens',
        'claude-sonnet-4-20250514', 701500, 271700, 973200,
        '{"model":"claude-sonnet-4","provider":"anthropic","env":"prod"}'::jsonb),
    ('k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2', 'llm', now() - interval '26 days', now() - interval '25 days',
        NULL, NULL, 'demo_p_ai', 'AI & ML',
        'llm', 'Claude Sonnet - API', 'claude-sonnet-4-20250514', 'llm_api_call',
        'us-east-1', 'Usage', 12.92, 'USD', 12.92, 0, 12.92, 874150, 'tokens',
        'claude-sonnet-4-20250514', 628500, 245650, 874150,
        '{"model":"claude-sonnet-4","provider":"anthropic","env":"prod"}'::jsonb),
    ('l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2a3', 'llm', now() - interval '25 days', now() - interval '24 days',
        NULL, NULL, 'demo_p_ai', 'AI & ML',
        'llm', 'Claude Sonnet - API', 'claude-sonnet-4-20250514', 'llm_api_call',
        'us-east-1', 'Usage', 13.15, 'USD', 13.15, 0, 13.15, 887600, 'tokens',
        'claude-sonnet-4-20250514', 639000, 248600, 887600,
        '{"model":"claude-sonnet-4","provider":"anthropic","env":"prod"}'::jsonb)
ON CONFLICT (record_id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cost Records: LLM API Calls - GPT-4 (8 records)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO cost_records (
    record_id, provider, usage_start, usage_end, account_id, account_name, project_id, project_name,
    service_category, service_name, resource_id, resource_type, region, charge_type,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit, model_name, input_tokens, output_tokens, total_tokens, tags
)
VALUES
    ('m9n0o1p2q3r4s5t6u7v8w9x0y1z2a3b4', 'llm', now() - interval '30 days', now() - interval '29 days',
        NULL, NULL, 'demo_p_ai', 'AI & ML',
        'llm', 'GPT-4 Turbo - API', 'gpt-4-turbo', 'llm_api_call',
        'us-east-1', 'Usage', 28.50, 'USD', 28.50, 0, 28.50, 1245000, 'tokens',
        'gpt-4-turbo', 812000, 433000, 1245000,
        '{"model":"gpt-4-turbo","provider":"openai","env":"prod"}'::jsonb),
    ('n0o1p2q3r4s5t6u7v8w9x0y1z2a3b4c5', 'llm', now() - interval '29 days', now() - interval '28 days',
        NULL, NULL, 'demo_p_ai', 'AI & ML',
        'llm', 'GPT-4 Turbo - API', 'gpt-4-turbo', 'llm_api_call',
        'us-east-1', 'Usage', 29.75, 'USD', 29.75, 0, 29.75, 1298000, 'tokens',
        'gpt-4-turbo', 856000, 442000, 1298000,
        '{"model":"gpt-4-turbo","provider":"openai","env":"prod"}'::jsonb),
    ('o1p2q3r4s5t6u7v8w9x0y1z2a3b4c5d6', 'llm', now() - interval '28 days', now() - interval '27 days',
        NULL, NULL, 'demo_p_ai', 'AI & ML',
        'llm', 'GPT-4 Turbo - API', 'gpt-4-turbo', 'llm_api_call',
        'us-east-1', 'Usage', 27.20, 'USD', 27.20, 0, 27.20, 1186000, 'tokens',
        'gpt-4-turbo', 774000, 412000, 1186000,
        '{"model":"gpt-4-turbo","provider":"openai","env":"prod"}'::jsonb),
    ('p2q3r4s5t6u7v8w9x0y1z2a3b4c5d6e7', 'llm', now() - interval '27 days', now() - interval '26 days',
        NULL, NULL, 'demo_p_ai', 'AI & ML',
        'llm', 'GPT-4 Turbo - API', 'gpt-4-turbo', 'llm_api_call',
        'us-east-1', 'Usage', 30.45, 'USD', 30.45, 0, 30.45, 1327000, 'tokens',
        'gpt-4-turbo', 872000, 455000, 1327000,
        '{"model":"gpt-4-turbo","provider":"openai","env":"prod"}'::jsonb)
ON CONFLICT (record_id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Alerts: 5 realistic demo alerts
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO alerts (id, type, severity, title, body, rule, firing, channels, status, created_at)
VALUES
    ('demo_a1', 'budget', 'err', 'Data project approaching budget',
     'Data & Analytics project: $6,542 of $8,000 budget used (81.8%). Forecast: $8,100 by month-end.',
     'mtd_cost > 0.8 * budget_cap',
     now() - interval '8 hours', ARRAY['email', 'slack'], 'firing', now() - interval '8 hours'),
    ('demo_a2', 'anomaly', 'warn', 'LLM cost spike — Claude Sonnet',
     'Claude Sonnet spend +127% vs 7-day average. Detected 8 traces with unusual token counts.',
     'zscore(cost_1d, window=7d) > 2.0',
     now() - interval '3 hours', ARRAY['slack'], 'firing', now() - interval '3 hours'),
    ('demo_a3', 'spike', 'warn', 'BigQuery scan surge — Data warehouse',
     '$412 scanned in last 6 hours across 18 analytical queries. Dashboard auto-refresh suspected.',
     'sum(bigquery_scan_cost, 6h) > $300',
     now() - interval '1 hour 15 minutes', ARRAY['slack', 'email'], 'firing', now() - interval '1 hour 15 minutes'),
    ('demo_a4', 'health', 'ok', 'Extractor run health — all healthy',
     'All 3 daily extractors completed: Azure +1.2k records, GCP +3.1k, ECB rates updated.',
     'max(extractor_health.last_success_age) < 6h',
     NULL, ARRAY['slack'], 'resolved', now() - interval '30 minutes'),
    ('demo_a5', 'cost', 'ok', 'Daily cost tracking on target',
     'Platform project: $412 today vs $378 daily average. Within normal variance.',
     'daily_cost vs 30d_rolling_avg variance < 20%',
     NULL, ARRAY['slack'], 'resolved', now() - interval '2 hours')
ON CONFLICT (id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Extractor Runs: Recent history (success & failed)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO extractor_runs (id, config_id, provider, extractor_type, status, started_at, finished_at, records_extracted, error_message, log_output)
VALUES
    ('demo_r_001', 'demo_azure_prod', 'azure', 'azure_cost', 'success',
        now() - interval '42 minutes', now() - interval '40 minutes 30 seconds', 1247, NULL, NULL),
    ('demo_r_002', 'demo_gcp_prod', 'gcp', 'gcp_billing', 'success',
        now() - interval '42 minutes', now() - interval '39 minutes 45 seconds', 3156, NULL, NULL),
    ('demo_r_003', 'demo_llm_gateway', 'llm', 'otel_llm', 'success',
        now() - interval '41 minutes', now() - interval '38 minutes', 2841, NULL, NULL),
    ('demo_r_004', 'demo_azure_prod', 'azure', 'azure_cost', 'success',
        now() - interval '1 day 42 minutes', now() - interval '1 day 40 minutes 15 seconds', 1203, NULL, NULL),
    ('demo_r_005', 'demo_gcp_prod', 'gcp', 'gcp_billing', 'success',
        now() - interval '1 day 41 minutes', now() - interval '1 day 39 minutes 20 seconds', 3089, NULL, NULL),
    ('demo_r_006', 'demo_llm_gateway', 'llm', 'otel_llm', 'success',
        now() - interval '1 day 40 minutes', now() - interval '1 day 37 minutes 50 seconds', 2756, NULL, NULL),
    ('demo_r_007', 'demo_azure_prod', 'azure', 'azure_cost', 'failed',
        now() - interval '2 days 30 minutes', now() - interval '2 days 30 minutes 45 seconds', 0,
        'AADSTS700082: token expired; tenant: demo-tenant-001', NULL),
    ('demo_r_008', 'demo_gcp_prod', 'gcp', 'gcp_billing', 'success',
        now() - interval '2 days 40 minutes', now() - interval '2 days 38 minutes 10 seconds', 3124, NULL, NULL),
    ('demo_r_009', 'demo_llm_gateway', 'llm', 'otel_llm', 'running',
        now() - interval '8 minutes', NULL, 1240, NULL, NULL)
ON CONFLICT (id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Extractor Health Status
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO extractor_health (extractor_name, last_run_ts, status, records_extracted, error_message, updated_at)
VALUES
    ('azure_cost_demo', now() - interval '40 minutes', 'success', 1247, NULL, now() - interval '40 minutes'),
    ('gcp_billing_demo', now() - interval '39 minutes 45 seconds', 'success', 3156, NULL, now() - interval '39 minutes 45 seconds'),
    ('llm_otel_demo', now() - interval '8 minutes', 'running', 1240, NULL, now()),
    ('exchange_rates', now() - interval '4 hours', 'success', 31, NULL, now() - interval '4 hours')
ON CONFLICT (extractor_name) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- Summary: 60+ demo cost records across:
--   - Azure: 6 VMs + 4 Storage + 6 AKS = 16 records
--   - GCP: 6 Compute + 6 BigQuery + 4 Storage = 16 records
--   - LLM: 6 Claude Sonnet + 4 GPT-4 = 10 records
--   - Plus 5 alerts and 9 extractor runs
-- ─────────────────────────────────────────────────────────────────────────────
