"""Integration tests for Health API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for GET /healthz endpoint."""

    def test_health_ok(self, client):
        """Test health check when database is healthy."""
        response = client.get("/healthz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["api"] == "finops-orchestrator"
        assert data["database"] == "ok"

    def test_health_degraded_database_error(self, client):
        """Test health check when database has an error."""
        with patch("api.db.get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database connection failed")
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            response = client.get("/healthz")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "degraded"
            assert "database" in data
            assert "error" in data["database"].lower()


class TestMetricsEndpoint:
    """Tests for GET /metrics endpoint."""

    def test_metrics_available(self, client):
        """Test metrics endpoint is available."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]


class TestDBStatsEndpoint:
    """Tests for GET /api/v1/db/stats endpoint."""

    def test_db_stats(self, client):
        """Test database stats endpoint."""
        mock_pool = MagicMock()
        mock_pool.min_size = 2
        mock_pool.max_size = 10
        mock_pool.__len__ = lambda self: 5

        with patch("api.db._sync_pool", mock_pool):
            with patch(
                "api.db.get_pool_stats",
                return_value={"async": None, "sync": {"min_size": 2, "max_size": 10, "size": 5}},
            ):
                response = client.get("/api/v1/db/stats")

                assert response.status_code == 200
                data = response.json()
                assert "sync" in data
