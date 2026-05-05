-- FinOps Multi-Cloud Monitoring — Database Initialization
-- PostgreSQL 16 + pg_partman + pg_cron

-- =============================================================================
-- Extensions
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pg_partman;
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- =============================================================================
-- fin_projects — project registry
-- =============================================================================

CREATE TABLE fin_projects (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    owner           TEXT NOT NULL DEFAULT '',
    cost_center     TEXT NOT NULL DEFAULT '',
    budget_cap      NUMERIC(18,6) DEFAULT NULL,
    mtd             NUMERIC(18,6) DEFAULT 0,
    tags            JSONB DEFAULT '{}',
    note            TEXT DEFAULT '',
    provider        TEXT DEFAULT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_projects_slug ON fin_projects (slug);
CREATE INDEX idx_projects_provider ON fin_projects (provider);

-- =============================================================================
-- alerts — anomaly & budget alerts
-- =============================================================================

CREATE TABLE alerts (
    id                  TEXT PRIMARY KEY,
    status              TEXT NOT NULL DEFAULT 'firing',
    severity            TEXT NOT NULL DEFAULT 'warning',
    rule                TEXT DEFAULT NULL,
    project             TEXT DEFAULT NULL,
    triggered_at        TIMESTAMPTZ DEFAULT NULL,
    description         TEXT NOT NULL DEFAULT '',
    cost_impact         NUMERIC(18,6) DEFAULT 0,
    resource            TEXT DEFAULT '',
    service             TEXT DEFAULT '',
    provider            TEXT DEFAULT '',
    acknowledged_at     TIMESTAMPTZ DEFAULT NULL,
    acknowledged_by     TEXT DEFAULT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_alerts_status ON alerts (status);
CREATE INDEX idx_alerts_severity ON alerts (severity);
CREATE INDEX idx_alerts_project ON alerts (project);
CREATE INDEX idx_alerts_triggered ON alerts (triggered_at);

-- =============================================================================
-- cost_records — partitioned by month on usage_start
-- =============================================================================

CREATE TABLE cost_records (
    record_id       TEXT PRIMARY KEY,
    provider        TEXT NOT NULL,
    usage_start     TIMESTAMPTZ NOT NULL,
    usage_end       TIMESTAMPTZ NOT NULL,
    ingestion_ts    TIMESTAMPTZ NOT NULL DEFAULT now(),
    account_id      TEXT NOT NULL,
    account_name    TEXT,
    project_id      TEXT NOT NULL,
    project_name    TEXT,
    environment     TEXT,
    team            TEXT,
    service_category TEXT NOT NULL,
    service_name    TEXT NOT NULL,
    resource_type   TEXT DEFAULT NULL,
    region          TEXT DEFAULT NULL,
    charge_type     TEXT DEFAULT NULL,
    resource_id     TEXT,
    cost_usd        NUMERIC(18,6) NOT NULL,
    currency_original TEXT NOT NULL,
    cost_original   NUMERIC(18,6) NOT NULL,
    discount_usd    NUMERIC(18,6) DEFAULT 0,
    net_cost_usd    NUMERIC(18,6) NOT NULL,
    usage_quantity  NUMERIC(28,6),
    usage_unit      TEXT,
    model_name      TEXT,
    input_tokens    BIGINT,
    output_tokens   BIGINT,
    total_tokens    BIGINT,
    latency_ms      DOUBLE PRECISION,
    trace_id        TEXT,
    tags            JSONB DEFAULT '{}'
) PARTITION BY RANGE (usage_start);

-- pg_partman: automatic monthly partitions
SELECT partman.create_parent(
    p_parent_table := 'public.cost_records',
    p_control := 'usage_start',
    p_interval := '1 month',
    p_premake := 3
);

-- Indexes
CREATE INDEX idx_cost_provider_project_time
    ON cost_records (provider, project_id, usage_start);
CREATE INDEX idx_cost_service_time
    ON cost_records (service_category, usage_start);
CREATE INDEX idx_cost_tags
    ON cost_records USING gin (tags);

-- =============================================================================
-- daily_costs — materialized view for dashboard queries
-- =============================================================================

CREATE MATERIALIZED VIEW daily_costs AS
SELECT
    date_trunc('day', usage_start) AS day,
    provider,
    project_id,
    service_category,
    service_name,
    model_name,
    sum(net_cost_usd) AS total_cost,
    sum(input_tokens) AS total_input_tokens,
    sum(output_tokens) AS total_output_tokens,
    count(*) AS record_count
FROM cost_records
GROUP BY 1, 2, 3, 4, 5, 6;

CREATE UNIQUE INDEX idx_daily_costs_pk
    ON daily_costs (day, provider, project_id, service_category, service_name, model_name);

-- Scheduled refresh via pg_cron (every 15 minutes)
-- Uncomment when pg_cron is available:
-- SELECT cron.schedule('refresh-daily-costs', '*/15 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY daily_costs');

-- =============================================================================
-- infra_metrics_agg — pre-aggregated infrastructure metrics
-- =============================================================================

CREATE TABLE infra_metrics_agg (
    window_start    TIMESTAMPTZ NOT NULL,
    window_end      TIMESTAMPTZ NOT NULL,
    provider        TEXT NOT NULL,
    project_id      TEXT NOT NULL,
    resource_id     TEXT NOT NULL,
    cpu_avg         DOUBLE PRECISION,
    cpu_p95         DOUBLE PRECISION,
    cpu_max         DOUBLE PRECISION,
    memory_avg_bytes BIGINT,
    memory_max_bytes BIGINT,
    network_in_bytes BIGINT,
    network_out_bytes BIGINT,
    sample_count    INTEGER NOT NULL
) PARTITION BY RANGE (window_start);

SELECT partman.create_parent(
    p_parent_table := 'public.infra_metrics_agg',
    p_control := 'window_start',
    p_interval := '1 month',
    p_premake := 3
);

CREATE INDEX idx_infra_resource_time
    ON infra_metrics_agg (resource_id, window_start);

-- =============================================================================
-- exchange_rates — ECB daily rates for currency conversion
-- =============================================================================

CREATE TABLE exchange_rates (
    currency       TEXT NOT NULL,
    rate_to_usd    NUMERIC(18,8) NOT NULL,
    rate_date      DATE NOT NULL,
    source         TEXT NOT NULL DEFAULT 'ecb',
    fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (currency, rate_date)
);

-- =============================================================================
-- extractor_health — health tracking for each extractor
-- =============================================================================

CREATE TABLE extractor_health (
    extractor_name  TEXT PRIMARY KEY,
    last_run_start  TIMESTAMPTZ NOT NULL,
    last_run_end    TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'running',  -- running | success | failed
    records_extracted INTEGER DEFAULT 0,
    error_message   TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- Seed Data — 90 days, GCP + Azure + LLM, 5 projects
-- =============================================================================

-- Projects
-- 1. finops-prod    (GCP, production)
-- 2. finops-staging (GCP, staging)
-- 3. analytics-prod (Azure, production)
-- 4. ml-platform    (GCP, production, LLM-heavy)
-- 5. dev-sandbox    (Azure, dev)

INSERT INTO cost_records (record_id, provider, usage_start, usage_end, ingestion_ts,
    account_id, account_name, project_id, project_name, environment, team,
    service_category, service_name, resource_id,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit, tags)
SELECT
    'seed-gcp-' || generate_series(1, 1500) || '-' || d.dt::text,
    'gcp',
    d.dt + make_interval(secs => (random() * 86400)::int),
    d.dt + make_interval(secs => (random() * 86400)::int + 3600),
    now(),
    'gcp-org-12345',
    'FinOps GCP Organization',
    (ARRAY['finops-prod','finops-staging','ml-platform'])[1 + (abs(('seed-gcp-' || generate_series(1,1) || d.dt::text)::text::bigint) % 3)],
    (ARRAY['FinOps Production','FinOps Staging','ML Platform'])[1 + (abs(('seed-gcp-' || generate_series(1,1) || d.dt::text)::text::bigint) % 3)],
    (ARRAY['prod','staging','prod'])[1 + (abs(('seed-gcp-' || generate_series(1,1) || d.dt::text)::text::bigint) % 3)],
    (ARRAY['platform','platform','ml'])[1 + (abs(('seed-gcp-' || generate_series(1,1) || d.dt::text)::text::bigint) % 3)],
    (ARRAY['compute','storage','network','database','ml'])[1 + (abs(('seed-gcp-' || generate_series(1,1) || d.dt::text)::text::bigint) % 5)],
    (ARRAY['Compute Engine','Cloud Storage','Cloud Networking','Cloud SQL','Vertex AI'])[1 + (abs(('seed-gcp-' || generate_series(1,1) || d.dt::text)::text::bigint) % 5)],
    'gcp-res-' || (abs(('seed-gcp-' || generate_series(1,1) || d.dt::text)::text::bigint) % 100),
    (random() * 500 + 10)::numeric(18,6),
    'USD',
    (random() * 500 + 10)::numeric(18,6),
    (random() * 50)::numeric(18,6),
    (random() * 450 + 5)::numeric(18,6),
    (random() * 1000 + 1)::numeric(18,6),
    (ARRAY['hours','GB','GB','hours','hours'])[1 + (abs(('seed-gcp-' || generate_series(1,1) || d.dt::text)::text::bigint) % 5)],
    '{"source":"seed","cloud":"gcp"}'::jsonb
FROM (
    SELECT generate_series(
        current_date - interval '90 days',
        current_date - interval '1 day',
        interval '1 day'
    )::date AS dt
) d,
    generate_series(1, 5);

-- Azure seed data
INSERT INTO cost_records (record_id, provider, usage_start, usage_end, ingestion_ts,
    account_id, account_name, project_id, project_name, environment, team,
    service_category, service_name, resource_id,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit, tags)
SELECT
    'seed-azure-' || generate_series(1, 1000) || '-' || d.dt::text,
    'azure',
    d.dt + make_interval(secs => (random() * 86400)::int),
    d.dt + make_interval(secs => (random() * 86400)::int + 3600),
    now(),
    'azure-sub-67890',
    'FinOps Azure Subscription',
    (ARRAY['analytics-prod','dev-sandbox'])[1 + (abs(('seed-azure-' || generate_series(1,1) || d.dt::text)::text::bigint) % 2)],
    (ARRAY['Analytics Production','Dev Sandbox'])[1 + (abs(('seed-azure-' || generate_series(1,1) || d.dt::text)::text::bigint) % 2)],
    (ARRAY['prod','dev'])[1 + (abs(('seed-azure-' || generate_series(1,1) || d.dt::text)::text::bigint) % 2)],
    (ARRAY['data','devops'])[1 + (abs(('seed-azure-' || generate_series(1,1) || d.dt::text)::text::bigint) % 2)],
    (ARRAY['compute','storage','network','database'])[1 + (abs(('seed-azure-' || generate_series(1,1) || d.dt::text)::text::bigint) % 4)],
    (ARRAY['Virtual Machines','Blob Storage','Azure CDN','Cosmos DB'])[1 + (abs(('seed-azure-' || generate_series(1,1) || d.dt::text)::text::bigint) % 4)],
    'azure-res-' || (abs(('seed-azure-' || generate_series(1,1) || d.dt::text)::text::bigint) % 80),
    (random() * 400 + 5)::numeric(18,6),
    'USD',
    (random() * 400 + 5)::numeric(18,6),
    (random() * 30)::numeric(18,6),
    (random() * 370 + 3)::numeric(18,6),
    (random() * 800 + 1)::numeric(18,6),
    (ARRAY['hours','GB','GB','hours'])[1 + (abs(('seed-azure-' || generate_series(1,1) || d.dt::text)::text::bigint) % 4)],
    '{"source":"seed","cloud":"azure"}'::jsonb
FROM (
    SELECT generate_series(
        current_date - interval '90 days',
        current_date - interval '1 day',
        interval '1 day'
    )::date AS dt
) d,
    generate_series(1, 5);

-- LLM seed data (OTel collector-style)
INSERT INTO cost_records (record_id, provider, usage_start, usage_end, ingestion_ts,
    account_id, account_name, project_id, project_name, environment, team,
    service_category, service_name, resource_id,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit,
    model_name, input_tokens, output_tokens, total_tokens, latency_ms, trace_id, tags)
SELECT
    'seed-llm-' || seq || '-' || d.dt::text,
    'llm',
    d.dt + make_interval(secs => (random() * 86400)::int),
    d.dt + make_interval(secs => (random() * 86400)::int + 300),
    now(),
    'otel-collector',
    'OTel LLM Collector',
    (ARRAY['ml-platform','finops-prod','dev-sandbox'])[1 + (abs(seq) % 3)],
    (ARRAY['ML Platform','FinOps Production','Dev Sandbox'])[1 + (abs(seq) % 3)],
    (ARRAY['prod','prod','dev'])[1 + (abs(seq) % 3)],
    (ARRAY['ml','platform','devops'])[1 + (abs(seq) % 3)],
    'llm',
    (ARRAY['gpt-4o','gpt-4o-mini','claude-3-5-sonnet','gemini-1.5-pro'])[1 + (abs(seq) % 4)],
    NULL,
    cost_val::numeric(18,6),
    'USD',
    cost_val::numeric(18,6),
    0,
    cost_val::numeric(18,6),
    total_tok,
    'tokens',
    (ARRAY['gpt-4o','gpt-4o-mini','claude-3-5-sonnet','gemini-1.5-pro'])[1 + (abs(seq) % 4)],
    in_tok,
    out_tok,
    in_tok + out_tok,
    (random() * 3000 + 200)::float,
    'trace-' || seq,
    jsonb_build_object('source', 'seed', 'otel_source', 'otel-collector-' || (abs(seq) % 5))
FROM (
    SELECT
        generate_series(1, 2000) AS seq,
        d.dt,
        (random() * 5000 + 100)::int AS in_tok,
        (random() * 2000 + 50)::int AS out_tok,
        (random() * 5000 + 150)::int AS total_tok,
        ((random() * 5000 + 100) * 0.00003 + (random() * 2000 + 50) * 0.00006)::numeric(18,6) AS cost_val
    FROM (
        SELECT generate_series(
            current_date - interval '90 days',
            current_date - interval '1 day',
            interval '1 day'
        )::date AS dt
    ) d,
        generate_series(1, 20)
) sub;

-- Refresh materialized view with seed data
REFRESH MATERIALIZED VIEW CONCURRENTLY daily_costs;

-- =============================================================================
-- Seed exchange rates
-- =============================================================================

INSERT INTO exchange_rates (currency, rate_to_usd, rate_date, source) VALUES
    ('EUR', 1.0850, current_date, 'ecb'),
    ('GBP', 1.2650, current_date, 'ecb'),
    ('JPY', 0.0066, current_date, 'ecb'),
    ('CHF', 1.1230, current_date, 'ecb'),
    ('CAD', 0.7350, current_date, 'ecb'),
    ('AUD', 0.6500, current_date, 'ecb'),
    ('SEK', 0.0950, current_date, 'ecb'),
    ('NOK', 0.0920, current_date, 'ecb'),
    ('DKK', 0.1450, current_date, 'ecb'),
    ('INR', 0.0120, current_date, 'ecb');

-- =============================================================================
-- Migrations — add columns/tables to existing deployments
-- Run these on top of older init.sql versions
-- =============================================================================

ALTER TABLE cost_records ADD COLUMN IF NOT EXISTS resource_type TEXT DEFAULT NULL;
ALTER TABLE cost_records ADD COLUMN IF NOT EXISTS region TEXT DEFAULT NULL;
ALTER TABLE cost_records ADD COLUMN IF NOT EXISTS charge_type TEXT DEFAULT NULL;

ALTER TABLE cloud_config ADD COLUMN IF NOT EXISTS last_test TEXT DEFAULT NULL;
ALTER TABLE cloud_config ADD COLUMN IF NOT EXISTS last_test_at TIMESTAMPTZ DEFAULT NULL;
ALTER TABLE cloud_config ADD COLUMN IF NOT EXISTS err TEXT DEFAULT NULL;