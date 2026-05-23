"""Tests for multi-subscription / multi-project environment discovery and iteration."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from extractors.azure_cost import (
    discover_azure_subscriptions_from_env,
    run_extractor,
)
from extractors.gcp_billing import (
    discover_gcp_projects_from_env,
    extract,
)

# ---------------------------------------------------------------------------
# Azure: discover_azure_subscriptions_from_env
# ---------------------------------------------------------------------------


class TestDiscoverAzureSubscriptions:
    def test_single_prefixed_subscription(self, monkeypatch):
        monkeypatch.setenv("AZURE_ABC123_SUBSCRIPTION_ID", "sub-001")
        monkeypatch.setenv("AZURE_ABC123_TENANT_ID", "tenant-001")
        monkeypatch.setenv("AZURE_ABC123_CLIENT_ID", "client-001")
        monkeypatch.setenv("AZURE_ABC123_CLIENT_SECRET", "secret-001")

        result = discover_azure_subscriptions_from_env()
        assert "ABC123" in result
        assert result["ABC123"]["subscription_id"] == "sub-001"
        assert result["ABC123"]["tenant_id"] == "tenant-001"
        assert result["ABC123"]["client_id"] == "client-001"
        assert result["ABC123"]["client_secret"] == "secret-001"
        assert result["ABC123"]["scope"] == "resourcegroup"
        assert result["ABC123"]["mgmt_group_id"] == ""

    def test_multiple_subscriptions(self, monkeypatch):
        monkeypatch.setenv("AZURE_SUB_A_SUBSCRIPTION_ID", "sub-aaa")
        monkeypatch.setenv("AZURE_SUB_A_TENANT_ID", "tenant-aaa")
        monkeypatch.setenv("AZURE_SUB_A_CLIENT_ID", "client-aaa")
        monkeypatch.setenv("AZURE_SUB_A_CLIENT_SECRET", "secret-aaa")
        monkeypatch.setenv("AZURE_SUB_B_SUBSCRIPTION_ID", "sub-bbb")
        monkeypatch.setenv("AZURE_SUB_B_TENANT_ID", "tenant-bbb")
        monkeypatch.setenv("AZURE_SUB_B_CLIENT_ID", "client-bbb")
        monkeypatch.setenv("AZURE_SUB_B_CLIENT_SECRET", "secret-bbb")

        result = discover_azure_subscriptions_from_env()
        assert len(result) == 2
        assert result["SUB_A"]["subscription_id"] == "sub-aaa"
        assert result["SUB_B"]["subscription_id"] == "sub-bbb"

    def test_empty_env_returns_empty(self, monkeypatch):
        monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
        for key in list(os.environ):
            if key.startswith("AZURE_") and key.endswith("_SUBSCRIPTION_ID"):
                monkeypatch.delenv(key, raising=False)

        result = discover_azure_subscriptions_from_env()
        assert result == {}

    def test_scope_and_mgmt_group_parsed(self, monkeypatch):
        monkeypatch.setenv("AZURE_MG_SUB_SUBSCRIPTION_ID", "sub-mg")
        monkeypatch.setenv("AZURE_MG_SUB_TENANT_ID", "tenant-mg")
        monkeypatch.setenv("AZURE_MG_SUB_CLIENT_ID", "client-mg")
        monkeypatch.setenv("AZURE_MG_SUB_CLIENT_SECRET", "secret-mg")
        monkeypatch.setenv("AZURE_MG_SUB_SCOPE", "managementgroup")
        monkeypatch.setenv("AZURE_MG_SUB_MGMT_GROUP_ID", "mg-001")

        result = discover_azure_subscriptions_from_env()
        assert result["MG_SUB"]["scope"] == "managementgroup"
        assert result["MG_SUB"]["mgmt_group_id"] == "mg-001"

    def test_empty_subscription_id_skipped(self, monkeypatch):
        monkeypatch.setenv("AZURE_EMPTY_SUB_SUBSCRIPTION_ID", "")
        result = discover_azure_subscriptions_from_env()
        assert "EMPTY_SUB" not in result

    def test_does_not_match_legacy_single_var(self, monkeypatch):
        """AZURE_SUBSCRIPTION_ID (no prefix) should NOT be discovered."""
        monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "legacy-sub")
        for key in list(os.environ):
            if key.startswith("AZURE_") and key.endswith("_SUBSCRIPTION_ID") and key != "AZURE_SUBSCRIPTION_ID":
                monkeypatch.delenv(key, raising=False)
        result = discover_azure_subscriptions_from_env()
        assert result == {}


# ---------------------------------------------------------------------------
# Azure: multi-subscription iteration in run_extractor
# ---------------------------------------------------------------------------


class TestAzureMultiSubscriptionRun:
    @patch("extractors.azure_cost.psycopg.connect")
    @patch("extractors.azure_cost.fetch_cost_rows")
    @patch("extractors.azure_cost._create_azure_client")
    def test_run_extractor_with_explicit_credentials(self, mock_client_fn, mock_fetch, mock_pg_connect):
        """run_extractor should accept tenant_id/client_id/client_secret params."""
        from datetime import datetime, timezone

        mock_fetch.return_value = []

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pg_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pg_connect.return_value.__exit__ = MagicMock(return_value=False)

        total = run_extractor(
            pg_dsn="postgresql://test:test@localhost/test",
            date_from=datetime(2024, 3, 1, tzinfo=timezone.utc),
            date_to=datetime(2024, 3, 31, tzinfo=timezone.utc),
            subscription_id="sub-001",
            tenant_id="tenant-001",
            client_id="client-001",
            client_secret="secret-001",
            health_provider="azure_prod",
            resource_group="test-rg",
        )
        assert total == 0
        mock_client_fn.assert_called_once_with(
            tenant_id="tenant-001",
            client_id="client-001",
            client_secret="secret-001",
            subscription_id="sub-001",
        )

    @patch("extractors.azure_cost.psycopg.connect")
    @patch("extractors.azure_cost.fetch_cost_rows")
    @patch("extractors.azure_cost._create_azure_client")
    def test_run_extractor_backward_compat(self, mock_client_fn, mock_fetch, mock_pg_connect, monkeypatch):
        """Single-subscription mode via AZURE_SUBSCRIPTION_ID still works."""
        from datetime import datetime, timezone

        monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "legacy-sub")
        monkeypatch.setenv("AZURE_TENANT_ID", "legacy-tenant")
        monkeypatch.setenv("AZURE_CLIENT_ID", "legacy-client")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "legacy-secret")
        monkeypatch.setenv("PG_DSN", "postgresql://test:test@localhost/test")

        mock_fetch.return_value = []

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pg_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pg_connect.return_value.__exit__ = MagicMock(return_value=False)

        total = run_extractor(
            date_from=datetime(2024, 3, 1, tzinfo=timezone.utc),
            date_to=datetime(2024, 3, 31, tzinfo=timezone.utc),
            resource_group="test-rg",
        )
        assert total == 0


# ---------------------------------------------------------------------------
# GCP: discover_gcp_projects_from_env
# ---------------------------------------------------------------------------


class TestDiscoverGcpProjects:
    def test_single_prefixed_project(self, monkeypatch):
        monkeypatch.setenv("GCP_MY_PROJECT_PROJECT", "my-project-prod")
        monkeypatch.setenv("GCP_MY_PROJECT_BQ_DATASET", "billing_ds")
        monkeypatch.setenv("GCP_MY_PROJECT_BQ_TABLE", "billing_tbl")
        monkeypatch.setenv("GCP_MY_PROJECT_INGESTION_MODE", "csv")
        monkeypatch.setenv("GCP_MY_PROJECT_CSV_PATH", "/data/billing.csv")

        result = discover_gcp_projects_from_env()
        assert "MY_PROJECT" in result
        assert result["MY_PROJECT"]["project_id"] == "my-project-prod"
        assert result["MY_PROJECT"]["bq_dataset"] == "billing_ds"
        assert result["MY_PROJECT"]["bq_table"] == "billing_tbl"
        assert result["MY_PROJECT"]["ingestion_mode"] == "csv"
        assert result["MY_PROJECT"]["csv_path"] == "/data/billing.csv"

    def test_multiple_projects(self, monkeypatch):
        monkeypatch.setenv("GCP_PROD_PROJECT", "prod-project")
        monkeypatch.setenv("GCP_STAGING_PROJECT", "staging-project")

        result = discover_gcp_projects_from_env()
        assert len(result) == 2
        assert result["PROD"]["project_id"] == "prod-project"
        assert result["STAGING"]["project_id"] == "staging-project"

    def test_empty_env_returns_empty(self, monkeypatch):
        monkeypatch.delenv("GCP_PROJECT", raising=False)
        for key in list(os.environ):
            if key.startswith("GCP_") and key.endswith("_PROJECT"):
                monkeypatch.delenv(key, raising=False)

        result = discover_gcp_projects_from_env()
        assert result == {}

    def test_defaults_when_partial_env(self, monkeypatch):
        monkeypatch.setenv("GCP_PARTIAL_PROJECT", "partial-proj")
        result = discover_gcp_projects_from_env()
        assert result["PARTIAL"]["project_id"] == "partial-proj"
        assert result["PARTIAL"]["bq_dataset"] == "billing_export"
        assert result["PARTIAL"]["bq_table"] == "gcp_billing_export_v1"
        assert result["PARTIAL"]["ingestion_mode"] == "bigquery"
        assert result["PARTIAL"]["csv_path"] == ""

    def test_empty_project_id_skipped(self, monkeypatch):
        monkeypatch.setenv("GCP_EMPTY_PROJECT", "")
        result = discover_gcp_projects_from_env()
        assert "EMPTY" not in result

    def test_does_not_match_legacy_single_var(self, monkeypatch):
        monkeypatch.setenv("GCP_PROJECT", "legacy-project")
        for key in list(os.environ):
            if key.startswith("GCP_") and key.endswith("_PROJECT") and key != "GCP_PROJECT":
                monkeypatch.delenv(key, raising=False)
        result = discover_gcp_projects_from_env()
        assert result == {}


# ---------------------------------------------------------------------------
# GCP: multi-project iteration via extract()
# ---------------------------------------------------------------------------


class TestGcpMultiProjectExtract:
    @patch("extractors.gcp_billing._get_pg_connection")
    @patch("extractors.gcp_billing.bigquery.Client")
    def test_extract_with_custom_health_name(self, mock_bq_cls, mock_pg_conn_factory):
        """extract() should raise RuntimeError when 0 records are inserted and mark health as failed."""
        mock_bq_client = MagicMock()
        mock_bq_cls.return_value = mock_bq_client

        mock_query_job = MagicMock()
        mock_bq_client.query.return_value = mock_query_job

        mock_row_iter = MagicMock()
        mock_row_iter.__iter__ = lambda self: iter([])
        mock_query_job.result.return_value = mock_row_iter

        mock_pg_conn = MagicMock()
        mock_pg_conn_factory.return_value = mock_pg_conn

        with pytest.raises(RuntimeError, match="Extraction completed but no records were inserted"):
            extract(
                gcp_project="my-proj",
                bq_dataset="billing",
                bq_table="export",
                pg_dsn="postgresql://user:***@localhost/db",
                date_from="2025-03-01",
                date_to="2025-04-01",
                health_name="gcp_billing_prod",
            )

        mock_pg_conn.close.assert_called_once()
