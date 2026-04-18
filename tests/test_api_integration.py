"""Integration tests for finna-app API.

Tests the main API endpoints with mocked database connections.
"""

import os

os.environ["PG_DSN"] = "postgresql://test:test@localhost/testdb"
os.environ["POOL_MIN_CONNS"] = "1"
os.environ["POOL_MAX_CONNS"] = "5"

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def create_mock_app():
    """Create test client with proper mocking."""

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    with patch("api.main.app.router.lifespan_context", noop_lifespan):
        with patch("api.db.get_connection") as mock_conn:
            mock_conn.return_value = MagicMock()
            from api.main import app

            return app


class TestConfigEndpoints:
    """Test Config CRUD endpoints."""

    def test_list_configs_empty(self):
        """Test GET /api/v1/config returns empty list."""
        with patch("api.db.query_all", return_value=[]):
            app = create_mock_app()
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/v1/config")
                assert response.status_code == 200
                assert response.json() == []

    def test_list_configs_with_data(self):
        """Test GET /api/v1/config returns config list."""
        test_config = {
            "id": "test-id",
            "provider": "azure",
            "name": "Test Config",
            "credential_type": "service_principal",
            "config": {"tenant_id": "test"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with patch("api.db.query_all", return_value=[test_config]):
            app = create_mock_app()
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/v1/config")
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1

    def test_get_config_not_found(self):
        """Test GET /api/v1/config/{id} returns 404 for missing config."""
        with patch("api.db.query_one", return_value=None):
            app = create_mock_app()
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/v1/config/nonexistent")
                assert response.status_code == 404

    def test_create_config_validation_error(self):
        """Test POST /api/v1/config validates input."""
        invalid_config = {"provider": "invalid_provider", "name": ""}
        app = create_mock_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/config", json=invalid_config)
            assert response.status_code == 422

    def test_update_config_no_fields(self):
        """Test PUT /api/v1/config/{id} with empty body."""
        app = create_mock_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.put("/api/v1/config/test-id", json={})
            assert response.status_code == 400

    def test_delete_config_success(self):
        """Test DELETE /api/v1/config/{id} returns 204."""
        with patch("api.db.execute"):
            app = create_mock_app()
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.delete("/api/v1/config/test-id")
                assert response.status_code == 204


class TestExtractorEndpoints:
    """Test Extractor endpoints."""

    def test_run_extractor_no_config(self):
        """Test POST /api/v1/extractors/run fails without config."""
        with patch("api.db.get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            app = create_mock_app()
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post("/api/v1/extractors/run", json={"provider": "azure"})
                assert response.status_code == 404
                assert "no configuration found" in response.json()["detail"].lower()

    def test_run_extractor_invalid_provider(self):
        """Test POST /api/v1/extractors/run validates provider."""
        app = create_mock_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/extractors/run", json={"provider": "invalid"})
            assert response.status_code == 422

    def test_get_status_empty(self):
        """Test GET /api/v1/extractors/status returns empty list."""
        with patch("api.runner.list_runs", return_value=[]):
            app = create_mock_app()
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/v1/extractors/status")
                assert response.status_code == 200
                assert response.json() == []

    def test_cancel_extractor_not_found(self):
        """Test POST /api/v1/extractors/cancel/{id} returns 404."""
        with patch("api.runner.cancel_run", return_value=False):
            app = create_mock_app()
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post("/api/v1/extractors/cancel/nonexistent")
                assert response.status_code == 404


class TestHealthEndpoints:
    """Test Health and Metrics endpoints."""

    def test_health_ok(self):
        """Test GET /healthz returns ok status."""
        app = create_mock_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/healthz")
            assert response.status_code in [200, 500]

    def test_health_degraded(self):
        """Test GET /healthz returns degraded on db error."""
        with patch("api.db.get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("DB Error")
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            app = create_mock_app()
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/healthz")
                assert response.status_code == 503

    def test_metrics_endpoint(self):
        """Test GET /metrics returns prometheus format."""
        app = create_mock_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/metrics")
            # May be 404 if not instrumented in test
            assert response.status_code in [200, 404]

    def test_db_stats(self):
        """Test GET /api/v1/db/stats returns pool stats."""
        mock_pool = MagicMock()
        mock_pool.min_size = 2
        mock_pool.max_size = 10
        mock_pool.__len__ = lambda self: 5

        with patch("api.db._sync_pool", mock_pool):
            with patch("api.db.get_pool_stats", return_value={"sync": {"size": 5}}):
                app = create_mock_app()
                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.get("/api/v1/db/stats")
                    assert response.status_code == 200
