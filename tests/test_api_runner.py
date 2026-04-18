"""Tests for api/runner.py - Extractor subprocess management (focused on core logic)."""

from __future__ import annotations

import os
from unittest.mock import patch


class TestRunnerHelpers:
    """Tests for runner helper functions."""

    def test_get_pg_dsn(self):
        """Test _get_pg_dsn returns env var."""
        from api.runner import _get_pg_dsn

        with patch.dict(os.environ, {"PG_DSN": "postgresql://test:5432/db"}):
            result = _get_pg_dsn()
            assert result == "postgresql://test:5432/db"

    def test_get_extractor_type_azure(self):
        """Test _get_extractor_type maps Azure correctly."""
        from api.runner import _get_extractor_type

        result = _get_extractor_type("azure")
        assert result == "azure_cost"

    def test_get_extractor_type_gcp(self):
        """Test _get_extractor_type maps GCP correctly."""
        from api.runner import _get_extractor_type

        result = _get_extractor_type("gcp")
        assert result == "gcp_billing"

    def test_get_extractor_type_custom(self):
        """Test _get_extractor_type returns provider for unknown."""
        from api.runner import _get_extractor_type

        result = _get_extractor_type("custom_provider")
        assert result == "custom_provider"


class TestBuildEnvFromConfig:
    """Tests for _build_env_from_config function."""

    def test_build_env_azure_cli(self):
        """Test building env for Azure with CLI auth."""
        from api.runner import _build_env_from_config

        config = {"credential_type": "cli", "subscription_id": "sub-123"}
        result = _build_env_from_config(config, "azure")

        assert result["AZURE_AUTH_METHOD"] == "cli"
        assert result["AZURE_SUBSCRIPTION_ID"] == "sub-123"

    def test_build_env_azure_client_secret(self):
        """Test building env for Azure with client secret."""
        from api.runner import _build_env_from_config

        config = {
            "tenant_id": "tenant-123",
            "client_id": "client-123",
            "client_secret": "secret-123",
            "subscription_id": "sub-123",
        }
        result = _build_env_from_config(config, "azure")

        assert result["AZURE_TENANT_ID"] == "tenant-123"
        assert result["AZURE_CLIENT_ID"] == "client-123"
        assert result["AZURE_CLIENT_SECRET"] == "secret-123"

    def test_build_env_gcp(self):
        """Test building env for GCP."""
        from api.runner import _build_env_from_config

        config = {
            "project_id": "gcp-project-123",
            "bigquery_dataset": "dataset1",
            "bigquery_table": "table1",
        }
        result = _build_env_from_config(config, "gcp")

        assert result["GCP_PROJECT"] == "gcp-project-123"
        assert result["BQ_DATASET"] == "dataset1"
        assert result["BQ_TABLE"] == "table1"

    def test_build_env_includes_pg_dsn(self):
        """Test building env includes PG_DSN."""
        from api.runner import _build_env_from_config

        config = {"subscription_id": "sub-123"}

        with patch.dict(os.environ, {"PG_DSN": "postgresql://test:5432/db"}):
            result = _build_env_from_config(config, "azure")
            assert "PG_DSN" in result


class TestBuildEnvEdgeCases:
    """Test edge cases for environment building."""

    def test_build_env_no_credentials(self):
        """Test building env without any credentials."""
        from api.runner import _build_env_from_config

        config = {"subscription_id": "sub-123"}
        result = _build_env_from_config(config, "azure")

        assert result["AZURE_AUTH_METHOD"] == "cli"
        assert result["AZURE_SUBSCRIPTION_ID"] == "sub-123"

    def test_build_env_with_resource_groups(self):
        """Test building env with resource groups."""
        from api.runner import _build_env_from_config

        config = {
            "subscription_id": "sub-123",
            "resource_groups": ["rg1", "rg2", "rg3"],
        }
        result = _build_env_from_config(config, "azure")

        assert result["AZURE_RESOURCE_GROUPS"] == "rg1,rg2,rg3"


class TestExtractorTypeMapping:
    """Tests for provider to extractor type mapping."""

    def test_mappings_complete(self):
        """Test all expected providers have mappings."""
        from api.runner import _get_extractor_type

        assert _get_extractor_type("azure") == "azure_cost"
        assert _get_extractor_type("gcp") == "gcp_billing"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
