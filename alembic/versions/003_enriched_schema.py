"""Add enriched cost_records schema: resource_type, region, charge_type.

Revision ID: 003_enriched_schema
Revises: 002_cloud_config
Create Date: 2026-04-22

"""

from typing import Sequence, Union

from alembic import op

revision: str = "003_enriched_schema"
down_revision: Union[str, None] = "002_cloud_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to cost_records for richer metadata
    op.execute("""
        ALTER TABLE cost_records
        ADD COLUMN IF NOT EXISTS resource_type TEXT,
        ADD COLUMN IF NOT EXISTS region TEXT,
        ADD COLUMN IF NOT EXISTS charge_type TEXT
    """)


def downgrade() -> None:
    # Remove the enriched columns
    op.execute("""
        ALTER TABLE cost_records
        DROP COLUMN IF EXISTS charge_type,
        DROP COLUMN IF EXISTS region,
        DROP COLUMN IF EXISTS resource_type
    """)
