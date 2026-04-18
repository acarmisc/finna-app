"""Integration tests for Config API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_db_with_config(mock_connection):
    """Mock database connection with config data."""
    cursor = mock_connection.cursor.return_value.__enter__.return_value

    test_config = {
        "id": "test-config-id",
        "provider": "azure",
        "name": "Test Config",
        "credential_type": "service_principal",
        "config": {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "subscription_id": "test-sub-id",
            "resource_groups": [],
            "scope": "resourcegroup",
        },
        "created_at": datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
    }

    def fetchone_side_effect(sql, params=None):
        if "WHERE id = %s" in sql and params and params[0] == "test-config-id":
            return test_config
        if "WHERE id = %s" in sql and params and params[0] == "non-existent-id":
            return None
        if "WHERE id = %s" in sql and params and params[0] == "update-test-id":
            return {
                "id": "update-test-id",
                "provider": "azure",
                "name": "Updated Config",
                "credential_type": "service_principal",
                "config": test_config["config"],
                "created_at": test_config["created_at"],
                "updated_at": datetime.now(timezone.utc),
            }
        return None

    def fetchall_side_effect(sql, params=None):
        if "ORDER BY provider, name" in sql:
            return [test_config]
        if "WHERE provider = %s" in sql and params and params[0] == "azure":
            return [test_config]
        return []

    cursor.fetchone.side_effect = fetchone_side_effect
    cursor.fetchall.side_effect = fetchall_side_effect

    return mock_connection


class TestListConfigs:
    """Tests for GET /api/v1/config endpoint."""

    def test_list_configs_empty(self, client):
        """Test listing configs when none exist."""
        with patch("api.db.query_all", return_value=[]):
            response = client.get("/api/v1/config")

            assert response.status_code == 200
            assert response.json() == []

    def test_list_configs_with_data(self, client):
        """Test listing configs with data."""
        test_config = {
            "id": "test-id",
            "provider": "azure",
            "name": "Test Config",
            "credential_type": "service_principal",
            "config": {"tenant_id": "test-tenant"},
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
        }

        with patch("api.db.query_all", return_value=[test_config]):
            response = client.get("/api/v1/config")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "test-id"
            assert data[0]["provider"] == "azure"


class TestCreateConfig:
    """Tests for POST /api/v1/config endpoint."""

    def test_create_config_success(self, client):
        """Test creating a new config."""
        new_config = {
            "provider": "azure",
            "name": "New Config",
            "credential_type": "service_principal",
            "config": {
                "tenant_id": "new-tenant-id",
                "client_id": "new-client-id",
                "client_secret": "new-secret",
                "subscription_id": "new-sub-id",
            },
        }

        with patch("api.db.insert_and_return", return_value="new-id"):
            response = client.post("/api/v1/config", json=new_config)

            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert data["provider"] == "azure"
            assert data["name"] == "New Config"
            assert data["config"]["client_secret"] == "***REDACTED***"

    def test_create_config_validation_error(self, client):
        """Test creating config with invalid data."""
        invalid_config = {
            "provider": "invalid_provider",
            "name": "",
        }

        response = client.post("/api/v1/config", json=invalid_config)

        assert response.status_code == 422


class TestGetConfig:
    """Tests for GET /api/v1/config/{config_id} endpoint."""

    def test_get_config_success(self, client):
        """Test getting a config by ID."""
        test_config = {
            "id": "test-id",
            "provider": "gcp",
            "name": "GCP Config",
            "credential_type": "service_principal",
            "config": {"project_id": "test-project"},
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
        }

        with patch("api.db.query_one", return_value=test_config):
            response = client.get("/api/v1/config/test-id")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test-id"
            assert data["provider"] == "gcp"

    def test_get_config_not_found(self, client):
        """Test getting a non-existent config."""
        with patch("api.db.query_one", return_value=None):
            response = client.get("/api/v1/config/non-existent-id")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestUpdateConfig:
    """Tests for PUT /api/v1/config/{config_id} endpoint."""

    def test_update_config_success(self, client):
        """Test updating a config."""
        update_data = {"name": "Updated Name"}

        updated_config = {
            "id": "test-id",
            "provider": "azure",
            "name": "Updated Name",
            "credential_type": "service_principal",
            "config": {"tenant_id": "test-tenant"},
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-02T00:00:00+00:00",
        }

        with patch("api.db.query_one", return_value=updated_config):
            response = client.put("/api/v1/config/test-id", json=update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Name"

    def test_update_config_not_found(self, client):
        """Test updating a non-existent config."""
        update_data = {"name": "Updated Name"}

        with patch("api.db.query_one", return_value=None):
            response = client.put("/api/v1/config/non-existent-id", json=update_data)

            assert response.status_code == 404

    def test_update_config_no_fields(self, client):
        """Test updating with no fields."""
        response = client.put("/api/v1/config/test-id", json={})

        assert response.status_code == 400


class TestDeleteConfig:
    """Tests for DELETE /api/v1/config/{config_id} endpoint."""

    def test_delete_config_success(self, client):
        """Test deleting a config."""
        with patch("api.db.execute"):
            response = client.delete("/api/v1/config/test-id")

            assert response.status_code == 204


class TestListConfigsByProvider:
    """Tests for GET /api/v1/config/provider/{provider} endpoint."""

    def test_list_configs_by_provider(self, client):
        """Test listing configs for a specific provider."""
        configs = [
            {
                "id": "config-1",
                "provider": "azure",
                "name": "Azure Config 1",
                "credential_type": "service_principal",
                "config": {"tenant_id": "tenant-1"},
                "created_at": "2025-01-01T00:00:00+00:00",
                "updated_at": "2025-01-01T00:00:00+00:00",
            },
            {
                "id": "config-2",
                "provider": "azure",
                "name": "Azure Config 2",
                "credential_type": "service_principal",
                "config": {"tenant_id": "tenant-2"},
                "created_at": "2025-01-02T00:00:00+00:00",
                "updated_at": "2025-01-02T00:00:00+00:00",
            },
        ]

        with patch("api.db.query_all", return_value=configs):
            response = client.get("/api/v1/config/provider/azure")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert all(c["provider"] == "azure" for c in data)
