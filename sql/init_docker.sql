-- FinOps Multi-Cloud Monitoring — Database Initialization (Docker-friendly)
-- PostgreSQL 16 (without pg_partman/pg_cron extensions)

-- Create users and database
-- CREATE USER finops WITH PASSWORD 'finops_dev';

-- Create tables without partitioning for Docker setup
CREATE TABLE IF NOT EXISTS cloud_config (
    id SERIAL PRIMARY KEY,
    provider TEXT NOT NULL UNIQUE,
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cost_records (
    record_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    usage_start TIMESTAMPTZ NOT NULL,
    usage_end TIMESTAMPTZ NOT NULL,
    ingestion_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    account_id TEXT NOT NULL,
    account_name TEXT,
    project_id TEXT NOT NULL,
    project_name TEXT,
    environment TEXT,
    team TEXT,
    service_category TEXT NOT NULL,
    service_name TEXT NOT NULL,
    resource_id TEXT,
    cost_usd NUMERIC(18,6) NOT NULL,
    currency_original TEXT NOT NULL,
    cost_original NUMERIC(18,6) NOT NULL,
    discount_usd NUMERIC(18,6) DEFAULT 0,
    net_cost_usd NUMERIC(18,6) NOT NULL,
    usage_quantity NUMERIC(28,6),
    usage_unit TEXT,
    model_name TEXT,
    input_tokens BIGINT,
    output_tokens BIGINT,
    total_tokens BIGINT,
    latency_ms DOUBLE PRECISION,
    trace_id TEXT,
    tags JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cost_aggregates (
    id SERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_cost NUMERIC(18,6) NOT NULL,
    record_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

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

-- Sample data for testing
INSERT INTO cloud_config (provider, config) VALUES 
('gcp', '{"project_id": "test-gcp-project", "credentials_path": "/app/config/gcp.json"}')
ON CONFLICT (provider) DO NOTHING;

INSERT INTO auth_users (username, email, hashed_password, is_active, is_admin) VALUES
('admin', 'admin@finops.local', '$2b$12$EixZaYVK1fsbw1ZfbX3OXe/aZlDk9o3p3d5Z7j8k9l0m1n2o3p4q5', true, true)
ON CONFLICT DO NOTHING;
