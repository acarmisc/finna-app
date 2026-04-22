-- FinOps Multi-Cloud Monitoring — Database Initialization (Docker-friendly)
-- PostgreSQL 16

-- ─── Cost records ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cost_records (
    record_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    usage_start TIMESTAMPTZ NOT NULL,
    usage_end TIMESTAMPTZ NOT NULL,
    ingestion_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    account_id TEXT,
    account_name TEXT,
    project_id TEXT,
    project_name TEXT,
    environment TEXT,
    team TEXT,
    service_category TEXT,
    service_name TEXT,
    resource_id TEXT,
    resource_type TEXT,
    region TEXT,
    charge_type TEXT,
    cost_usd NUMERIC(18,6) NOT NULL DEFAULT 0,
    currency_original TEXT NOT NULL DEFAULT 'USD',
    cost_original NUMERIC(18,6) NOT NULL DEFAULT 0,
    discount_usd NUMERIC(18,6) DEFAULT 0,
    net_cost_usd NUMERIC(18,6) DEFAULT 0,
    usage_quantity NUMERIC(18,6),
    usage_unit TEXT,
    model_name TEXT,
    input_tokens BIGINT,
    output_tokens BIGINT,
    total_tokens BIGINT,
    latency_ms INTEGER,
    trace_id TEXT,
    tags JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cost_records_provider ON cost_records(provider);
CREATE INDEX IF NOT EXISTS idx_cost_records_usage_start ON cost_records(usage_start);
CREATE INDEX IF NOT EXISTS idx_cost_records_project_id ON cost_records(project_id);

-- ─── Alerts ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL DEFAULT '',
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    rule TEXT,
    firing TEXT,
    channels TEXT[] DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'firing',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

-- ─── Extractor runs ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS exchange_rates (
    currency TEXT PRIMARY KEY,
    rate_to_usd NUMERIC(18,8) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);
INSERT INTO exchange_rates (currency, rate_to_usd) VALUES ('EUR', 1.08), ('GBP', 1.27)
ON CONFLICT (currency) DO NOTHING;

CREATE TABLE IF NOT EXISTS extractor_health (
    extractor_name TEXT PRIMARY KEY,
    last_run_ts TIMESTAMPTZ,
    status TEXT,
    records_extracted INT DEFAULT 0,
    error_message TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS extractor_runs (
    id TEXT PRIMARY KEY,
    config_id TEXT,
    provider TEXT NOT NULL,
    extractor_type TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    records_extracted INTEGER DEFAULT 0,
    error_message TEXT,
    log_output TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── Fin projects ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fin_projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    owner TEXT NOT NULL,
    cost_center TEXT NOT NULL,
    budget_cap NUMERIC(18,6) NOT NULL DEFAULT 0,
    mtd NUMERIC(18,6) NOT NULL DEFAULT 0,
    tags JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    note TEXT
);

-- ─── Cloud config (existing) ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cloud_config (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    name TEXT,
    credential_type TEXT,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── Auth ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS auth_users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auth_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    token_type TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── Seed data ──────────────────────────────────────────────────────────────

-- Admin user (password: admin)
INSERT INTO auth_users (username, email, hashed_password, is_active, is_admin)
VALUES ('admin', 'admin@finops.local',
        '$2b$12$UYoRP.qb0Lx5AlFzlY0dnOdq19.JSYRR3z2Mw2WspmnuCOMUWJZXG',
        true, true)
ON CONFLICT (username) DO UPDATE SET hashed_password = EXCLUDED.hashed_password;

-- Fin projects
INSERT INTO fin_projects (id, name, slug, owner, cost_center, budget_cap, mtd, tags, created_at, note) VALUES
('p_platform', 'Platform', 'platform', 'platform-eng@acme.co', 'eng-001', 14000, 8412.22, '{"env":"prod","business_unit":"core"}'::jsonb, now() - interval '30 days', 'Core platform + shared data infra.'),
('p_ml', 'ML & AI', 'ml-ai', 'ml-team@acme.co', 'ml-002', 3500, 1241.40, '{"env":"mixed","business_unit":"ai"}'::jsonb, now() - interval '20 days', 'Training, serving and LLM spend.'),
('p_analytics', 'Analytics', 'analytics', 'data@acme.co', 'data-004', 10000, 4094.41, '{"env":"prod","business_unit":"data"}'::jsonb, now() - interval '60 days', 'BI, dashboards, warehouse.'),
('p_dev', 'Dev & Staging', 'dev', 'devops@acme.co', 'eng-002', 900, 208.00, '{"env":"dev","business_unit":"core"}'::jsonb, now() - interval '25 days', 'Developer sandboxes and CI.')
ON CONFLICT (id) DO NOTHING;

-- Cloud configs linked to projects
INSERT INTO cloud_config (id, provider, name, credential_type, config, created_at, updated_at)
VALUES
('c_az_prod', 'azure', 'acme-prod', 'service_account',
    '{"tenant_id":"acme-prod","client_id":"az-prod-sa","subscription_id":"sub-001"}'::jsonb,
    now() - interval '30 days', now() - interval '30 days'),
('c_az_dev', 'azure', 'acme-dev', 'device_code',
    '{"tenant_id":"acme-dev","client_id":"az-dev-sa"}'::jsonb,
    now() - interval '20 days', now() - interval '20 days'),
('c_gcp_prod', 'gcp', 'prod-platform', 'service_account',
    '{"project_id":"prod-platform","key_file_base64":"base64encodedkey"}'::jsonb,
    now() - interval '30 days', now() - interval '30 days'),
('c_gcp_ml', 'gcp', 'staging-ml', 'service_account',
    '{"project_id":"staging-ml","key_file_base64":"base64encodedkey"}'::jsonb,
    now() - interval '20 days', now() - interval '20 days'),
('c_llm_us', 'llm', 'otel-gateway-us', 'otlp',
    '{"endpoint":"0.0.0.0:4317","protocol":"otlp"}'::jsonb,
    now() - interval '15 days', now() - interval '15 days'),
('c_llm_eu', 'llm', 'otel-gateway-eu', 'otlp',
    '{"endpoint":"0.0.0.0:4317","protocol":"otlp"}'::jsonb,
    now() - interval '15 days', now() - interval '15 days')
ON CONFLICT (id) DO NOTHING;

-- cost_records seed data removed — populated via extractors

-- Seeded alerts
INSERT INTO alerts (id, type, severity, title, body, rule, firing, channels, status, created_at)
VALUES
    ('a1', 'budget', 'err', 'rg-analytics over budget',
     '$8,200 of $10,000 used. Forecast exceeds cap by Nov 28.',
     'cost_mtd rg-analytics > 0.8 * budget',
     now() - interval '12 minutes', ARRAY['finops-slack', 'oncall@acme.co'], 'firing', now() - interval '12 minutes'),
    ('a2', 'anomaly', 'warn', 'LLM cost anomaly claude-sonnet-4',
     '+120% vs 7d average. 3 traces flagged for review.',
     'zscore cost_1d claude-sonnet-4 window=7 > 2.0',
     now() - interval '2 hours', ARRAY['finops-slack'], 'firing', now() - interval '2 hours'),
    ('a3', 'sla', 'ok', 'Nightly extraction SLA',
     'All 4 extractors completed within 15 min window.',
     'extractor_health.last_success < 6h',
     NULL, ARRAY['oncall@acme.co'], 'resolved', now() - interval '1 hour'),
    ('a4', 'freshness', 'ok', 'Exchange rates freshness',
     'ECB rates updated at 16:05 UTC within 24h threshold.',
     'max exchange_rates.fetched_at < 24h',
     NULL, ARRAY['finops-slack'], 'resolved', now() - interval '1 hour'),
    ('a5', 'spike', 'warn', 'BigQuery scan cost spike prod-platform',
     '$412 in the last 6 hours across 18 queries. Dashboard auto-refresh suspected.',
     'sum cost_1h prod-platform sku=BigQuery > 60 for 3h',
     now() - interval '42 minutes', ARRAY['finops-slack'], 'firing', now() - interval '42 minutes')
ON CONFLICT (id) DO NOTHING;

-- Seeded extractor runs
INSERT INTO extractor_runs (id, config_id, provider, extractor_type, status, started_at, finished_at, records_extracted, error_message, log_output)
VALUES
    ('r_01jf2kn8b3', 'c_az_prod', 'azure', 'azure_cost', 'success', now() - interval '4 minutes', now() - interval '3 minutes 58 seconds', 1204, NULL, NULL),
    ('r_01jf2kn7a1', 'c_gcp_prod', 'gcp', 'gcp_billing', 'success', now() - interval '4 minutes', now() - interval '3 minutes 56 seconds', 3092, NULL, NULL),
    ('r_01jf2kn6x9', NULL, 'ecb', 'exchange_rates', 'success', now() - interval '4 minutes', now() - interval '4 minutes 2 seconds', 31, NULL, NULL),
    ('r_01jf2kn5v4', 'c_llm_us', 'llm', 'otel_llm', 'running', now() - interval '1 minute', NULL, 0, NULL, NULL),
    ('r_01jf1zna2b', 'c_az_dev', 'azure', 'azure_cost', 'failed', now() - interval '1 day', now() - interval '1 day 5 seconds', 0, 'AADSTS700082: token expired (acme-dev)', NULL),
    ('r_01jf1wmc84', 'c_gcp_prod', 'gcp', 'gcp_billing', 'success', now() - interval '1 day', now() - interval '1 day 1 minute 12 seconds', 3140, NULL, NULL),
    ('r_01jf1wmb78', 'c_az_prod', 'azure', 'azure_cost', 'success', now() - interval '1 day', now() - interval '1 day 1 minute 39 seconds', 1188, NULL, NULL),
    ('r_01jf1wma22', NULL, 'ecb', 'exchange_rates', 'success', now() - interval '1 day', now() - interval '1 day 1 minute 2 seconds', 31, NULL, NULL),
    ('r_01jf1r28kk', 'c_llm_us', 'llm', 'otel_llm', 'success', now() - interval '1 day', now() - interval '1 day 1 minute 8 seconds', 842, NULL, NULL),
    ('r_01jf1kn812', 'c_gcp_prod', 'gcp', 'gcp_billing', 'success', now() - interval '2 days', now() - interval '2 days 1 minute 4 seconds', 3081, NULL, NULL),
    ('r_01jf1kn7hx', 'c_az_prod', 'azure', 'azure_cost', 'success', now() - interval '2 days', now() - interval '2 days 1 minute 44 seconds', 1192, NULL, NULL),
    ('r_01jf0n2p1k', 'c_llm_eu', 'llm', 'otel_llm', 'failed', now() - interval '3 days', now() - interval '3 days 1 minute 18 seconds', 0, 'connection refused: otel-gateway-eu:4317', NULL)
ON CONFLICT (id) DO NOTHING;
