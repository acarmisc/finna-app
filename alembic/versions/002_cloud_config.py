"""Add cloud_config and extractor_runs tables.

Revision ID: 002_cloud_config
Revises: 001_baseline
Create Date: 2026-04-18

"""

from typing import Sequence, Union

from alembic import op

revision: str = "002_cloud_config"
down_revision: Union[str, None] = "001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # cloud_config: credentials and configuration for cloud providers
    op.execute("""
        CREATE TABLE IF NOT EXISTS cloud_config (
            id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            provider        TEXT NOT NULL CHECK (provider IN ('azure', 'gcp')),
            name            TEXT NOT NULL,
            credential_type TEXT NOT NULL DEFAULT 'service_principal'
                CHECK (credential_type IN ('service_principal', 'managed_identity', 'cli', 'device_code')),
            config          JSONB NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cloud_config_provider ON cloud_config (provider)
    """)

    # extractor_runs: execution history for extractors
    op.execute("""
        CREATE TABLE IF NOT EXISTS extractor_runs (
            id                TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            config_id         TEXT NOT NULL REFERENCES cloud_config(id) ON DELETE CASCADE,
            provider          TEXT NOT NULL,
            extractor_type    TEXT NOT NULL,
            status            TEXT NOT NULL DEFAULT 'running'
                CHECK (status IN ('running', 'success', 'failed')),
            started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at       TIMESTAMPTZ,
            records_extracted INTEGER DEFAULT 0,
            error_message     TEXT,
            log_output       TEXT,
            pid              INTEGER
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extractor_runs_status ON extractor_runs (status)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extractor_runs_config ON extractor_runs (config_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS extractor_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS cloud_config CASCADE")
