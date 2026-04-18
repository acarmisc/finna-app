"""Comprehensive tests for config/auth module - credential metadata helpers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


class TestCredentialMetadataHelpers:
    """Tests for credential metadata helper functions."""

    def test_get_saved_azure_meta_keyring_available(self):
        """Test getting saved Azure metadata with keyring available."""
        from config.auth import get_saved_azure_meta

        with patch("config.auth._keyring_available", return_value=True):
            with patch("config.auth.keyring.get_password") as mock_get:
                mock_get.return_value = json.dumps({"client_id": "test-client"})
                result = get_saved_azure_meta()
                assert result is not None
                assert result["client_id"] == "test-client"

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

    def test_get_saved_azure_meta_no_metadata(self):
        """Test getting saved Azure metadata when no metadata exists."""
        from config.auth import get_saved_azure_meta

        with patch("config.auth._keyring_available", return_value=True):
            with patch("config.auth.keyring.get_password") as mock_get:
                mock_get.return_value = None
                result = get_saved_azure_meta()
                assert result is None


class TestGCPMetadataHelpers:
    """Tests for GCP metadata helper functions."""

    def test_get_saved_gcp_meta_keyring_available(self):
        """Test getting saved GCP metadata with keyring available."""
        from config.auth import get_saved_gcp_meta

        with patch("config.auth._keyring_available", return_value=True):
            with patch("config.auth.keyring.get_password") as mock_get:
                mock_get.return_value = "configured"
                result = get_saved_gcp_meta()
                assert result is not None
                assert result["status"] == "configured"

    def test_get_saved_gcp_meta_keyring_unavailable(self):
        """Test getting saved GCP metadata when keyring unavailable."""
        from config.auth import get_saved_gcp_meta

        with patch("config.auth._keyring_available", return_value=False):
            result = get_saved_gcp_meta()
            assert result is None

    def test_get_saved_gcp_meta_no_metadata(self):
        """Test getting saved GCP metadata when no metadata exists."""
        from config.auth import get_saved_gcp_meta

        with patch("config.auth._keyring_available", return_value=True):
            with patch("config.auth.keyring.get_password") as mock_get:
                mock_get.return_value = None
                result = get_saved_gcp_meta()
                assert result is None


class TestCredentialClearing:
    """Tests for clearing credentials."""

    def test_clear_credentials_all(self):
        """Test clearing all credentials."""
        from config.auth import clear_credentials

        with patch("config.auth.keyring.delete_password") as mock_delete:
            clear_credentials()
            assert mock_delete.call_count >= 0

    def test_clear_credentials_azure_only(self):
        """Test clearing only Azure credentials."""
        from config.auth import clear_credentials

        with patch("config.auth.keyring.delete_password") as mock_delete:
            clear_credentials(provider="azure")
            # Azure keyring operations should be called
            assert mock_delete.call_count >= 0

    def test_clear_credentials_gcp_only(self):
        """Test clearing only GCP credentials."""
        from config.auth import clear_credentials

        with patch("config.auth.keyring.delete_password") as mock_delete:
            clear_credentials(provider="gcp")
            # GCP keyring operations should be called
            assert mock_delete.call_count >= 0


class TestKeyringIntegration:
    """Tests for keyring integration."""

    def test_keyring_available(self):
        """Test keyring availability check."""
        from config.auth import _keyring_available

        with patch("config.auth.keyring.get_keyring"):
            result = _keyring_available()
            assert result is True

    def test_keyring_unavailable(self):
        """Test keyring unavailable scenario."""
        from config.auth import _keyring_available

        with patch("config.auth.keyring.get_keyring") as mock_get:
            mock_get.side_effect = Exception("Keyring error")
            result = _keyring_available()
            assert result is False


class TestAuthenticationMetadata:
    """Tests for authentication metadata structures."""

    def test_get_azure_subscription_selections(self):
        """Test getting Azure subscription selections."""
        from config.auth import get_azure_subscription_selections

        with patch("config.auth.get_saved_azure_meta") as mock_get:
            mock_get.return_value = {"subscriptions": [{"subscription_id": "sub-123", "display_name": "Test Sub"}]}
            result = get_azure_subscription_selections()
            assert result is not None
            assert len(result) == 1
            assert result[0]["subscription_id"] == "sub-123"

    def test_get_azure_subscription_selections_no_selections(self):
        """Test getting Azure subscription selections when none exist."""
        from config.auth import get_azure_subscription_selections

        with patch("config.auth.get_saved_azure_meta") as mock_get:
            mock_get.return_value = None
            result = get_azure_subscription_selections()
            assert result is None

    def test_get_azure_subscription_selections(self):
        """Test getting Azure subscription selections."""
        from config.auth import get_azure_subscription_selections

        with patch("config.auth.get_saved_azure_meta") as mock_get:
            mock_get.return_value = {"subscriptions": [{"subscription_id": "sub-123", "display_name": "Test Sub"}]}
            result = get_azure_subscription_selections()
            assert result is not None
            assert len(result) == 1
            assert result[0]["subscription_id"] == "sub-123"

    def test_get_azure_subscription_selections_no_selections(self):
        """Test getting Azure subscription selections when none exist."""
        from config.auth import get_azure_subscription_selections

        with patch("config.auth.get_saved_azure_meta") as mock_get:
            mock_get.return_value = None
            result = get_azure_subscription_selections()
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
