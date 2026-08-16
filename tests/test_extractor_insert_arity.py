"""Regression guard for the P0-1 batch-insert defect class.

azure_cost.py, litellm_cost.py, and aws_cost.py once declared more INSERT
columns than SQL placeholders, so every batch insert failed at the database
with a psycopg ProgrammingError at runtime — invisible to the pre-existing
unit tests because they pass a MagicMock connection, which silently accepts
any argument count regardless of arity.

These tests call each extractor's real batch-insert function against a
mocked connection and assert the SQL passed to executemany() has exactly as
many %s placeholders as each row tuple has values — the same mismatch
psycopg raises on at runtime. See docs/audit-and-bedrock-plan.md P0-1.
"""

from __future__ import annotations

import importlib
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from models import NormalizedCostRecord, Provider, ServiceCategory


def _make_record(provider: Provider) -> NormalizedCostRecord:
    return NormalizedCostRecord(
        record_id="arity-check-0001",
        provider=provider,
        usage_start=datetime(2024, 1, 1, tzinfo=UTC),
        usage_end=datetime(2024, 1, 2, tzinfo=UTC),
        account_id="acc-1",
        project_id="proj-1",
        service_category=ServiceCategory.COMPUTE,
        service_name="svc",
        cost_usd=Decimal("1.00"),
        currency_original="USD",
        cost_original=Decimal("1.00"),
        discount_usd=Decimal("0"),
        net_cost_usd=Decimal("1.00"),
    )


@pytest.mark.parametrize(
    "module_path,func_name,provider",
    [
        ("extractors.aws_cost", "_insert_batch", Provider.AWS),
        ("extractors.litellm_cost", "_insert_batch", Provider.LLM),
        ("extractors.azure_cost", "_insert_batch", Provider.AZURE),
        ("extractors.gcp_billing", "_batch_insert", Provider.GCP),
    ],
)
def test_batch_insert_sql_arity(module_path: str, func_name: str, provider: Provider) -> None:
    """The SQL passed to executemany() must have exactly as many %s
    placeholders as each row tuple has values, for every cost extractor."""
    mod = importlib.import_module(module_path)
    insert_fn = getattr(mod, func_name)

    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
    # gcp_billing's _batch_insert loops `while True: ... if not cur.nextset(): break`
    # and iterates `cur` directly (RETURNING rows) — a bare MagicMock never returns
    # a falsy nextset() or supports iteration, so without these it hangs forever.
    mock_cursor.nextset.return_value = False
    mock_cursor.__iter__.return_value = iter([])

    insert_fn(mock_conn, [_make_record(provider)])

    assert mock_cursor.executemany.called, f"{module_path}.{func_name} did not call executemany()"
    call = mock_cursor.executemany.call_args
    sql_text = str(call.args[0])
    rows = call.args[1]
    placeholder_count = sql_text.count("%s")
    row_len = len(rows[0])
    assert placeholder_count == row_len, (
        f"{module_path}: SQL has {placeholder_count} '%s' placeholders but each "
        f"row tuple has {row_len} values. This mismatch causes a psycopg "
        f"ProgrammingError at insert time — see docs/audit-and-bedrock-plan.md P0-1."
    )
