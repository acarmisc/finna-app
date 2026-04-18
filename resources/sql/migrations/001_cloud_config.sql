-- Migration: cloud_config and extractor_runs tables
-- Version: 001
-- Created: 2026-04-14

BEGIN;

-- cloud_config: credentials and configuration for cloud providers
CREATE TABLE IF NOT EXISTS cloud_config (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    provider        TEXT NOT NULL CHECK (provider IN ('azure', 'gcp')),
    name            TEXT NOT NULL,
    credential_type TEXT NOT NULL DEFAULT 'service_principal'
        CHECK (credential_type IN ('service_principal', 'managed_identity', 'cli', 'device_code')),
    config          JSONB NOT NULL,
    -- Azure example: {tenant_id, client_id, client_secret, subscription_id, resource_groups, scope, ...}
    -- GCP example:   {project_id, billing_account_id, bigquery_dataset, bigquery_table, ...}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cloud_config_provider ON cloud_config (provider);

-- extractor_runs: execution history for extractors
CREATE TABLE IF NOT EXISTS extractor_runs (
    id                TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    config_id         TEXT NOT NULL REFERENCES cloud_config(id) ON DELETE CASCADE,
    provider          TEXT NOT NULL,
    extractor_type    TEXT NOT NULL,  -- 'azure_cost' | 'gcp_billing' | 'exchange_rates'
    status            TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'success', 'failed')),
    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at       TIMESTAMPTZ,
    records_extracted INTEGER DEFAULT 0,
    error_message     TEXT,
    log_output       TEXT,
    pid              INTEGER
);

CREATE INDEX IF NOT EXISTS idx_extractor_runs_status ON extractor_runs (status);
CREATE INDEX IF NOT EXISTS idx_extractor_runs_config ON extractor_runs (config_id);

COMMIT;