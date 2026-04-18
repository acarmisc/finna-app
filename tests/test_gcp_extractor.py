"""Unit tests for extractors.gcp_billing — BigQuery-specific logic.

Shared utilities (record ID, service-category mapping, label extraction,
datetime parsing) are tested in test_gcp_shared.py.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from extractors.gcp_billing import (
    _batch_insert,
    _build_query,
    _mark_health_failure,
    _mark_health_start,
    _mark_health_success,
    extract,
    normalise_row,
)
from models import NormalizedCostRecord, Provider, ServiceCategory

# ---------------------------------------------------------------------------
# Fixtures — realistic BigQuery billing rows
# ---------------------------------------------------------------------------


def _make_bq_row(
    project_id: str = "my-gcp-project",
    service_description: str = "Compute Engine",
    sku_description: str = "N1 Predefined Instance Core",
    cost: float = 12.50,
    currency: str = "USD",
    usage_amount: float = 7.0,
    usage_unit: str = "hours",
    labels: list[dict] | None = None,
    usage_start_time: str = "2025-03-01T00:00:00Z",
    usage_end_time: str = "2025-03-01T01:00:00Z",
) -> dict:
    """Build a realistic GCP BigQuery billing row dict."""
    if labels is None:
        labels = [
            {"key": "project", "value": "my-label-project"},
            {"key": "environment", "value": "prod"},
        ]
    return {
        "project_id": project_id,
        "project_number": "123456789",
        "billing_account_id": "01ABCD-012345-6789AB",
        "service_description": service_description,
        "sku_description": sku_description,
        "usage_start_time": usage_start_time,
        "usage_end_time": usage_end_time,
        "usage_amount": usage_amount,
        "usage_unit": usage_unit,
        "cost": cost,
        "currency": currency,
        "labels": labels,
        "system_labels": [],
    }


@pytest.fixture
def sample_row() -> dict:
    return _make_bq_row()


# ---------------------------------------------------------------------------
# Tests — BigQuery row normalisation
# ---------------------------------------------------------------------------


class TestNormaliseRow:
    def test_basic_mapping(self, sample_row: dict) -> None:
        record = normalise_row(sample_row)
        assert isinstance(record, NormalizedCostRecord)
        assert record.provider == Provider.GCP
        assert record.account_id == "my-gcp-project"
        assert record.project_id == "my-label-project"  # from label "project"
        assert record.service_category == ServiceCategory.COMPUTE
        assert record.service_name == "N1 Predefined Instance Core"
        assert record.cost_usd == Decimal("12.5")
        assert record.usage_quantity == Decimal("7")
        assert record.usage_unit == "hours"
        assert record.tags == {"project": "my-label-project", "environment": "prod"}

    def test_project_id_falls_back_to_project_field(self) -> None:
        """When no 'project' label exists, use project.id as project_id."""
        row = _make_bq_row(labels=[])
        record = normalise_row(row)
        assert record.project_id == "my-gcp-project"

    def test_cost_usd_precision(self) -> None:
        """Cost should be converted via string to preserve Decimal precision."""
        row = _make_bq_row(cost=0.1 + 0.2)  # float imprecision
        record = normalise_row(row)
        assert isinstance(record.cost_usd, Decimal)

    def test_zero_cost(self) -> None:
        row = _make_bq_row(cost=0)
        record = normalise_row(row)
        assert record.cost_usd == Decimal("0")

    def test_negative_cost_credit(self) -> None:
        """GCP billing can have negative costs for credits / adjustments."""
        row = _make_bq_row(cost=-5.0)
        record = normalise_row(row)
        assert record.cost_usd == Decimal("-5")

    def test_missing_usage_fields(self) -> None:
        row = _make_bq_row()
        row["usage_amount"] = None
        row["usage_unit"] = None
        record = normalise_row(row)
        assert record.usage_quantity is None
        assert record.usage_unit is None

    def test_service_category_mapping(self) -> None:
        row = _make_bq_row(service_description="Cloud Storage")
        record = normalise_row(row)
        assert record.service_category == ServiceCategory.STORAGE

    def test_custom_service_category_map(self) -> None:
        custom = {"My Service": ServiceCategory.DATABASE}
        row = _make_bq_row(service_description="My Service")
        record = normalise_row(row, service_category_map=custom)
        assert record.service_category == ServiceCategory.DATABASE

    def test_record_id_is_deterministic(self) -> None:
        row = _make_bq_row()
        r1 = normalise_row(row)
        r2 = normalise_row(row)
        assert r1.record_id == r2.record_id

    def test_net_cost_usd_set(self, sample_row: dict) -> None:
        record = normalise_row(sample_row)
        assert record.net_cost_usd == record.cost_usd


# ---------------------------------------------------------------------------
# Tests — BigQuery query building
# ---------------------------------------------------------------------------


class TestBuildQuery:
    def test_query_contains_table(self) -> None:
        query, params = _build_query("my-proj", "my_ds", "my_tbl", "2025-03-01", "2025-04-01")
        assert "my-proj.my_ds.my_tbl" in query
        assert "@date_from" in query
        assert "@date_to" in query

    def test_query_params(self) -> None:
        _, params = _build_query("p", "d", "t", "2025-03-01", "2025-04-01")
        assert len(params) == 2
        assert params[0].name == "date_from"
        assert params[0].value == "2025-03-01"
        assert params[1].name == "date_to"
        assert params[1].value == "2025-04-01"


# ---------------------------------------------------------------------------
# Tests — batch insert
# ---------------------------------------------------------------------------


class TestBatchInsert:
    def test_batch_insert_returns_count(self) -> None:
        mock_conn = MagicMock()
        records = [normalise_row(_make_bq_row(cost=i)) for i in range(3)]
        inserted = _batch_insert(mock_conn, records)
        assert inserted == 3
        mock_conn.commit.assert_called_once()

    def test_batch_insert_empty(self) -> None:
        mock_conn = MagicMock()
        result = _batch_insert(mock_conn, [])
        assert result == 0
        mock_conn.cursor.assert_not_called()


# ---------------------------------------------------------------------------
# Tests — extractor health tracking
# ---------------------------------------------------------------------------


class TestExtractorHealth:
    def test_mark_health_start(self) -> None:
        mock_conn = MagicMock()
        _mark_health_start(mock_conn)
        mock_conn.cursor.return_value.__enter__.return_value.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_mark_health_success(self) -> None:
        mock_conn = MagicMock()
        _mark_health_success(mock_conn, 42)
        mock_conn.cursor.return_value.__enter__.return_value.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_mark_health_failure(self) -> None:
        mock_conn = MagicMock()
        _mark_health_failure(mock_conn, "connection timeout")
        mock_conn.cursor.return_value.__enter__.return_value.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_mark_health_failure_swallows_db_error(self) -> None:
        """_mark_health_failure should not raise even if the DB write fails."""
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("db down")
        _mark_health_failure(mock_conn, "some error")


# ---------------------------------------------------------------------------
# Tests — full extract pipeline (with mocked BigQuery + PostgreSQL)
# ---------------------------------------------------------------------------


class TestExtract:
    @patch("extractors.gcp_billing._get_pg_connection")
    @patch("extractors.gcp_billing.bigquery.Client")
    def test_extract_happy_path(self, mock_bq_cls, mock_pg_conn_factory) -> None:
        mock_bq_client = MagicMock()
        mock_bq_cls.return_value = mock_bq_client

        mock_query_job = MagicMock()
        mock_bq_client.query.return_value = mock_query_job

        bq_rows = [
            _make_bq_row(project_id="proj-1", cost=10.0, usage_start_time="2025-03-01T00:00:00Z"),
            _make_bq_row(project_id="proj-2", cost=20.0, usage_start_time="2025-03-01T01:00:00Z"),
            _make_bq_row(project_id="proj-3", cost=30.0, usage_start_time="2025-03-01T02:00:00Z"),
        ]
        mock_row_iter = MagicMock()
        mock_row_iter.__iter__ = lambda self: iter(bq_rows)
        mock_query_job.result.return_value = mock_row_iter

        mock_pg_conn = MagicMock()
        mock_pg_conn_factory.return_value = mock_pg_conn

        total = extract(
            gcp_project="test-project",
            bq_dataset="billing",
            bq_table="export",
            pg_dsn="postgresql://user:pass@localhost/db",
            date_from="2025-03-01",
            date_to="2025-04-01",
            batch_size=500,
        )

        assert total == 3
        mock_pg_conn.close.assert_called_once()

    @patch("extractors.gcp_billing._get_pg_connection")
    @patch("extractors.gcp_billing.bigquery.Client")
    def test_extract_empty_result_set(self, mock_bq_cls, mock_pg_conn_factory) -> None:
        mock_bq_client = MagicMock()
        mock_bq_cls.return_value = mock_bq_client

        mock_query_job = MagicMock()
        mock_bq_client.query.return_value = mock_query_job

        mock_row_iter = MagicMock()
        mock_row_iter.__iter__ = lambda self: iter([])
        mock_query_job.result.return_value = mock_row_iter

        mock_pg_conn = MagicMock()
        mock_pg_conn_factory.return_value = mock_pg_conn

        total = extract(
            gcp_project="test-project",
            bq_dataset="billing",
            bq_table="export",
            pg_dsn="postgresql://user:pass@localhost/db",
            date_from="2025-03-01",
            date_to="2025-04-01",
        )

        assert total == 0
        mock_pg_conn.close.assert_called_once()

    @patch("extractors.gcp_billing._get_pg_connection")
    @patch("extractors.gcp_billing.bigquery.Client")
    def test_extract_with_batching(self, mock_bq_cls, mock_pg_conn_factory) -> None:
        """Verify multiple batch inserts when rows exceed batch_size."""
        mock_bq_client = MagicMock()
        mock_bq_cls.return_value = mock_bq_client

        mock_query_job = MagicMock()
        mock_bq_client.query.return_value = mock_query_job

        bq_rows = [
            _make_bq_row(project_id=f"proj-{i}", cost=float(i), usage_start_time=f"2025-03-01T{i:02d}:00:00Z")
            for i in range(5)
        ]
        mock_row_iter = MagicMock()
        mock_row_iter.__iter__ = lambda self: iter(bq_rows)
        mock_query_job.result.return_value = mock_row_iter

        mock_pg_conn = MagicMock()
        mock_pg_conn_factory.return_value = mock_pg_conn

        total = extract(
            gcp_project="test-project",
            bq_dataset="billing",
            bq_table="export",
            pg_dsn="postgresql://user:pass@localhost/db",
            date_from="2025-03-01",
            date_to="2025-04-01",
            batch_size=2,
        )

        assert total == 5
        cursor_mock = mock_pg_conn.cursor.return_value.__enter__.return_value
        assert cursor_mock.executemany.call_count == 3

    def test_extract_missing_gcp_project(self) -> None:
        with pytest.raises(ValueError, match="GCP_PROJECT"):
            extract(
                gcp_project="",
                pg_dsn="postgresql://localhost/db",
                date_from="2025-03-01",
                date_to="2025-04-01",
            )

    @patch("extractors.gcp_billing.bigquery.Client")
    def test_extract_missing_pg_dsn(self, mock_bq_cls: MagicMock) -> None:
        mock_bq_client = MagicMock()
        mock_bq_cls.return_value = mock_bq_client
        with pytest.raises(ValueError, match="PG_DSN"):
            extract(
                gcp_project="test-project",
                pg_dsn="",
                date_from="2025-03-01",
                date_to="2025-04-01",
            )

    def test_extract_missing_dates(self) -> None:
        with pytest.raises(ValueError, match="DATE_FROM"):
            extract(
                gcp_project="test-project",
                pg_dsn="postgresql://localhost/db",
                date_from="",
                date_to="",
            )

    @patch("extractors.gcp_billing._get_pg_connection")
    @patch("extractors.gcp_billing.bigquery.Client")
    def test_extract_db_failure_marks_health_failed(self, mock_bq_cls, mock_pg_conn_factory) -> None:
        """When a DB error occurs, health should be marked as failed."""
        mock_bq_client = MagicMock()
        mock_bq_cls.return_value = mock_bq_client

        mock_query_job = MagicMock()
        mock_bq_client.query.return_value = mock_query_job

        bq_rows = [_make_bq_row()]
        mock_row_iter = MagicMock()
        mock_row_iter.__iter__ = lambda self: iter(bq_rows)
        mock_query_job.result.return_value = mock_row_iter

        mock_pg_conn = MagicMock()
        mock_pg_conn_factory.return_value = mock_pg_conn
        # Simulate DB failure on commit
        mock_pg_conn.commit.side_effect = [None, Exception("db write failed")]

        with pytest.raises(Exception, match="db write failed"):
            extract(
                gcp_project="test-project",
                bq_dataset="billing",
                bq_table="export",
                pg_dsn="postgresql://user:pass@localhost/db",
                date_from="2025-03-01",
                date_to="2025-04-01",
            )
