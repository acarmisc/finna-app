"""Add OIDC auth providers table and auth_users OIDC columns

Revision ID: 005_oidc_auth
Revises: 004_cli_unblock
Create Date: 2026-05-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "005_oidc_auth"
down_revision: Union[str, Sequence[str], None] = "004_cli_unblock"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create auth_providers table
    op.execute("""
        CREATE TABLE IF NOT EXISTS auth_providers (
            id UUID PRIMARY KEY,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT false,
            config BYTEA NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by TEXT,
            last_test_at TIMESTAMPTZ,
            last_test_ok BOOLEAN
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_providers_name
        ON auth_providers (lower(name))
    """)

    # Add OIDC columns to auth_users
    op.execute("""
        ALTER TABLE auth_users
        ADD COLUMN IF NOT EXISTS oidc_provider_id UUID REFERENCES auth_providers(id),
        ADD COLUMN IF NOT EXISTS oidc_subject TEXT,
        ADD COLUMN IF NOT EXISTS oidc_claims JSONB DEFAULT '{}'::jsonb
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_users_oidc
        ON auth_users (oidc_provider_id, oidc_subject)
        WHERE oidc_subject IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_auth_users_oidc")
    op.execute("""
        ALTER TABLE auth_users
        DROP COLUMN IF EXISTS oidc_claims,
        DROP COLUMN IF EXISTS oidc_subject,
        DROP COLUMN IF EXISTS oidc_provider_id
    """)
    op.execute("DROP INDEX IF EXISTS idx_auth_providers_name")
    op.execute("DROP TABLE IF EXISTS auth_providers CASCADE")
