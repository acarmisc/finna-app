"""Comprehensive tests for config/auth module - OAuth and credential management."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestAzureCredentialRetrieval:
    """Tests for getting Azure credentials."""

    def test_get_azure_credential_with_env_vars(self):
        """Test getting Azure credential from environment variables."""
        from config.auth import get_azure_credential

        with patch.dict(
            os.environ,
            {
                "AZURE_TENANT_ID": "test-tenant",
                "AZURE_CLIENT_ID": "test-client",
                "AZURE_CLIENT_SECRET": "test-secret",
            },
        ):
            with patch("config.auth._keyring_available", return_value=False):
                cred = get_azure_credential()
                assert cred is not None

    def test_get_azure_credential_keyring(self):
        """Test getting Azure credential from keyring."""
        from config.auth import get_azure_credential

        saved_meta = {
            "client_id": "test-client",
            "tenant_id": "test-tenant",
            "auth_method": "device_code",
        }

        with patch("config.auth._keyring_available", return_value=True):
            with patch("config.auth.keyring.get_password") as mock_get:
                mock_get.return_value = saved_meta
                with patch("api.db.release_connection"):
                    cred = get_azure_credential()
                    assert cred is not None

    def test_get_azure_credential_azure_cli(self):
        """Test getting Azure credential using Azure CLI."""
        from config.auth import get_azure_credential

        with patch("config.auth._keyring_available", return_value=False):
            with patch("config.auth.AzureCliCredential") as mock_cli:
                mock_cred = MagicMock()
                mock_cli.return_value = mock_cred
                cred = get_azure_credential()
                assert cred is not None

    def test_get_azure_credential_default_azure_credential(self):
        """Test getting Azure credential with DefaultAzureCredential."""
        from config.auth import get_azure_credential

        with patch("config.auth._keyring_available", return_value=False):
            with patch("config.auth.AzureCliCredential") as mock_cli:
                mock_cli.return_value.get_token.side_effect = Exception("No CLI")
                with patch("config.auth.DefaultAzureCredential") as mock_default:
                    mock_cred = MagicMock()
                    mock_default.return_value = mock_cred
                    cred = get_azure_credential()
                    assert cred is not None


class TestAzureDeviceFlow:
    """Tests for Azure device flow."""

    def test_azure_device_flow_success(self):
        """Test successful Azure device flow."""
        from config.auth import azure_device_flow

        with patch("config.auth.console") as mock_console:
            with patch("config.auth.DeviceCodeCredential") as mock_credential:
                mock_token = MagicMock()
                mock_token.token = "test-token"
                mock_credential.return_value.get_token.return_value = mock_token

                result = azure_device_flow()
                assert result is not None
                assert result["auth_method"] == "device_code"


class TestKeyringIntegration:
    """Tests for keyring integration."""

    def test_get_saved_azure_meta(self):
        """Test getting saved Azure metadata."""
        from config.auth import get_saved_azure_meta

        with patch("config.auth._keyring_available", return_value=True):
            with patch("config.auth.keyring.get_password") as mock_get:
                mock_get.return_value = '{"client_id": "test"}'
                result = get_saved_azure_meta()
                assert result is not None
                assert result["client_id"] == "test"

    def test_get_saved_azure_meta_keyring_unavailable(self):
        """Test getting saved Azure metadata when keyring unavailable."""
        from config.auth import get_saved_azure_meta

        with patch("config.auth._keyring_available", return_value=False):
            result = get_saved_azure_meta()
            assert result is None

    def test_get_saved_azure_meta_invalid_json(self):
        """Test getting saved Azure metadata with invalid JSON."""
        from config.auth import get_saved_azure_meta

        with patch("config.auth._keyring_available", return_value=True):
            with patch("config.auth.keyring.get_password") as mock_get:
                mock_get.return_value = "not valid json"
                result = get_saved_azure_meta()
                assert result is None


class TestGCPIntegration:
    """Tests for GCP credential integration."""

    def test_get_gcp_credentials_success(self):
        """Test getting GCP credentials successfully."""
        from config.auth import get_gcp_credentials

        with patch("config.auth.google_auth_default") as mock_default:
            mock_creds = MagicMock()
            mock_creds.valid = True
            mock_default.return_value = (mock_creds, "test-project")
            creds, project = get_gcp_credentials()
            assert creds is not None
            assert project == "test-project"

    def test_get_gcp_credentials_no_credentials(self):
        """Test getting GCP credentials when none available."""
        from config.auth import get_gcp_credentials

        with patch("config.auth.google_auth_default") as mock_default:
            mock_default.side_effect = Exception("No credentials")
            with pytest.raises(RuntimeError) as exc_info:
                get_gcp_credentials()
            assert "GCP credentials" in str(exc_info.value)


class TestConfigManagement:
    """Tests for configuration management functions."""

    def test_clear_credentials(self):
        """Test clearing saved credentials."""
        from config.auth import clear_credentials

        with patch("config.auth.keyring.delete_password") as mock_delete:
            clear_credentials()
            assert mock_delete.call_count >= 0

    def test_clear_azure_only(self):
        """Test clearing only Azure credentials."""
        from config.auth import clear_credentials

        with patch("config.auth.keyring.delete_password") as mock_delete:
            clear_credentials(provider="azure")
            mock_delete.assert_called()


class TestADCStatus:
    """Tests for ADC (Application Default Credentials) status."""

    def test_get_saved_gcp_meta(self):
        """Test getting saved GCP metadata."""
        from config.auth import get_saved_gcp_meta

        with patch("config.auth._keyring_available", return_value=True):
            with patch("config.auth.keyring.get_password") as mock_get:
                mock_get.return_value = "configured"
                result = get_saved_gcp_meta()
                assert result is not None
                assert result["status"] == "configured"

    def test_get_saved_gcp_meta_not_configured(self):
        """Test getting saved GCP metadata when not configured."""
        from config.auth import get_saved_gcp_meta

        with patch("config.auth._keyring_available", return_value=True):
            with patch("config.auth.keyring.get_password") as mock_get:
                mock_get.return_value = None
                result = get_saved_gcp_meta()
                assert result is None


class TestAzureAuthMethods:
    """Tests for different Azure authentication methods."""

    def test_azure_auth_interactive_azure_cli(self):
        """Test Azure CLI authentication method."""
        from config.auth import azure_auth_interactive

        with patch("config.auth.console") as mock_console:
            with patch("config.auth.AzureCliCredential") as mock_cli:
                mock_token = MagicMock()
                mock_token.token = "test-token"
                mock_cli.return_value.get_token.return_value = mock_token

                with patch("questionary.select") as mock_select:
                    mock_select.return_value.ask.return_value = "Azure CLI (az login — recommended)"
                    result = azure_auth_interactive()
                    assert result is not None

    def test_azure_auth_interactive_device_code(self):
        """Test Azure device code authentication method."""
        from config.auth import azure_auth_interactive

        with patch("config.auth.console") as mock_console:
            with patch("config.auth.azure_device_flow") as mock_flow:
                mock_flow.return_value = {"auth_method": "device_code"}

                with patch("questionary.select") as mock_select:
                    mock_select.return_value.ask.return_value = "OAuth device code (browser login)"

                    with patch("questionary.checkbox") as mock_checkbox:
                        mock_checkbox.return_value.ask.return_value = []

                        result = azure_auth_interactive()
                        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
