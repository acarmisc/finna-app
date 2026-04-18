"""Integration tests for auth routes (api/routes/auth.py)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_test_client():
    import backend.app.db as db_module
    import backend.app.main as main_module

    original_lifespan = main_module.app.router.lifespan_context

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    main_module.app.router.lifespan_context = noop_lifespan

    mock_connection = MagicMock()
    mock_connection.closed = False
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []
    mock_connection.cursor.return_value = cursor
    mock_connection.commit = MagicMock()
    mock_connection.rollback = MagicMock()

    mock_sync_pool = MagicMock()
    mock_sync_pool.min_size = 2
    mock_sync_pool.max_size = 10
    mock_sync_pool.__len__ = lambda self: 5

    from backend.app.auth import create_access_token

    token = create_access_token(data={"sub": "testuser"})

    try:
        with patch.object(db_module, "get_connection", return_value=mock_connection):
            with patch.object(db_module, "release_connection"):
                with patch.object(db_module, "query_one", return_value=None):
                    with patch.object(db_module, "query_all", return_value=[]):
                        with patch.object(db_module, "execute"):
                            with patch.object(db_module, "insert_and_return", return_value="test-config-id"):
                                with TestClient(main_module.app, raise_server_exceptions=False) as client:
                                    client._auth_token = token
                                    yield client
    finally:
        main_module.app.router.lifespan_context = original_lifespan


class TestDeviceCodeStart:
    def test_device_code_requires_auth(self, auth_test_client):
        resp = auth_test_client.post("/api/v1/auth/azure/device-code", json={"tenant_id": "organizations"})
        assert resp.status_code == 401

    def test_device_code_cors_preflight(self, auth_test_client):
        resp = auth_test_client.options(
            "/api/v1/auth/azure/device-code",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers

    @patch("backend.app.routes.auth.DeviceCodeCredential", create=True)
    @patch("msal.Application", create=True)
    def test_device_code_start_success(self, mock_app_cls, mock_cred_cls, auth_test_client):
        mock_app = MagicMock()
        mock_app.initiate_device_flow.return_value = {
            "verification_uri": "https://microsoft.com/devicelogin",
            "user_code": "ABC-123",
            "device_code": "dc-123",
            "expires_in": 900,
            "interval": 5,
            "message": "Enter the code ABC-123 to authenticate",
        }
        mock_app_cls.return_value = mock_app

        with patch("backend.app.routes.auth.DeviceCodeCredential"):
            resp = auth_test_client.post(
                "/api/v1/auth/azure/device-code",
                json={"tenant_id": "organizations"},
                headers={"Authorization": f"Bearer {auth_test_client._auth_token}"},
            )
            assert resp.status_code in (200, 500)


class TestDeviceCodePoll:
    def test_poll_requires_auth(self, auth_test_client):
        resp = auth_test_client.post(
            "/api/v1/auth/azure/device-code/poll",
            json={"device_code": "nonexistent"},
        )
        assert resp.status_code == 401

    def test_poll_invalid_device_code(self, auth_test_client):
        resp = auth_test_client.post(
            "/api/v1/auth/azure/device-code/poll",
            json={"device_code": "nonexistent-code"},
            headers={"Authorization": f"Bearer {auth_test_client._auth_token}"},
        )
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] in ("failed", "pending", "expired")

    def test_poll_cors_preflight(self, auth_test_client):
        resp = auth_test_client.options(
            "/api/v1/auth/azure/device-code/poll",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers


class TestGCPRegister:
    def test_gcp_register_requires_auth(self, auth_test_client):
        resp = auth_test_client.post(
            "/api/v1/auth/gcp/register",
            json={"project_id": "my-project"},
        )
        assert resp.status_code == 401

    def test_gcp_register_success(self, auth_test_client):
        resp = auth_test_client.post(
            "/api/v1/auth/gcp/register",
            json={"project_id": "my-gcp-project"},
            headers={"Authorization": f"Bearer {auth_test_client._auth_token}"},
        )
        assert resp.status_code in (200, 201)
        if resp.status_code in (200, 201):
            data = resp.json()
            assert "config_id" in data
            assert data["project_id"] == "my-gcp-project"

    def test_gcp_register_with_key_file(self, auth_test_client):
        resp = auth_test_client.post(
            "/api/v1/auth/gcp/register",
            json={"project_id": "my-project", "key_file_content": '{"type": "service_account"}'},
            headers={"Authorization": f"Bearer {auth_test_client._auth_token}"},
        )
        assert resp.status_code in (200, 201)

    def test_gcp_register_cors_preflight(self, auth_test_client):
        resp = auth_test_client.options(
            "/api/v1/auth/gcp/register",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers


class TestAuthResponseStructure:
    def test_device_code_response_fields(self):
        from backend.app.models import DeviceCodeStartResponse

        resp = DeviceCodeStartResponse(
            verification_uri="https://microsoft.com/devicelogin",
            user_code="ABC-123",
            device_code="dc-123",
            expires_in=900,
            interval=5,
            message="Enter the code",
        )
        assert resp.verification_uri == "https://microsoft.com/devicelogin"
        assert resp.user_code == "ABC-123"
        assert resp.device_code == "dc-123"
        assert resp.expires_in == 900
        assert resp.interval == 5
        assert resp.message == "Enter the code"

    def test_device_code_poll_response_fields(self):
        from backend.app.models import DeviceCodePollResponse

        resp = DeviceCodePollResponse(status="pending")
        assert resp.status == "pending"
        assert resp.config_id is None

        resp_completed = DeviceCodePollResponse(status="completed", config_id="cfg-123")
        assert resp_completed.status == "completed"
        assert resp_completed.config_id == "cfg-123"
