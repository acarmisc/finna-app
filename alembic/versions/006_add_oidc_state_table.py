"""Add oidc_state table for database-backed state/nonce storage.

Revision ID: 006_add_oidc_state_table
Revises: 005_oidc_auth
Create Date: 2026-05-24

"""

from typing import Sequence, Union

from alembic import op

revision: str = "006_add_oidc_state_table"
down_revision: Union[str, Sequence[str], None] = "004_cli_unblock_add_alert_ack_columns_and_extractors_"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create oidc_state table for multi-replica support
    op.execute("""
        CREATE TABLE IF NOT EXISTS oidc_state (
            id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            state           TEXT NOT NULL UNIQUE,
            provider_id     UUID NOT NULL,
            nonce           TEXT NOT NULL,
            code_verifier   TEXT NOT NULL,
            expires_at      TIMESTAMPTZ NOT NULL
        )
    """)

    # Index on expires_at for cleanup of expired entries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_oidc_state_expires
        ON oidc_state (expires_at)
    """)

    # Index on state for fast lookup
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_oidc_state_state
        ON oidc_state (state)
    """)


def downgrade() -> None:
    # Remove indexes first
    op.execute("DROP INDEX IF EXISTS idx_oidc_state_state")
    op.execute("DROP INDEX IF EXISTS idx_oidc_state_expires")
    
    # Drop the table
    op.execute("DROP TABLE IF EXISTS oidc_state CASCADE")
