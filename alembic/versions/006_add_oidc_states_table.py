"""Add OIDC states table for multi-replica support

Revision ID: 006_oidc_states
Revises: 005_add_oidc_auth_providers
Create Date: 2026-05-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "006_oidc_states"
down_revision: Union[str, Sequence[str], None] = "005_add_oidc_auth_providers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create oidc_states table for database-backed state storage
    # This enables multi-replica deployments by storing state in PostgreSQL
    op.execute("""
        CREATE TABLE IF NOT EXISTS oidc_states (
            state TEXT PRIMARY KEY,
            provider_id UUID NOT NULL,
            nonce TEXT NOT NULL,
            code_verifier TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Create index on expires_at for cleanup queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_oidc_states_expires
        ON oidc_states (expires_at)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS oidc_states CASCADE")
    op.execute("DROP INDEX IF EXISTS idx_oidc_states_expires")
