"""Comprehensive unit tests for utils/encryption.py - Fernet encryption utilities."""

from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock


class TestEncryptionKey:
    """Tests for encryption key generation."""

    def test_get_encryption_key_from_env(self):
        """Test getting key from environment variable."""
        # Clean up first
        if "ENCRYPTION_KEY" in os.environ:
            del os.environ["ENCRYPTION_KEY"]

        # Generate initial key
        from utils.encryption import _get_encryption_key, _fernet

        # Should work (creates key if not set)
        key1 = _get_encryption_key()
        assert key1 is not None

    def test_encryption_key_format(self):
        """Test encryption key is valid Fernet key."""
        from utils.encryption import _get_encryption_key

        key = _get_encryption_key()
        # Fernet keys are 32 URL-safe base64-encoded bytes (44 chars)
        assert len(key) == 44 or len(key) == 32


class TestEncrypt:
    """Tests for encrypt function."""

    def test_encrypt_string(self):
        """Test encrypting a string."""
        from utils.encryption import encrypt

        result = encrypt("test-secret-password")
        assert result != "test-secret-password"
        assert len(result) > len("test-secret-password")
        assert isinstance(result, str)

    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        from utils.encryption import encrypt

        result = encrypt("")
        assert result == ""

    def test_encrypt_bytes(self):
        """Test encrypting bytes input."""
        from utils.encryption import encrypt

        result = encrypt(b"test-bytes")
        assert result != "test-bytes"
        assert isinstance(result, str)


class TestDecrypt:
    """Tests for decrypt function."""

    def test_decrypt_valid_token(self):
        """Test decrypting valid encrypted token."""
        from utils.encryption import encrypt, decrypt

        original = "test-password-12345"
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        assert decrypted == original

    def test_decrypt_empty_string(self):
        """Test decrypting empty string."""
        from utils.encryption import decrypt

        result = decrypt("")
        assert result == ""

    def test_decrypt_invalid_token(self):
        """Test decrypting invalid token returns original."""
        from utils.encryption import decrypt

        result = decrypt("invalid-token-here")
        assert result == "invalid-token-here"

    def test_decrypt_corrupted_token(self):
        """Test decrypting corrupted token."""
        from utils.encryption import decrypt

        result = decrypt("abc.def.ghi")
        assert "abc.def.ghi" in result


class TestEncryptConfig:
    """Tests for encrypt_config function."""

    def test_encrypt_config_sensitive_fields(self):
        """Test encrypting config with sensitive fields."""
        from utils.encryption import encrypt_config

        config = {
            "id": "test-id",
            "provider": "azure",
            "client_secret": "my-secret",
            "tenant_id": "tenant123",
        }

        encrypted = encrypt_config(config)

        assert encrypted["client_secret"] != "my-secret"
        assert encrypted["tenant_id"] == "tenant123"  # Not sensitive

    def test_encrypt_config_nested_dict_top_level(self):
        """Test encrypting config with nested dict at top level."""
        from utils.encryption import encrypt_config

        # Nested dicts are encrypted only if they are SENSITIVE_FIELDS themselves
        config = {
            "id": "test-id",
            "config": {
                "client_secret": "nested-secret",
                "other_field": "value",
            },
        }

        encrypted = encrypt_config(config)

        # SENSITIVE_FIELDS only matches top-level keys
        # nested "client_secret" inside "config" dict is not encrypted
        assert encrypted["config"]["client_secret"] == "nested-secret"
        assert encrypted["config"]["other_field"] == "value"

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

    def test_encrypt_config_empty_config(self):
        """Test encrypting empty config."""
        from utils.encryption import encrypt_config

        result = encrypt_config({})
        assert result == {}

    def test_encrypt_config_non_dict(self):
        """Test encrypt_config with non-dict input."""
        from utils.encryption import encrypt_config

        with pytest.raises(AttributeError):
            encrypt_config("not a dict")


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

    def test_decrypt_config_empty_config(self):
        """Test decrypting empty config."""
        from utils.encryption import decrypt_config

        result = decrypt_config({})
        assert result == {}

    def test_decrypt_config_nested(self):
        """Test decrypting nested config."""
        from utils.encryption import encrypt_config, decrypt_config

        config = {
            "outer": "value",
            "nested": {
                "client_secret": "nested-secret",
                "other": "data",
            },
        }

        encrypted = encrypt_config(config)
        decrypted = decrypt_config(encrypted)

        assert decrypted["nested"]["client_secret"] == "nested-secret"
        assert decrypted["nested"]["other"] == "data"


class TestSensitiveFields:
    """Tests for SENSITIVE_FIELDS constant."""

    def test_sensitive_fields_defined(self):
        """Test that SENSITIVE_FIELDS contains expected fields."""
        from utils.encryption import SENSITIVE_FIELDS

        assert "client_secret" in SENSITIVE_FIELDS
        assert "key_file_content" in SENSITIVE_FIELDS
        assert "service_account_key" in SENSITIVE_FIELDS

    def test_sensitive_fields_count(self):
        """Test SENSITIVE_FIELDS has expected number of fields."""
        from utils.encryption import SENSITIVE_FIELDS

        assert len(SENSITIVE_FIELDS) == 3


class TestEncryptionRoundtrip:
    """Tests for encryption/decryption roundtrip."""

    def test_roundtrip_simple_string(self):
        """Test simple string roundtrip."""
        from utils.encryption import encrypt, decrypt

        test_cases = [
            "password123",
            "secret-key-value",
            "token:abc123xyz789",
            "A" * 100,  # Long string
        ]

        for secret in test_cases:
            encrypted = encrypt(secret)
            decrypted = decrypt(encrypted)
            assert decrypted == secret

    def test_roundtrip_with_special_chars(self):
        """Test roundtrip with special characters."""
        from utils.encryption import encrypt, decrypt

        test_cases = [
            "pass@word#123",
            "secret!@#$%^&*()",
            "key with spaces",
        ]

        for secret in test_cases:
            encrypted = encrypt(secret)
            decrypted = decrypt(encrypted)
            assert decrypted == secret


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
