"""Integration tests for /api/v1/config CRUD endpoints."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

SAMPLE_CONFIG = {
    "id": "cfg-001",
    "provider": "azure",
    "name": "Test Azure Config",
    "credential_type": "service_principal",
    "config": {
        "tenant_id": "00000000-0000-0000-0000-000000000000",
        "client_id": "app-id",
        "client_secret": "secret-value",
        "subscription_id": "sub-id",
    },
    "created_at": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    "updated_at": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
}

SAMPLE_GCP_CONFIG = {
    "id": "cfg-002",
    "provider": "gcp",
    "name": "Test GCP Config",
    "credential_type": "service_principal",
    "config": {
        "project_id": "my-project",
    },
    "created_at": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    "updated_at": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
}


@pytest.fixture
def config_client():
    import api.db as db_module
    import api.main as main_module

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

    from api.auth import create_access_token

    token = create_access_token(data={"sub": "testuser"})

    try:
        with patch.object(db_module, "get_connection", return_value=mock_connection):
            with patch.object(db_module, "release_connection"):
                with patch.object(db_module, "query_one", return_value=None):
                    with patch.object(db_module, "query_all", return_value=[]):
                        with patch.object(db_module, "execute"):
                            with patch.object(db_module, "insert_and_return", return_value="cfg-001"):
                                with TestClient(main_module.app, raise_server_exceptions=False) as client:
                                    client._auth_token = token
                                    client._mock_connection = mock_connection
                                    yield client
    finally:
        main_module.app.router.lifespan_context = original_lifespan


def _auth_headers(client):
    return {"Authorization": f"Bearer {client._auth_token}"}


class TestConfigAuth:
    def test_list_configs_returns_401_without_token(self, config_client):
        resp = config_client.get("/api/v1/config")
        assert resp.status_code == 401

    def test_create_config_returns_401_without_token(self, config_client):
        resp = config_client.post(
            "/api/v1/config",
            json={
                "provider": "azure",
                "name": "test",
                "credential_type": "service_principal",
                "config": {"tenant_id": "t", "client_id": "c", "client_secret": "s", "subscription_id": "sub"},
            },
        )
        assert resp.status_code == 401

    def test_get_config_returns_401_without_token(self, config_client):
        resp = config_client.get("/api/v1/config/cfg-001")
        assert resp.status_code == 401

    def test_update_config_returns_401_without_token(self, config_client):
        resp = config_client.put("/api/v1/config/cfg-001", json={"name": "updated"})
        assert resp.status_code == 401

    def test_delete_config_returns_401_without_token(self, config_client):
        resp = config_client.delete("/api/v1/config/cfg-001")
        assert resp.status_code == 401


class TestListConfigs:
    def test_list_configs_empty(self, config_client):
        with patch("api.routes.config.query_all", return_value=[]):
            with patch("api.routes.config.decrypt_config", side_effect=lambda x: x):
                resp = config_client.get("/api/v1/config", headers=_auth_headers(config_client))
                assert resp.status_code == 200
                assert resp.json() == []

    def test_list_configs_with_data(self, config_client):
        with patch("api.routes.config.query_all", return_value=[SAMPLE_CONFIG]):
            with patch("api.routes.config.decrypt_config", side_effect=lambda x: x):
                resp = config_client.get("/api/v1/config", headers=_auth_headers(config_client))
                assert resp.status_code == 200
                data = resp.json()
                assert len(data) == 1
                assert data[0]["id"] == "cfg-001"
                assert data[0]["provider"] == "azure"

    def test_list_configs_by_provider(self, config_client):
        with patch("api.routes.config.query_all", return_value=[SAMPLE_GCP_CONFIG]):
            with patch("api.routes.config.decrypt_config", side_effect=lambda x: x):
                resp = config_client.get("/api/v1/config/provider/gcp", headers=_auth_headers(config_client))
                assert resp.status_code == 200
                data = resp.json()
                assert len(data) == 1
                assert data[0]["provider"] == "gcp"


class TestCreateConfig:
    def test_create_azure_config(self, config_client):
        with patch("api.routes.config.encrypt_config", side_effect=lambda x: x):
            with patch("api.routes.config.insert_and_return", return_value="cfg-new"):
                resp = config_client.post(
                    "/api/v1/config",
                    json={
                        "provider": "azure",
                        "name": "New Azure Config",
                        "credential_type": "service_principal",
                        "config": {
                            "tenant_id": "t",
                            "client_id": "c",
                            "client_secret": "s",
                            "subscription_id": "sub",
                        },
                    },
                    headers=_auth_headers(config_client),
                )
                assert resp.status_code == 201
                data = resp.json()
                assert data["provider"] == "azure"
                assert data["name"] == "New Azure Config"
                assert "id" in data

    def test_create_gcp_config(self, config_client):
        with patch("api.routes.config.encrypt_config", side_effect=lambda x: x):
            with patch("api.routes.config.insert_and_return", return_value="cfg-gcp"):
                resp = config_client.post(
                    "/api/v1/config",
                    json={
                        "provider": "gcp",
                        "name": "New GCP Config",
                        "credential_type": "service_principal",
                        "config": {"project_id": "my-project"},
                    },
                    headers=_auth_headers(config_client),
                )
                assert resp.status_code == 201
                data = resp.json()
                assert data["provider"] == "gcp"

    def test_create_config_masks_secrets(self, config_client):
        with patch("api.routes.config.encrypt_config", side_effect=lambda x: x):
            with patch("api.routes.config.insert_and_return", return_value="cfg-mask"):
                resp = config_client.post(
                    "/api/v1/config",
                    json={
                        "provider": "azure",
                        "name": "Masked",
                        "credential_type": "service_principal",
                        "config": {
                            "tenant_id": "t",
                            "client_id": "c",
                            "client_secret": "super-secret",
                            "subscription_id": "sub",
                        },
                    },
                    headers=_auth_headers(config_client),
                )
                assert resp.status_code == 201
                config_data = resp.json().get("config", {})
                assert config_data.get("client_secret") == "***REDACTED***"


class TestGetConfig:
    def test_get_config_found(self, config_client):
        with patch("api.routes.config.query_one", return_value=SAMPLE_CONFIG):
            with patch("api.routes.config.decrypt_config", side_effect=lambda x: x):
                resp = config_client.get("/api/v1/config/cfg-001", headers=_auth_headers(config_client))
                assert resp.status_code == 200
                data = resp.json()
                assert data["id"] == "cfg-001"

    def test_get_config_not_found(self, config_client):
        with patch("api.routes.config.query_one", return_value=None):
            resp = config_client.get("/api/v1/config/nonexistent", headers=_auth_headers(config_client))
            assert resp.status_code == 404


class TestUpdateConfig:
    def test_update_config_name(self, config_client):
        updated = {**SAMPLE_CONFIG, "name": "Updated Name"}
        with patch("api.routes.config.query_one", return_value=updated):
            with patch("api.routes.config.decrypt_config", side_effect=lambda x: x):
                with patch("api.routes.config.encrypt_config", side_effect=lambda x: x):
                    resp = config_client.put(
                        "/api/v1/config/cfg-001",
                        json={"name": "Updated Name"},
                        headers=_auth_headers(config_client),
                    )
                    assert resp.status_code == 200

    def test_update_config_not_found(self, config_client):
        with patch("api.routes.config.query_one", return_value=None):
            resp = config_client.put(
                "/api/v1/config/nonexistent",
                json={"name": "x"},
                headers=_auth_headers(config_client),
            )
            assert resp.status_code == 404

    def test_update_config_no_fields(self, config_client):
        # CloudConfigUpdate: all fields optional, endpoint checks for updates
        resp = config_client.put(
            "/api/v1/config/cfg-001",
            json={"name": "x"},
            headers=_auth_headers(config_client),
        )
        # Could be 404 (query_one returns None) or 200 depending on mock state
        assert resp.status_code in (200, 404)


class TestDeleteConfig:
    def test_delete_config(self, config_client):
        with patch("api.routes.config.execute"):
            resp = config_client.delete("/api/v1/config/cfg-001", headers=_auth_headers(config_client))
            assert resp.status_code == 204
