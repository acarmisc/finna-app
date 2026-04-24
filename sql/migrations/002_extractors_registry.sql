-- Extractors registry table for CRUD operations
-- This table stores the extractor configurations that can be scheduled and triggered

CREATE TABLE IF NOT EXISTS extractors (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    extractor_type TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    schedule TEXT,  -- Cron expression (optional)
    config_id TEXT REFERENCES cloud_config(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'idle',  -- idle, running, paused
    last_run_id TEXT REFERENCES extractor_runs(id) ON DELETE SET NULL,
    last_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_extractors_provider ON extractors(provider);
CREATE INDEX IF NOT EXISTS idx_extractors_enabled ON extractors(enabled);
CREATE INDEX IF NOT EXISTS idx_extractors_status ON extractors(status);

-- Seed some default extractors
INSERT INTO extractors (id, name, provider, extractor_type, enabled, config_id, schedule)
VALUES
    ('ext_azure_cost', 'Azure Cost Extractor', 'azure', 'azure_cost', true, 'c_az_prod', '0 * * * *'),
    ('ext_gcp_billing', 'GCP Billing Extractor', 'gcp', 'gcp_billing', true, 'c_gcp_prod', '0 * * * *'),
    ('ext_exchange_rates', 'Exchange Rates', 'ecb', 'exchange_rates', true, NULL, '0 0 * * *'),
    ('ext_otel_llm_us', 'OTEL LLM (US)', 'llm', 'otel_llm', true, 'c_llm_us', '0 * * * *'),
    ('ext_otel_llm_eu', 'OTEL LLM (EU)', 'llm', 'otel_llm', true, 'c_llm_eu', '0 * * * *')
ON CONFLICT (id) DO NOTHING;
