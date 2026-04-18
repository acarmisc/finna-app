"""Integration tests for Secret encryption functionality."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ["ENCRYPTION_KEY"] = "fd7Em6qcDLS1FfjAgi0oSc6-keC5uK8r8rshY_UVw5I="
os.environ["PG_DSN"] = "postgresql://test:test@localhost/testdb"


class TestEncryption:
    """Tests for encryption/decryption functions."""

    def test_encrypt_string(self):
        """Test encrypting a string."""
        from utils.encryption import encrypt

        plaintext = "test-secret-password"
        encrypted = encrypt(plaintext)

        assert encrypted != plaintext
        assert isinstance(encrypted, str)
        assert len(encrypted) > len(plaintext)

    def test_decrypt_string(self):
        """Test decrypting a string."""
        from utils.encryption import encrypt, decrypt

        plaintext = "test-password-12345"
        encrypted = encrypt(plaintext)
        decrypted = decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption roundtrip."""
        from utils.encryption import encrypt, decrypt

        secrets = ["password123", "secret-key-value", "my-super-secret-token"]

        for secret in secrets:
            encrypted = encrypt(secret)
            decrypted = decrypt(encrypted)
            assert decrypted == secret

    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        from utils.encryption import encrypt

        assert encrypt("") == ""

    def test_decrypt_empty_string(self):
        """Test decrypting empty string."""
        from utils.encryption import decrypt

        assert decrypt("") == ""

    def test_decrypt_invalid_token(self):
        """Test decrypting invalid token returns original."""
        from utils.encryption import decrypt

        result = decrypt("invalid-token-here")
        assert result == "invalid-token-here"


class TestEncryptConfig:
    """Tests for encrypt_config function."""

    def test_encrypt_config_sensitive_fields(self):
        """Test encrypting config with sensitive fields."""
        from utils.encryption import encrypt_config

        config = {
            "id": "test-id",
            "provider": "azure",
            "name": "Test Config",
            "client_secret": "my-secret-key",
            "tenant_id": "tenant123",
        }

        encrypted = encrypt_config(config)

        assert encrypted["client_secret"] != "my-secret-key"
        assert encrypted["tenant_id"] == "tenant123"

    def test_encrypt_config_nested_dict(self):
        """Test encrypting nested dict."""
        from utils.encryption import encrypt_config

        config = {
            "id": "test-id",
            "config": {
                "client_secret": "nested-secret",
                "other_field": "value",
            },
        }

        encrypted = encrypt_config(config)

        assert encrypted["config"]["client_secret"] != "nested-secret"

    def test_encrypt_config_skip_non_sensitive(self):
        """Test that non-sensitive fields are unchanged."""
        from utils.encryption import encrypt_config

        config = {
            "id": "test-id",
            "provider": "azure",
            "name": "Test",
            "tenant_id": "123",
        }

        encrypted = encrypt_config(config)

        assert encrypted["provider"] == "azure"
        assert encrypted["tenant_id"] == "123"


class TestDecryptConfig:
    """Tests for decrypt_config function."""

    def test_decrypt_config_sensitive_fields(self):
        """Test decrypting config with encrypted fields."""
        from utils.encryption import encrypt_config, decrypt_config

        config = {
            "id": "test-id",
            "client_secret": "my-secret",
        }

        encrypted = encrypt_config(config)
        decrypted = decrypt_config(encrypted)

        assert decrypted["client_secret"] == "my-secret"

    def test_decrypt_config_skip_non_encrypted(self):
        """Test that non-encrypted fields pass through."""
        from utils.encryption import decrypt_config

        config = {
            "id": "test-id",
            "provider": "gcp",
        }

        decrypted = decrypt_config(config)

        assert decrypted["provider"] == "gcp"

    def test_decrypt_config_already_decrypted(self):
        """Test decrypting already-decrypted config."""
        from utils.encryption import decrypt_config

        config = {
            "id": "test-id",
            "client_secret": "not-encrypted",
        }

        result = decrypt_config(config)
        assert result["client_secret"] == "not-encrypted"


class TestSensitiveFields:
    """Tests for SENSITIVE_FIELDS constant."""

    def test_sensitive_fields_defined(self):
        """Test that SENSITIVE_FIELDS contains expected fields."""
        from utils.encryption import SENSITIVE_FIELDS

        assert "client_secret" in SENSITIVE_FIELDS
        assert "key_file_content" in SENSITIVE_FIELDS
        assert "service_account_key" in SENSITIVE_FIELDS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
