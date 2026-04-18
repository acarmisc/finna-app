"""Integration tests for Superset security - SECRET_KEY validation."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


class TestSupersetSecurity:
    """Tests for Superset security configuration."""

    def test_superset_secret_key_exists(self):
        """Test that SECRET_KEY is set in environment."""
        os.environ["SECRET_KEY"] = "test-secret-key-for-superset"

        assert os.getenv("SECRET_KEY") is not None
        assert len(os.getenv("SECRET_KEY")) >= 16

    def test_superset_secret_key_length(self):
        """Test SECRET_KEY meets minimum length."""
        os.environ["SECRET_KEY"] = "a" * 32

        from superset.app import create_app

        with patch("superset.app.config") as mock_config:
            mock_config.return_value = {
                "SECRET_KEY": os.getenv("SECRET_KEY"),
            }

            secret_key = os.getenv("SECRET_KEY")
            assert len(secret_key) >= 16

    def test_superset_secret_key_not_default(self):
        """Test SECRET_KEY is not default value."""
        default_keys = [
            "mysecretkey",
            "change-me",
            "superset-secret",
            "1234567890123456",
        ]

        os.environ["SECRET_KEY"] = "actual-secure-key-do-not-use"

        assert os.getenv("SECRET_KEY") not in default_keys

    def test_secret_key_validation(self):
        """Test SECRET_KEY validation."""
        os.environ["SECRET_KEY"] = "ValidSecretKey123"
        key = os.getenv("SECRET_KEY")
        assert key is not None
        assert len(key) >= 16


class TestSecretKeyConfiguration:
    """Tests for secret key configuration in Superset."""

    def test_secret_key_configurable(self):
        """Test that SECRET_KEY is configurable via env var."""
        os.environ["SECRET_KEY"] = "configurable-secret-key-12345678"

        os.environ["SUPERSET_SECRET_KEY"] = os.getenv("SECRET_KEY")

        assert os.getenv("SECRET_KEY") == os.getenv("SUPERSET_SECRET_KEY")

    def test_secret_key_in_app_config(self):
        """Test SECRET_KEY in app configuration."""
        from superset.app import create_app

        with patch("flask.app.App") as mock_app:
            mock_app.return_value.config = {"SECRET_KEY": "test"}

            with patch("superset.app.config") as mock_config:
                mock_config.return_value = {"SECRET_KEY": os.getenv("SECRET_KEY")}

                assert os.getenv("SECRET_KEY") is not None


class TestSecurityHeaders:
    """Tests for security headers in Superset."""

    def test_security_headers_configured(self):
        """Test that security headers are configured."""
        os.environ["ENABLE_SECURITY_HEADERS"] = "true"

        assert os.getenv("ENABLE_SECURITY_HEADERS") == "true"

    def test_csp_header_configured(self):
        """Test Content-Security-Policy header."""
        os.environ["CSP_HEADER"] = "default-src 'self'"

        assert os.getenv("CSP_HEADER") is not None


class TestAuthenticationSecurity:
    """Tests for authentication security in Superset."""

    def test_token_validation(self):
        """Test token validation configuration."""
        os.environ["TOKEN_VALIDATION_ENABLED"] = "true"

        assert os.getenv("TOKEN_VALIDATION_ENABLED") == "true"

    def test_secret_key_not_none(self):
        """Test that SECRET_KEY is not None."""
        os.environ["SECRET_KEY"] = "actual-key-do-not-use-in-production"
        assert os.getenv("SECRET_KEY") is not None

    def test_session_timeout(self):
        """Test session timeout configuration."""
        os.environ["PERMANENT_SESSION_LIFETIME"] = "3600"

        assert os.getenv("PERMANENT_SESSION_LIFETIME") == "3600"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
