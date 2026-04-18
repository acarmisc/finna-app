"""Integration tests for AWS Cost Explorer extractor."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


os.environ["AWS_ACCESS_KEY_ID"] = "test-aws-key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test-aws-secret"
os.environ["AWS_REGION"] = "us-east-1"


class TestAWSExtractor:
    """Tests for AWS Cost Explorer extractor."""

    def test_aws_extractor_module_exists(self):
        """Test that AWS extractor module can be imported."""
        import extractors.aws_extractor

        assert hasattr(extractors.aws_extractor, "extract_costs")

    def test_aws_extractor_function(self):
        """Test AWS extractor function signature."""
        from extractors.aws_extractor import extract_costs

        assert callable(extract_costs)

    def test_aws_extractor_config(self):
        """Test AWS extractor configuration."""
        from api.extractors import get_extractor

        assert callable(get_extractor)

    def test_aws_cost_extraction(self):
        """Test AWS cost extraction."""
        with patch("boto3.client") as mock_boto:
            mock_client = MagicMock()
            mock_client.get_cost_and_usage.return_value = {
                "ResultsByTime": [
                    {
                        "TimePeriod": {
                            "Start": (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
                            "End": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        },
                        "Total": {"UnblendedCost": {"Amount": "100.50", "Unit": "USD"}},
                    }
                ]
            }
            mock_boto.return_value = mock_client

            from extractors.aws_extractor import extract_costs

            result = extract_costs(
                config={
                    "aws_access_key_id": "test-key",
                    "aws_secret_access_key": "test-secret",
                },
                start_date=(datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
                end_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            )

            assert result is not None


class TestAWSExtractorEndpoints:
    """Tests for AWS extractor API endpoints."""

    def test_run_aws_extractor(self):
        """Test running AWS extractor via API."""
        request_data = {
            "provider": "aws",
            "extractor_type": "aws_cost",
        }

        with patch("api.runner.start_extractor", return_value="aws-run-id"):
            with patch("api.db.get_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = {
                    "id": "aws-config-id",
                    "config": {
                        "aws_access_key_id": "test-key",
                        "aws_secret_access_key": "test-secret",
                    },
                    "credential_type": "cli",
                }
                mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn

                from api.main import app

                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.post("/api/v1/extractors/run", json=request_data)

                    assert response.status_code == 200
                    data = response.json()
                    assert "id" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
