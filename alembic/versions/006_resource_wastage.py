"""Add resource_wastage and wastage_scan_runs tables.

Revision ID: 006_resource_wastage
Revises: 005_oidc_auth
Create Date: 2026-06-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "006_resource_wastage"
down_revision: Union[str, Sequence[str], None] = "005_oidc_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Status enum for wastage findings
    op.execute("""
        CREATE TYPE wastage_status AS ENUM ('open', 'acked', 'resolved', 'ignored')
    """)

    # resource_wastage — one row per (provider, resource_id, rule_id) finding
    op.execute("""
        CREATE TABLE resource_wastage (
            finding_id          TEXT PRIMARY KEY,
            provider            TEXT NOT NULL,
            account_id          TEXT NOT NULL,
            resource_group      TEXT,
            region              TEXT,
            resource_id         TEXT NOT NULL,
            resource_type       TEXT NOT NULL,
            rule_id             TEXT NOT NULL,
            severity            TEXT NOT NULL,
            category            TEXT NOT NULL,
            estimated_monthly_usd NUMERIC(18, 6) NOT NULL DEFAULT 0,
            currency            TEXT NOT NULL DEFAULT 'USD',
            evidence            JSONB NOT NULL DEFAULT '{}'::jsonb,
            first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            status              wastage_status NOT NULL DEFAULT 'open',
            tags                JSONB NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT uq_wastage_provider_resource_rule
                UNIQUE (provider, resource_id, rule_id)
        )
    """)

    op.execute("""
        CREATE INDEX idx_wastage_provider_account_status
        ON resource_wastage (provider, account_id, status)
    """)

    op.execute("""
        CREATE INDEX idx_wastage_rule_id
        ON resource_wastage (rule_id)
    """)

    op.execute("""
        CREATE INDEX idx_wastage_status_severity
        ON resource_wastage (status, severity)
    """)

    # wastage_scan_runs — audit log for each scan execution
    op.execute("""
        CREATE TABLE wastage_scan_runs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider        TEXT NOT NULL,
            started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at     TIMESTAMPTZ,
            status          TEXT NOT NULL DEFAULT 'running',
            findings_count  INTEGER,
            error           TEXT
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS wastage_scan_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS resource_wastage CASCADE")
    op.execute("DROP TYPE IF EXISTS wastage_status CASCADE")
