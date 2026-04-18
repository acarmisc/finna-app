"""Comprehensive tests for api/routes/config.py - Config CRUD endpoints."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

os.environ["ENCRYPTION_KEY"] = "KjZlG4Cp3mN9qR7sT1uV5wX2yZ6aB8cD"


class TestListConfigs:
    """Tests for GET /api/v1/config endpoint."""

    def test_list_configs_empty(self):
        """Test listing configs when none exist."""
        from api.routes.config import list_configs

        with patch("api.db.query_all", return_value=[]):
            results = list_configs()
            assert results == []

    def test_list_configs_with_data(self):
        """Test listing configs with data."""
        from api.routes.config import list_configs

        mock_config = {
            "id": "test-id",
            "provider": "azure",
            "name": "Test Config",
            "credential_type": "service_principal",
            "config": {"tenant_id": "test-tenant"},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        with patch("api.db.query_all", return_value=[mock_config]):
            with patch("api.routes.config.decrypt_config") as mock_decrypt:
                mock_decrypt.return_value = mock_config["config"]
                results = list_configs()
                assert len(results) == 1
                assert results[0]["id"] == "test-id"


class TestCreateConfig:
    """Tests for POST /api/v1/config endpoint."""

    def test_create_config_success(self):
        """Test creating a new config."""
        from api.models import Provider, CredentialType
        from api.routes.config import create_config
        from pydantic import BaseModel

        class MockData(BaseModel):
            provider: Provider
            name: str
            credential_type: CredentialType
            config: dict

        data = MockData(
            provider=Provider.AZURE,
            name="New Config",
            credential_type=CredentialType.SERVICE_PRINCIPAL,
            config={"tenant_id": "test-tenant"},
        )

        with patch("api.db.insert_and_return", return_value="new-id"):
            with patch("api.routes.config.encrypt_config") as mock_encrypt:
                mock_encrypt.return_value = {"tenant_id": "encrypted"}
                result = create_config(data)
                assert result is not None
                assert result["provider"] == "azure"
                assert "client_secret" not in result["config"]

    def test_create_config_masks_secrets(self):
        """Test that create_config masks secrets in response."""
        from api.models import Provider, CredentialType
        from api.routes.config import create_config
        from pydantic import BaseModel

        class MockData(BaseModel):
            provider: Provider
            name: str
            credential_type: CredentialType
            config: dict

        data = MockData(
            provider=Provider.AZURE,
            name="Config With Secret",
            credential_type=CredentialType.SERVICE_PRINCIPAL,
            config={
                "tenant_id": "test-tenant",
                "client_secret": "super-secret",
            },
        )

        with patch("api.db.insert_and_return", return_value="new-id"):
            with patch("api.routes.config.encrypt_config"):
                result = create_config(data)
                assert result["config"]["client_secret"] == "***REDACTED***"


class TestGetConfig:
    """Tests for GET /api/v1/config/{config_id} endpoint."""

    def test_get_config_success(self):
        """Test getting a config by ID."""
        from api.routes.config import get_config

        mock_config = {
            "id": "test-id",
            "provider": "azure",
            "name": "Test Config",
            "credential_type": "service_principal",
            "config": {"tenant_id": "test-tenant"},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        with patch("api.db.query_one", return_value=mock_config):
            with patch("api.routes.config.decrypt_config") as mock_decrypt:
                mock_decrypt.return_value = {"tenant_id": "test-tenant"}
                result = get_config("test-id")
                assert result is not None
                assert result["id"] == "test-id"

    def test_get_config_not_found(self):
        """Test getting a non-existent config."""
        from api.routes.config import get_config

        with patch("api.db.query_one", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                get_config("non-existent-id")
            assert exc_info.value.status_code == 404


class TestUpdateConfig:
    """Tests for PUT /api/v1/config/{config_id} endpoint."""

    def test_update_config_success(self):
        """Test updating a config."""
        from api.models import CredentialType
        from api.routes.config import update_config
        from pydantic import BaseModel

        class MockData(BaseModel):
            name: str = None
            credential_type: CredentialType = None
            config: dict = None

        data = MockData(name="Updated Name")
        config_id = "test-id"

        mock_updated = {
            "id": "test-id",
            "provider": "azure",
            "name": "Updated Name",
            "credential_type": "service_principal",
            "config": {"tenant_id": "test-tenant"},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        with patch("api.db.query_one", return_value=mock_updated):
            with patch("api.routes.config.decrypt_config") as mock_decrypt:
                mock_decrypt.return_value = {"tenant_id": "test-tenant"}
                result = update_config(config_id, data)
                assert result is not None
                assert result["name"] == "Updated Name"

    def test_update_config_not_found(self):
        """Test updating a non-existent config."""
        from api.routes.config import update_config
        from pydantic import BaseModel

        class MockData(BaseModel):
            name: str = None

        data = MockData(name="Updated")

        with patch("api.db.query_one", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                update_config("non-existent-id", data)
            assert exc_info.value.status_code == 404

    def test_update_config_no_fields(self):
        """Test updating with no fields."""
        from api.routes.config import update_config
        from pydantic import BaseModel

        class MockData(BaseModel):
            name: str = None
            credential_type = None
            config: dict = None

        data = MockData()

        with pytest.raises(HTTPException) as exc_info:
            update_config("test-id", data)
        assert exc_info.value.status_code == 400


class TestDeleteConfig:
    """Tests for DELETE /api/v1/config/{config_id} endpoint."""

    def test_delete_config_success(self):
        """Test deleting a config."""
        from api.routes.config import delete_config

        with patch("api.db.execute"):
            delete_config("test-id")


class TestListConfigsByProvider:
    """Tests for GET /api/v1/config/provider/{provider} endpoint."""

    def test_list_configs_by_provider(self):
        """Test listing configs for a specific provider."""
        from api.routes.config import list_configs_by_provider

        mock_configs = [
            {
                "id": "config-1",
                "provider": "azure",
                "name": "Azure Config 1",
                "credential_type": "service_principal",
                "config": {"tenant_id": "tenant-1"},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": "config-2",
                "provider": "azure",
                "name": "Azure Config 2",
                "credential_type": "service_principal",
                "config": {"tenant_id": "tenant-2"},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        ]

        with patch("api.db.query_all", return_value=mock_configs):
            with patch("api.routes.config.decrypt_config") as mock_decrypt:
                mock_decrypt.return_value = {"tenant_id": "tenant"}

                results = list_configs_by_provider("azure")
                assert len(results) == 2
                assert all(r["provider"] == "azure" for r in results)


class TestSecretMasking:
    """Tests for secret masking in config responses."""

    def test_mask_secrets_client_secret(self):
        """Test masking client_secret field."""
        from api.routes.config import _mask_secrets

        config = {
            "tenant_id": "test-tenant",
            "client_secret": "super-secret-password",
            "other_field": "public",
        }

        result = _mask_secrets(config)
        assert result["client_secret"] == "***REDACTED***"
        assert result["other_field"] == "public"

    def test_mask_secrets_key_file_content(self):
        """Test masking key_file_content field."""
        from api.routes.config import _mask_secrets

        config = {
            "project_id": "test-project",
            "key_file_content": "base64-encoded-json",
        }

        result = _mask_secrets(config)
        assert result["key_file_content"] == "***REDACTED***"

    def test_mask_secrets_multiple_fields(self):
        """Test masking multiple sensitive fields."""
        from api.routes.config import _mask_secrets

        config = {
            "client_secret": "secret1",
            "key_file_content": "secret2",
            "service_account_key": "secret3",
            "public_field": "ok",
        }

        result = _mask_secrets(config)
        assert result["client_secret"] == "***REDACTED***"
        assert result["key_file_content"] == "***REDACTED***"
        assert result["service_account_key"] == "***REDACTED***"
        assert result["public_field"] == "ok"


class TestConfigEncryption:
    """Tests for config encryption integration."""

    def test_encrypt_config(self):
        """Test encrypting a config dict."""
        from api.routes.config import create_config
        from api.models import Provider, CredentialType
        from pydantic import BaseModel

        class MockData(BaseModel):
            provider: Provider
            name: str
            credential_type: CredentialType
            config: dict

        data = MockData(
            provider=Provider.AZURE,
            name="Config",
            credential_type=CredentialType.SERVICE_PRINCIPAL,
            config={
                "tenant_id": "tenant",
                "client_secret": "secret",
                "client_id": "client",
            },
        )

        with patch("api.db.insert_and_return", return_value="id"):
            with patch("api.routes.config.encrypt_config") as mock_encrypt:
                mock_encrypt.return_value = {
                    "tenant_id": "tenant",
                    "client_secret": "encrypted",
                    "client_id": "client",
                }
                create_config(data)
                mock_encrypt.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
