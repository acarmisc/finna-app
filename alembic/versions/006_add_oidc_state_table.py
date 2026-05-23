"""Add oidc_state table for multi-replica OIDC state/nonce storage.

Revision ID: 006_oidc_state_table
Revises: 005_oidc_auth
Create Date: 2026-05-23

Purpose: Replace in-memory state/nonce storage with database-backed storage
         for multi-replica deployments.

"""
from typing import Sequence, Union

from alembic import op

revision: str = "006_oidc_state_table"
down_revision: Union[str, Sequence[str], None] = "005_oidc_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # oidc_state: stores state and nonce values for OIDC flow
    # Used to validate callback requests and prevent CSRF attacks
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

    # Index for cleanup of expired states
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_oidc_state_expires
        ON oidc_state (expires_at)
    """)

    # Index for quick lookup by state
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_oidc_state_state
        ON oidc_state (state)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_oidc_state_state")
    op.execute("DROP INDEX IF EXISTS idx_oidc_state_expires")
    op.execute("DROP TABLE IF EXISTS oidc_state CASCADE")
