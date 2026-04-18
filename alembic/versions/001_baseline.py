"""Baseline migration: create initial schema.

Revision ID: 001_baseline
Revises:
Create Date: 2026-04-18

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if pg_partman is available before trying to create it
    conn = op.get_bind()
    res = conn.execute(text("SELECT 1 FROM pg_available_extensions WHERE name = 'pg_partman'")).fetchone()
    HAS_PARTMAN = res is not None

    if HAS_PARTMAN:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_partman")
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_cron")
    else:
        print("WARNING: pg_partman not available, skipping partitioning setup")

    # cost_records — partitioned by month on usage_start
    partition_clause = "PARTITION BY RANGE (usage_start)" if HAS_PARTMAN else ""
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS cost_records (
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
            tags            JSONB DEFAULT '{{}}'
        ) {partition_clause}
    """)

    if HAS_PARTMAN:
        op.execute("""
            SELECT partman.create_parent(
                p_parent_table := 'public.cost_records',
                p_control := 'usage_start',
                p_interval := '1 month',
                p_premake := 3
            )
        """)

    # Indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cost_provider_project_time
        ON cost_records (provider, project_id, usage_start)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cost_service_time
        ON cost_records (service_category, usage_start)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cost_tags
        ON cost_records USING gin (tags)
    """)

    # daily_costs — materialized view for dashboard queries
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS daily_costs AS
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
        GROUP BY 1, 2, 3, 4, 5, 6
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_costs_pk
        ON daily_costs (day, provider, project_id, service_category, service_name, model_name)
    """)

    # infra_metrics_agg — pre-aggregated infrastructure metrics
    partition_clause_infra = "PARTITION BY RANGE (window_start)" if HAS_PARTMAN else ""
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS infra_metrics_agg (
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
        ) {partition_clause_infra}
    """)

    if HAS_PARTMAN:
        op.execute("""
            SELECT partman.create_parent(
                p_parent_table := 'public.infra_metrics_agg',
                p_control := 'window_start',
                p_interval := '1 month',
                p_premake := 3
            )
        """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_infra_resource_time
        ON infra_metrics_agg (resource_id, window_start)
    """)

    # exchange_rates — ECB daily rates for currency conversion
    op.execute("""
        CREATE TABLE IF NOT EXISTS exchange_rates (
            currency       TEXT NOT NULL,
            rate_to_usd    NUMERIC(18,8) NOT NULL,
            rate_date      DATE NOT NULL,
            source         TEXT NOT NULL DEFAULT 'ecb',
            fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (currency, rate_date)
        )
    """)

    # extractor_health — health tracking for each extractor
    op.execute("""
        CREATE TABLE IF NOT EXISTS extractor_health (
            extractor_name  TEXT PRIMARY KEY,
            last_run_start  TIMESTAMPTZ NOT NULL,
            last_run_end    TIMESTAMPTZ,
            status          TEXT NOT NULL DEFAULT 'running',
            records_extracted INTEGER DEFAULT 0,
            error_message   TEXT,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Seed exchange rates
    op.execute("""
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
            ('INR', 0.0120, current_date, 'ecb')
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS extractor_health CASCADE")
    op.execute("DROP TABLE IF EXISTS exchange_rates CASCADE")
    op.execute("DROP TABLE IF EXISTS infra_metrics_agg CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS daily_costs CASCADE")
    op.execute("DROP TABLE IF EXISTS cost_records CASCADE")
    op.execute("DROP EXTENSION IF EXISTS pg_cron CASCADE")
    op.execute("DROP EXTENSION IF EXISTS pg_partman CASCADE")
