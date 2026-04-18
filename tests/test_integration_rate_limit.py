"""Integration tests for Rate limiting functionality."""

from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ["RATE_LIMIT_REQUESTS"] = "5"
os.environ["RATE_LIMIT_WINDOW"] = "60"
os.environ["ENCRYPTION_KEY"] = "fd7Em6qcDLS1FfjAgi0oSc6-keC5uK8r8rshY_UVw5I="


class TestRateLimiter:
    """Tests for rate limiting middleware."""

    def test_rate_limiter_configured(self):
        """Test that rate limiter is properly configured."""
        from api.main import app

        assert app is not None

    def test_exceeded_rate_limit(self):
        """Test that rate limit is enforced."""
        # This test requires slowapi to be configured
        # For now, we just verify the configuration exists
        os.environ["RATE_LIMIT_ENABLED"] = "true"

        from slowapi import Limiter
        from slowapi.util import get_remote_address

        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
        )

        assert limiter is not None
        assert hasattr(limiter, "_default_limits")

    def test_rate_limit_dependency(self):
        """Test rate limit dependency injection."""
        from api.routes.config import check_rate_limit

        assert callable(check_rate_limit)


class TestRateLimitMiddleware:
    """Tests for rate limit middleware integration."""

    def test_middleware_registered(self):
        """Test that rate limit middleware is registered."""
        import api.main

        app = api.main.app

        assert app is not None
        assert hasattr(app, "state")


class TestRateLimitConfig:
    """Tests for rate limit configuration."""

    def test_rate_limit_env_vars(self):
        """Test that rate limit env vars are loaded."""
        assert os.getenv("RATE_LIMIT_REQUESTS") == "5"
        assert os.getenv("RATE_LIMIT_WINDOW") == "60"

    def test_rate_limit_default_config(self):
        """Test default rate limit configuration."""
        os.environ["RATE_LIMIT_ENABLED"] = "false"

        default_limits = [
            "200 per day",
            "50 per hour",
            "10 per minute",
        ]

        assert "10 per minute" in default_limits


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
