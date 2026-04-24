"""add alert ack columns and extractors registry

Revision ID: 004_cli_unblock
Revises: 003_enriched_schema
Create Date: 2026-04-24 09:44:46.989395

"""
from typing import Sequence, Union

from alembic import op

revision: str = "004_cli_unblock"
down_revision: Union[str, Sequence[str], None] = "003_enriched_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ack columns to alerts
    op.execute("""
        ALTER TABLE alerts
        ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS acknowledged_by TEXT
    """)

    # Create extractors registry table
    op.execute("""
        CREATE TABLE IF NOT EXISTS extractors_registry (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            provider TEXT NOT NULL,
            config_id TEXT REFERENCES cloud_config(id) ON DELETE SET NULL,
            enabled BOOLEAN NOT NULL DEFAULT true,
            schedule TEXT DEFAULT '0 0 * * *',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Create index for common lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_extractors_registry_provider
        ON extractors_registry (provider)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS extractors_registry CASCADE")
    op.execute("ALTER TABLE alerts DROP COLUMN IF EXISTS acknowledged_by")
    op.execute("ALTER TABLE alerts DROP COLUMN IF EXISTS acknowledged_at")
