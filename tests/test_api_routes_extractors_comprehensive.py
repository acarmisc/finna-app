"""Comprehensive tests for api/routes/extractors.py - Extractor endpoints."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

os.environ["ENCRYPTION_KEY"] = "KjZlG4Cp3mN9qR7sT1uV5wX2yZ6aB8cD"


class TestRunExtractor:
    """Tests for POST /api/v1/extractors/run endpoint."""

    def test_run_extractor_with_config_id(self):
        """Test starting extractor with specific config ID."""
        from api.routes.extractors import run_extractor
        from api.models import Provider

        class MockRequest:
            provider = Provider.AZURE
            config_id = "test-config-id"
            extractor_type = "azure_cost"

        request = MockRequest()

        with patch("api.routes.extractors.start_extractor", return_value="new-run-id"):
            result = run_extractor(request)
            assert result is not None
            assert result["id"] == "new-run-id"
            assert result["config_id"] == "test-config-id"
            assert result["provider"] == "azure"

    def test_run_extractor_autoconfig(self):
        """Test starting extractor with auto-config lookup."""
        from api.routes.extractors import run_extractor
        from api.models import Provider

        class MockRequest:
            provider = Provider.AZURE
            config_id = None
            extractor_type = None

        request = MockRequest()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": "auto-config-id"}
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("api.routes.extractors.get_connection", return_value=mock_conn):
            with patch("api.routes.extractors.start_extractor", return_value="run-123"):
                result = run_extractor(request)
                assert result is not None
                assert result["config_id"] == "auto-config-id"

    def test_run_extractor_no_config_found(self):
        """Test starting extractor when no config exists."""
        from api.routes.extractors import run_extractor
        from api.models import Provider

        class MockRequest:
            provider = Provider.AZURE
            config_id = None
            extractor_type = None

        request = MockRequest()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("api.routes.extractors.get_connection", return_value=mock_conn):
            with pytest.raises(HTTPException) as exc_info:
                run_extractor(request)
            assert exc_info.value.status_code == 404
            assert "no configuration found" in exc_info.value.detail.lower()

    def test_run_extractor_custom_extractor_type(self):
        """Test starting extractor with custom extractor type."""
        from api.routes.extractors import run_extractor
        from api.models import Provider

        class MockRequest:
            provider = Provider.GCP
            config_id = "config-id"
            extractor_type = "custom_extractor"

        request = MockRequest()

        with patch("api.routes.extractors.start_extractor", return_value="run-456"):
            result = run_extractor(request)
            assert result is not None
            assert result["extractor_type"] == "custom_extractor"

    def test_run_extractor_default_extractor_type(self):
        """Test starting extractor with default extractor type."""
        from api.routes.extractors import run_extractor
        from api.models import Provider

        class MockRequest:
            provider = Provider.AZURE
            config_id = "config-id"
            extractor_type = None

        request = MockRequest()

        with patch("api.routes.extractors.start_extractor", return_value="run-789"):
            result = run_extractor(request)
            assert result is not None
            assert result["extractor_type"] == "azure_cost"


class TestGetStatus:
    """Tests for GET /api/v1/extractors/status endpoint."""

    def test_get_status_success(self):
        """Test getting extractor status."""
        from api.routes.extractors import get_status

        mock_run = {
            "id": "test-run-id",
            "config_id": "test-config-id",
            "provider": "azure",
            "extractor_type": "azure_cost",
            "status": "running",
            "started_at": datetime.now(timezone.utc),
        }

        with patch("api.routes.extractors.list_runs", return_value=[mock_run]):
            results = get_status()
            assert len(results) == 1
            assert results[0]["id"] == "test-run-id"

    def test_get_status_empty(self):
        """Test getting status when no runs exist."""
        from api.routes.extractors import get_status

        with patch("api.routes.extractors.list_runs", return_value=[]):
            results = get_status()
            assert results == []

    def test_get_status_with_provider_filter(self):
        """Test getting status filtered by provider."""
        from api.routes.extractors import get_status

        mock_run = {
            "id": "test-run-id",
            "provider": "azure",
            "extractor_type": "azure_cost",
            "status": "running",
            "started_at": datetime.now(timezone.utc),
        }

        with patch("api.routes.extractors.list_runs") as mock_list:
            mock_list.return_value = [mock_run]
            results = get_status(provider="azure")
            assert len(results) == 1


class TestGetRunDetail:
    """Tests for GET /api/v1/extractors/status/{run_id} endpoint."""

    def test_get_run_detail_success(self):
        """Test getting detailed run status."""
        from api.routes.extractors import get_run_detail

        mock_run = {
            "id": "test-run-id",
            "provider": "azure",
            "extractor_type": "azure_cost",
            "status": "running",
            "started_at": datetime.now(timezone.utc),
            "records_extracted": 100,
        }

        with patch("api.routes.extractors.get_run_status", return_value=mock_run):
            result = get_run_detail("test-run-id")
            assert result is not None
            assert result["id"] == "test-run-id"
            assert result["records_extracted"] == 100

    def test_get_run_detail_not_found(self):
        """Test getting detail for non-existent run."""
        from api.routes.extractors import get_run_detail

        with patch("api.routes.extractors.get_run_status", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                get_run_detail("non-existent-id")
            assert exc_info.value.status_code == 404

    def test_get_run_detail_with_error(self):
        """Test getting run status with error message."""
        from api.routes.extractors import get_run_detail

        mock_run = {
            "id": "test-run-id",
            "provider": "gcp",
            "extractor_type": "gcp_billing",
            "status": "failed",
            "started_at": datetime.now(timezone.utc),
            "finished_at": datetime.now(timezone.utc),
            "records_extracted": 50,
            "error_message": "Connection timeout",
        }

        with patch("api.routes.extractors.get_run_status", return_value=mock_run):
            result = get_run_detail("test-run-id")
            assert result["status"] == "failed"
            assert result["error_message"] == "Connection timeout"


class TestCancelExtractor:
    """Tests for POST /api/v1/extractors/cancel/{run_id} endpoint."""

    def test_cancel_extractor_success(self):
        """Test cancelling a running extractor."""
        from api.routes.extractors import cancel_extractor

        with patch("api.routes.extractors.cancel_run", return_value=True):
            result = cancel_extractor("test-run-id")
            assert result is not None
            assert result["status"] == "cancelled"
            assert result["run_id"] == "test-run-id"

    def test_cancel_extractor_not_found(self):
        """Test cancelling non-existent run."""
        from api.routes.extractors import cancel_extractor

        with patch("api.routes.extractors.cancel_run", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                cancel_extractor("non-existent-id")
            assert exc_info.value.status_code == 404


class TestGetExtractorHealth:
    """Tests for GET /api/v1/extractors/health endpoint."""

    def test_get_extractor_health(self):
        """Test getting extractor health status."""
        from api.routes.extractors import get_extractor_health

        health_data = [
            {
                "extractor_name": "azure_cost",
                "status": "healthy",
                "last_run": datetime.now(timezone.utc),
                "records_count": 100,
            },
            {
                "extractor_name": "gcp_billing",
                "status": "healthy",
                "last_run": datetime.now(timezone.utc),
                "records_count": 200,
            },
        ]

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = health_data
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("api.routes.extractors.get_connection", return_value=mock_conn):
            results = get_extractor_health()
            assert len(results) == 2
            assert results[0]["name"] == "azure_cost"
            assert results[1]["name"] == "gcp_billing"

    def test_get_extractor_health_empty(self):
        """Test getting health when no extractors exist."""
        from api.routes.extractors import get_extractor_health

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("api.routes.extractors.get_connection", return_value=mock_conn):
            results = get_extractor_health()
            assert results == []


class TestRunExtractorIntegration:
    """Integration tests for run_extractor."""

    def test_run_extractor_status_fields(self):
        """Test that run_extractor returns all expected status fields."""
        from api.routes.extractors import run_extractor
        from api.models import Provider

        class MockRequest:
            provider = Provider.AZURE
            config_id = "config-id"
            extractor_type = "azure_cost"

        request = MockRequest()

        with patch("api.routes.extractors.start_extractor", return_value="run-123"):
            result = run_extractor(request)
            assert "id" in result
            assert "config_id" in result
            assert "provider" in result
            assert "extractor_type" in result
            assert "status" in result
            assert "started_at" in result

    def test_run_extractor_gcp_provider(self):
        """Test running extractor for GCP provider."""
        from api.routes.extractors import run_extractor
        from api.models import Provider

        class MockRequest:
            provider = Provider.GCP
            config_id = "gcp-config"
            extractor_type = "gcp_billing"

        request = MockRequest()

        with patch("api.routes.extractors.start_extractor", return_value="gcp-run"):
            result = run_extractor(request)
            assert result["provider"] == "gcp"
            assert result["extractor_type"] == "gcp_billing"


class TestStatusFiltering:
    """Tests for status filtering functionality."""

    def test_get_status_limit(self):
        """Test getting status with limit."""
        from api.routes.extractors import get_status

        mock_runs = [
            {
                "id": f"run-{i}",
                "provider": "azure",
                "extractor_type": "azure_cost",
                "status": "running",
                "started_at": datetime.now(timezone.utc),
            }
            for i in range(10)
        ]

        with patch("api.routes.extractors.list_runs", return_value=mock_runs):
            results = get_status(limit=5)
            assert len(results) == 5

    def test_get_status_combined_filter(self):
        """Test getting status with combined filters."""
        from api.routes.extractors import get_status

        mock_runs = [
            {
                "id": "run-1",
                "provider": "azure",
                "extractor_type": "azure_cost",
                "status": "running",
                "started_at": datetime.now(timezone.utc),
            },
            {
                "id": "run-2",
                "provider": "azure",
                "extractor_type": "azure_cost",
                "status": "success",
                "started_at": datetime.now(timezone.utc),
                "finished_at": datetime.now(timezone.utc),
            },
        ]

        with patch("api.routes.extractors.list_runs", return_value=mock_runs):
            results = get_status(provider="azure")
            assert len(results) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
