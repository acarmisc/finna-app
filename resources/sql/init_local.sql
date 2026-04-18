-- FinOps — Local development init (no pg_partman/pg_cron required)

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
);

CREATE INDEX idx_cost_provider_project_time
    ON cost_records (provider, project_id, usage_start);
CREATE INDEX idx_cost_service_time
    ON cost_records (service_category, usage_start);
CREATE INDEX idx_cost_tags
    ON cost_records USING gin (tags);

CREATE TABLE extractor_health (
    extractor_name  TEXT PRIMARY KEY,
    last_run_start  TIMESTAMPTZ NOT NULL,
    last_run_end    TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'running',
    records_extracted INTEGER DEFAULT 0,
    error_message   TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE exchange_rates (
    currency       TEXT NOT NULL,
    rate_to_usd    NUMERIC(18,8) NOT NULL,
    rate_date      DATE NOT NULL,
    source         TEXT NOT NULL DEFAULT 'ecb',
    fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (currency, rate_date)
);