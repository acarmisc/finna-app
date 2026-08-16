"""Real-database round-trip regression guard for the P0-1 batch-insert defect.

The mock-based unit tests (test_aws_cost.py, test_litellm_cost.py,
test_azure_extractor.py, test_gcp_extractor.py) all pass a MagicMock
connection, which accepts any argument count — so an INSERT with mismatched
column/placeholder counts passes those tests and only fails against a real
psycopg connection. This file closes that gap: it inserts one real record
per extractor into the live `cost_records` table and reads it back.

See docs/audit-and-bedrock-plan.md P0-1. Requires a live PostgreSQL
(same requirement as the other @pytest.mark.integration tests).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal

import psycopg
import pytest

from extractors import aws_cost, azure_cost, litellm_cost
from models import NormalizedCostRecord, Provider, ServiceCategory

pytestmark = pytest.mark.integration


@pytest.fixture
def db_conn():
    conn = psycopg.connect(os.environ["PG_DSN"])
    yield conn
    conn.rollback()
    conn.close()


def _make_record(provider: Provider, record_id: str, **overrides: object) -> NormalizedCostRecord:
    base = dict(
        record_id=record_id,
        provider=provider,
        usage_start=datetime(2024, 3, 15, tzinfo=UTC),
        usage_end=datetime(2024, 3, 16, tzinfo=UTC),
        account_id="acc-1",
        project_id="proj-1",
        service_category=ServiceCategory.COMPUTE,
        service_name="svc",
        cost_usd=Decimal("1.50"),
        currency_original="USD",
        cost_original=Decimal("1.50"),
        discount_usd=Decimal("0"),
        net_cost_usd=Decimal("1.50"),
    )
    base.update(overrides)
    return NormalizedCostRecord(**base)


@pytest.mark.parametrize(
    "module,provider,record_id",
    [
        (aws_cost, Provider.AWS, "roundtrip-guard-aws-0001"),
        (litellm_cost, Provider.LLM, "roundtrip-guard-llm-0001"),
        (azure_cost, Provider.AZURE, "roundtrip-guard-azure-0001"),
    ],
)
def test_extractor_insert_records_roundtrip(db_conn, module, provider, record_id) -> None:
    """insert_records() must write a real, readable row — not just satisfy a mock."""
    db_conn.execute("DELETE FROM cost_records WHERE record_id = %s", (record_id,))
    db_conn.commit()

    record = _make_record(provider, record_id)
    try:
        inserted = module.insert_records(db_conn, [record], batch_size=500)
        assert inserted == 1

        row = db_conn.execute(
            "SELECT record_id, provider, cost_usd FROM cost_records WHERE record_id = %s",
            (record_id,),
        ).fetchone()
        assert row is not None, "record was not persisted"
        assert row[0] == record_id
        assert row[1] == provider.value
        assert row[2] == Decimal("1.500000")
    finally:
        db_conn.execute("DELETE FROM cost_records WHERE record_id = %s", (record_id,))
        db_conn.commit()
