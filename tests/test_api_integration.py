"""Integration tests for FastAPI endpoints — real DB connectivity and happy path scenarios."""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

backend_path = Path(__file__).parent.parent / "backend" / "app"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

os.environ["TESTING"] = "1"
os.environ["PG_DSN"] = "postgresql://test:***@localhost/testdb"
os.environ["POOL_MIN_CONNS"] = "1"
os.environ["POOL_MAX_CONNS"] = "5"
os.environ["ENCRYPTION_KEY"] = secrets.token_urlsafe(32)
os.environ["JWT_SECRET"] = secrets.token_urlsafe(32)
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRATION_MINUTES"] = "60"

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.api.auth import create_access_token  # noqa: E402


@pytest.fixture
def client():
    """Create test client with TESTING env bypassing DB middleware."""
    from backend.app.api import main as main_module

    with TestClient(main_module.app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def auth_client(client):
    """Create test client that auto-injects auth headers."""
    token = create_access_token(data={"sub": "testuser"})
    auth_headers = {"Authorization": f"Bearer {token}"}

    original_request = client.request

    def patched_request(method, url, **kwargs):
        headers = kwargs.get("headers") or {}
        headers.update(auth_headers)
        kwargs["headers"] = headers
        return original_request(method, url, **kwargs)

    client.request = lambda m, u, **kw: patched_request(m, u, **kw)
    yield client
    client.request = original_request


# ─────────────────────────────────────────────────────────────────────────────
# Healthz Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHealthz:
    """Tests for GET /healthz endpoint."""

    @pytest.mark.integration
    def test_healthz_returns_200_ok(self, client):
        """Healthz endpoint returns 200 with ok status."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["api"] == "finops-orchestrator"

    @pytest.mark.integration
    def test_healthz_includes_database_status(self, client):
        """Healthz includes database connection status."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert "database" in data


# ─────────────────────────────────────────────────────────────────────────────
# Auth Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthToken:
    """Tests for POST /auth/token endpoint."""

    @pytest.mark.integration
    def test_login_success_with_valid_credentials(self, client):
        """Valid credentials return JWT token."""
        with patch("backend.app.api.routes.auth.query_one") as mock_query:
            mock_query.return_value = {
                "id": 1,
                "username": "admin",
                "hashed_password": "$2b$12$UYoRP.qb0Lx5AlFzlY0dnOdq19.JSYRR3z2Mw2WspmnuCOMUWJZXG",
                "is_active": True,
                "is_admin": True,
            }

            response = client.post(
                "/api/v1/auth/token",
                json={"username": "admin", "password": "admin"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "token" in data
            assert len(data["token"]) > 20

    @pytest.mark.integration
    def test_login_fails_with_invalid_credentials(self, client):
        """Invalid credentials return 401."""
        with patch("backend.app.api.routes.auth.query_one") as mock_query:
            mock_query.return_value = {
                "id": 1,
                "username": "admin",
                "hashed_password": "$2b$12$UYoRP.qb0Lx5AlFzlY0dnOdq19.JSYRR3z2Mw2WspmnuCOMUWJZXG",
                "is_active": True,
                "is_admin": True,
            }

            response = client.post(
                "/api/v1/auth/token",
                json={"username": "admin", "password": "wrongpassword"},
            )

            assert response.status_code == 401
            data = response.json()
            assert data["detail"] == "Invalid credentials"

    @pytest.mark.integration
    def test_login_fails_with_nonexistent_user(self, client):
        """Nonexistent user returns 401."""
        with patch("backend.app.api.routes.auth.query_one") as mock_query:
            mock_query.return_value = None

            response = client.post(
                "/api/v1/auth/token",
                json={"username": "nonexistent", "password": "anypassword"},
            )

            assert response.status_code == 401
            data = response.json()
            assert data["detail"] == "Invalid credentials"

    @pytest.mark.integration
    def test_login_fails_with_disabled_account(self, client):
        """Disabled account returns 403."""
        with patch("backend.app.api.routes.auth.query_one") as mock_query:
            mock_query.return_value = {
                "id": 1,
                "username": "admin",
                "hashed_password": "$2b$12$UYoRP.qb0Lx5AlFzlY0dnOdq19.JSYRR3z2Mw2WspmnuCOMUWJZXG",
                "is_active": False,
                "is_admin": True,
            }

            response = client.post(
                "/api/v1/auth/token",
                json={"username": "admin", "password": "admin"},
            )

            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Account is disabled"


# ─────────────────────────────────────────────────────────────────────────────
# Config CRUD Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigCrud:
    """Tests for Config CRUD endpoints."""

    @pytest.mark.integration
    def test_create_config_success(self, auth_client):
        """Creating a config succeeds and returns config with ID."""
        with patch("backend.app.api.routes.config.insert_and_return") as mock_insert:
            mock_insert.return_value = "test-config-id"

            response = auth_client.post(
                "/api/v1/config",
                json={
                    "provider": "gcp",
                    "name": "Test GCP Project",
                    "credential_type": "service_principal",
                    "config": {"project_id": "test-project"},
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["id"] is not None
            assert len(data["id"]) > 0
            assert data["provider"] == "gcp"
            assert data["name"] == "Test GCP Project"
            assert "created_at" in data
            assert "updated_at" in data

    @pytest.mark.integration
    def test_list_configs_success(self, auth_client):
        """List configs returns array of configs."""
        with patch("backend.app.api.routes.config.query_all") as mock_query:
            mock_query.return_value = [
                {
                    "id": "config-1",
                    "provider": "gcp",
                    "name": "GCP Config",
                    "credential_type": "service_principal",
                    "config": '{"project_id": "test"}',
                    "created_at": "2025-04-22T12:00:00+00:00",
                    "updated_at": "2025-04-22T12:00:00+00:00",
                },
            ]

            with patch("utils.encryption.decrypt_config") as mock_decrypt:
                mock_decrypt.return_value = {"project_id": "test"}

                response = auth_client.get("/api/v1/config")

                assert response.status_code == 200
                data = response.json()
                assert isinstance(data, list)
                assert len(data) == 1
                assert data[0]["id"] == "config-1"
                assert data[0]["provider"] == "gcp"

    @pytest.mark.integration
    def test_get_config_by_id_success(self, auth_client):
        """Get config by ID returns the config."""
        with patch("backend.app.api.routes.config.query_one") as mock_query:
            mock_query.return_value = {
                "id": "config-1",
                "provider": "gcp",
                "name": "GCP Config",
                "credential_type": "service_principal",
                "config": '{"project_id": "test"}',
                "created_at": "2025-04-22T12:00:00+00:00",
                "updated_at": "2025-04-22T12:00:00+00:00",
            }

            with patch("utils.encryption.decrypt_config") as mock_decrypt:
                mock_decrypt.return_value = {"project_id": "test"}

                response = auth_client.get("/api/v1/config/config-1")

                assert response.status_code == 200
                data = response.json()
                assert data["id"] == "config-1"
                assert data["provider"] == "gcp"

    @pytest.mark.integration
    def test_get_config_not_found(self, auth_client):
        """Get nonexistent config returns 404."""
        with patch("backend.app.api.routes.config.query_one") as mock_query:
            mock_query.return_value = None

            response = auth_client.get("/api/v1/config/nonexistent-id")

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()

    @pytest.mark.integration
    def test_update_config_success(self, auth_client):
        """Updating a config succeeds and returns updated config."""
        with patch("backend.app.api.routes.config.query_one") as mock_query:
            mock_query.return_value = {
                "id": "config-1",
                "provider": "gcp",
                "name": "Updated GCP Config",
                "credential_type": "service_principal",
                "config": '{"project_id": "test"}',
                "created_at": "2025-04-22T12:00:00+00:00",
                "updated_at": "2025-04-22T12:01:00+00:00",
            }

            with patch("utils.encryption.encrypt_config") as mock_encrypt:
                mock_encrypt.return_value = '{"project_id": "test"}'

                with patch("utils.encryption.decrypt_config") as mock_decrypt:
                    mock_decrypt.return_value = {"project_id": "test"}

                    response = auth_client.put(
                        "/api/v1/config/config-1",
                        json={"name": "Updated GCP Config"},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["id"] == "config-1"
                    assert data["name"] == "Updated GCP Config"

    @pytest.mark.integration
    def test_delete_config_success(self, auth_client):
        """Deleting a config succeeds and returns 204."""
        with patch("backend.app.api.routes.config.execute") as mock_execute:
            response = auth_client.delete("/api/v1/config/config-1")

            assert response.status_code == 204
            mock_execute.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Config Test Endpoint Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigTestEndpoint:
    """Tests for POST /config/{id}/test endpoint."""

    @pytest.mark.integration
    def test_config_test_gcp_success(self, auth_client):
        """Testing GCP config returns ok=True."""
        with patch("backend.app.api.routes.config.query_one") as mock_query:
            mock_query.return_value = {
                "provider": "gcp",
                "credential_type": "service_principal",
                "config": '{"project_id": "test-project"}',
            }

            with patch("utils.encryption.decrypt_config") as mock_decrypt:
                mock_decrypt.return_value = {"project_id": "test-project"}

                with patch("google.auth.default") as mock_google_auth:
                    mock_creds = MagicMock()
                    mock_creds.valid = True
                    mock_google_auth.return_value = (mock_creds, "test-project")

                    response = auth_client.post("/api/v1/config/config-1/test")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["ok"] is True
                    assert data["provider"] == "gcp"

    @pytest.mark.integration
    def test_config_test_azure_success(self, auth_client):
        """Testing Azure config returns ok=True."""
        with patch("backend.app.api.routes.config.query_one") as mock_query:
            mock_query.return_value = {
                "provider": "azure",
                "credential_type": "service_account",
                "config": '{"tenant_id": "test", "client_id": "test", "client_secret": "test"}',
            }

            with patch("utils.encryption.decrypt_config") as mock_decrypt:
                mock_decrypt.return_value = {
                    "tenant_id": "test",
                    "client_id": "test",
                    "client_secret": "test",
                }

                with patch("azure.identity.ClientSecretCredential") as mock_cred:
                    mock_cred_inst = MagicMock()
                    mock_token = MagicMock()
                    mock_token.expires_on = 1234567890
                    mock_cred_inst.get_token.return_value = mock_token
                    mock_cred.return_value = mock_cred_inst

                    response = auth_client.post("/api/v1/config/config-1/test")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["ok"] is True
                    assert data["provider"] == "azure"

    @pytest.mark.integration
    def test_config_test_not_found(self, auth_client):
        """Testing nonexistent config returns 404."""
        with patch("backend.app.api.routes.config.query_one") as mock_query:
            mock_query.return_value = None

            response = auth_client.post("/api/v1/config/nonexistent/test")

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# Extractor Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractorRun:
    """Tests for extractor run endpoints."""

    @pytest.mark.integration
    def test_run_extractor_success(self, auth_client):
        """Running an extractor succeeds and returns run_id."""
        with patch("backend.app.api.routes.extractors_registry.start_extractor") as mock_start:
            mock_start.return_value = "run-123"

            response = auth_client.post(
                "/api/v1/extractors/run",
                json={"config_id": "config-1", "provider": "gcp"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["run_id"] == "run-123"
            assert data["status"] == "started"

    @pytest.mark.integration
    def test_run_extractor_requires_config_id(self, auth_client):
        """Running an extractor without config_id returns 400."""
        response = auth_client.post(
            "/api/v1/extractors/run",
            json={"provider": "gcp"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "config_id is required" in data["detail"]

    @pytest.mark.integration
    def test_list_extractors_status_success(self, auth_client):
        """Listing extractor status succeeds and returns runs."""
        with patch("backend.app.api.routes.extractors_registry.list_runs") as mock_list:
            mock_list.return_value = [
                {
                    "id": "run-1",
                    "provider": "gcp",
                    "extractor_type": "gcp",
                    "status": "completed",
                    "started_at": "2025-04-22T12:00:00+00:00",
                    "finished_at": "2025-04-22T12:05:00+00:00",
                    "records_extracted": 100,
                },
            ]

            response = auth_client.get("/api/v1/extractors/runs")

            assert response.status_code == 200
            data = response.json()
            assert "runs" in data
            assert "count" in data
            assert data["count"] == 1
            assert len(data["runs"]) == 1

    @pytest.mark.integration
    def test_list_extractors_status_empty(self, auth_client):
        """Listing extractor status when no runs returns empty list."""
        with patch("backend.app.api.routes.extractors_registry.list_runs") as mock_list:
            mock_list.return_value = []

            response = auth_client.get("/api/v1/extractors/runs")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 0
            assert data["runs"] == []

    @pytest.mark.integration
    def test_get_extractor_run_success(self, auth_client):
        """Getting extractor run by ID succeeds."""
        with patch("backend.app.api.routes.extractors_registry.get_run_status") as mock_get:
            mock_get.return_value = {
                "id": "run-1",
                "provider": "gcp",
                "extractor_type": "gcp",
                "status": "completed",
                "started_at": "2025-04-22T12:00:00+00:00",
                "finished_at": "2025-04-22T12:05:00+00:00",
                "records_extracted": 100,
            }

            response = auth_client.get("/api/v1/extractors/runs/run-1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "run-1"
            assert data["status"] == "completed"

    @pytest.mark.integration
    def test_get_extractor_run_not_found(self, auth_client):
        """Getting nonexistent run returns 404."""
        with patch("backend.app.api.routes.extractors_registry.get_run_status") as mock_get:
            mock_get.return_value = None

            response = auth_client.get("/api/v1/extractors/runs/nonexistent")

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()

    @pytest.mark.integration
    def test_cancel_extractor_run_success(self, auth_client):
        """Canceling an extractor run succeeds."""
        with patch("backend.app.api.routes.extractors_registry.cancel_run") as mock_cancel:
            mock_cancel.return_value = True

            response = auth_client.post("/api/v1/extractors/runs/run-1/cancel")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "cancelled"

    @pytest.mark.integration
    def test_cancel_extractor_run_not_found(self, auth_client):
        """Canceling nonexistent run returns 404."""
        with patch("backend.app.api.routes.extractors_registry.cancel_run") as mock_cancel:
            mock_cancel.return_value = False

            response = auth_client.post("/api/v1/extractors/runs/nonexistent/cancel")

            assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Auth-Required Endpoints Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthRequiredEndpoints:
    """Tests for endpoints that require authentication."""

    @pytest.mark.integration
    def test_config_list_requires_auth(self, client):
        """Listing configs without auth returns 401."""
        response = client.get("/api/v1/config")

        assert response.status_code == 401

    @pytest.mark.integration
    def test_extractor_run_requires_auth(self, client):
        """Running extractor without auth returns 401."""
        response = client.post(
            "/api/v1/extractors/run",
            json={"config_id": "config-1"},
        )

        assert response.status_code == 401

    @pytest.mark.integration
    def test_healthz_does_not_require_auth(self, client):
        """Healthz endpoint does not require auth."""
        response = client.get("/healthz")

        assert response.status_code == 200

    @pytest.mark.integration
    def test_auth_token_does_not_require_auth(self, client):
        """Token endpoint does not require auth."""
        with patch("backend.app.api.routes.auth.query_one") as mock_query:
            mock_query.return_value = {
                "id": 1,
                "username": "admin",
                "hashed_password": "$2b$12$UYoRP.qb0Lx5AlFzlY0dnOdq19.JSYRR3z2Mw2WspmnuCOMUWJZXG",
                "is_active": True,
                "is_admin": True,
            }

            response = client.post(
                "/api/v1/auth/token",
                json={"username": "admin", "password": "admin"},
            )

            assert response.status_code == 200
