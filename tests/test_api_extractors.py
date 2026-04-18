"""Integration tests for Extractor API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestRunExtractor:
    """Tests for POST /api/v1/extractors/run endpoint."""

    def test_run_extractor_with_config_id(self, client):
        """Test starting extractor with specific config ID."""
        request_data = {
            "provider": "azure",
            "config_id": "test-config-id",
            "extractor_type": "azure_cost",
        }

        with patch("api.db.get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.side_effect = [
                {"id": "test-config-id", "config": {"tenant_id": "test"}, "credential_type": "service_principal"},
                {"id": "test-config-id"},
            ]
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            with patch("api.runner.start_extractor", return_value="new-run-id"):
                response = client.post("/api/v1/extractors/run", json=request_data)

                assert response.status_code == 200
                data = response.json()
                assert "id" in data
                assert data["config_id"] == "test-config-id"
                assert data["provider"] == "azure"

    def test_run_extractor_no_config_found(self, client):
        """Test starting extractor when no config exists for provider."""
        request_data = {"provider": "azure"}

        with patch("api.db.get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            response = client.post("/api/v1/extractors/run", json=request_data)

            assert response.status_code == 404
            assert "no configuration found" in response.json()["detail"].lower()

    def test_run_extractor_invalid_provider(self, client):
        """Test starting extractor with invalid provider."""
        request_data = {"provider": "invalid_provider"}

        response = client.post("/api/v1/extractors/run", json=request_data)

        assert response.status_code == 422


class TestGetExtractorStatus:
    """Tests for GET /api/v1/extractors/status endpoint."""

    def test_get_status_success(self, client):
        """Test getting extractor status."""
        mock_run = {
            "id": "test-run-id",
            "config_id": "test-config-id",
            "provider": "azure",
            "extractor_type": "azure_cost",
            "status": "running",
            "started_at": datetime.now(timezone.utc),
        }

        with patch("api.runner.list_runs", return_value=[mock_run]):
            response = client.get("/api/v1/extractors/status")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "test-run-id"

    def test_get_status_empty(self, client):
        """Test getting status when no runs exist."""
        with patch("api.runner.list_runs", return_value=[]):
            response = client.get("/api/v1/extractors/status")

            assert response.status_code == 200
            assert response.json() == []

    def test_get_status_with_provider_filter(self, client):
        """Test getting status filtered by provider."""
        mock_run = {
            "id": "test-run-id",
            "config_id": "test-config-id",
            "provider": "azure",
            "extractor_type": "azure_cost",
            "status": "running",
            "started_at": datetime.now(timezone.utc),
        }

        with patch("api.runner.list_runs", return_value=[mock_run]):
            response = client.get("/api/v1/extractors/status?provider=azure")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["provider"] == "azure"


class TestGetRunDetail:
    """Tests for GET /api/v1/extractors/status/{run_id} endpoint."""

    def test_get_run_detail_success(self, client):
        """Test getting detailed run status."""
        mock_run = {
            "id": "test-run-id",
            "config_id": "test-config-id",
            "provider": "azure",
            "extractor_type": "azure_cost",
            "status": "running",
            "started_at": datetime.now(timezone.utc),
        }

        with patch("api.runner.get_run_status", return_value=mock_run):
            response = client.get("/api/v1/extractors/status/test-run-id")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test-run-id"

    def test_get_run_detail_not_found(self, client):
        """Test getting detail for non-existent run."""
        with patch("api.runner.get_run_status", return_value=None):
            response = client.get("/api/v1/extractors/status/non-existent-id")

            assert response.status_code == 404


class TestCancelExtractor:
    """Tests for POST /api/v1/extractors/cancel/{run_id} endpoint."""

    def test_cancel_extractor_success(self, client):
        """Test cancelling a running extractor."""
        with patch("api.runner.cancel_run", return_value=True):
            response = client.post("/api/v1/extractors/cancel/test-run-id")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "cancelled"

    def test_cancel_extractor_not_found(self, client):
        """Test cancelling non-existent run."""
        with patch("api.runner.cancel_run", return_value=False):
            response = client.post("/api/v1/extractors/cancel/non-existent-id")

            assert response.status_code == 404


class TestGetExtractorHealth:
    """Tests for GET /api/v1/extractors/health endpoint."""

    def test_get_extractor_health(self, client):
        """Test getting extractor health status."""
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

        with patch("api.db.get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = health_data
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            response = client.get("/api/v1/extractors/health")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
