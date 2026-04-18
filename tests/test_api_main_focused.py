"""Comprehensive tests for api/main.py - FastAPI application setup."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# Don't pre-set ENCRYPTION_KEY - let modules generate their own
if "ENCRYPTION_KEY" in os.environ:
    del os.environ["ENCRYPTION_KEY"]


class TestRateLimitFunctions:
    """Tests for rate limit configuration functions."""

    def test_rate_limit_from_env_valid(self):
        """Test rate limit parsing from valid env var."""
        from api.main import rate_limit_from_env

        with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "100"}):
            result = rate_limit_from_env("RATE_LIMIT_PER_MINUTE", 60)
            assert result == 100

    def test_rate_limit_from_env_invalid(self):
        """Test rate limit parsing from invalid env var falls back to default."""
        from api.main import rate_limit_from_env

        with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "not_a_number"}):
            result = rate_limit_from_env("RATE_LIMIT_PER_MINUTE", 60)
            assert result == 60

    def test_rate_limit_from_env_not_set(self):
        """Test rate limit parsing when env var not set."""
        from api.main import rate_limit_from_env

        if "RATE_LIMIT_PER_MINUTE" in os.environ:
            del os.environ["RATE_LIMIT_PER_MINUTE"]

        result = rate_limit_from_env("RATE_LIMIT_PER_MINUTE", 60)
        assert result == 60

    def test_rate_limit_defaults(self):
        """Test default rate limit values."""
        from api.main import RATE_LIMIT_PER_MINUTE, RATE_LIMIT_PER_HOUR

        assert RATE_LIMIT_PER_MINUTE > 0
        assert RATE_LIMIT_PER_HOUR > 0

    def test_extractor_rate_limits(self):
        """Test extractor rate limit configuration."""
        from api.main import EXTRACTOR_LIMIT_PER_MINUTE, EXTRACTOR_LIMIT_PER_HOUR

        assert EXTRACTOR_LIMIT_PER_MINUTE > 0
        assert EXTRACTOR_LIMIT_PER_HOUR > 0


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    def test_middleware_initialization(self):
        """Test middleware can be instantiated."""
        from api.main import RateLimitMiddleware
        from fastapi import FastAPI

        app = FastAPI()
        middleware = RateLimitMiddleware(app)

        assert middleware.app is not None

    def test_dispatch_passes_through(self):
        """Test dispatch passes through normal requests."""
        from api.main import RateLimitMiddleware

        app = FastAPI()
        middleware = RateLimitMiddleware(app)

        class MockRequest:
            url = MagicMock()
            url.path = "/api/v1/healthz"

        async def mock_call_next(request):
            return MagicMock()

        result = middleware.dispatch(MockRequest(), mock_call_next)
        assert result is not None


class TestTokenVerificationMiddleware:
    """Tests for TokenVerificationMiddleware."""

    def test_middleware_initialization(self):
        """Test middleware can be instantiated."""
        from api.main import TokenVerificationMiddleware
        from fastapi import FastAPI

        app = FastAPI()
        middleware = TokenVerificationMiddleware(app)

        assert middleware.app is not None

    def test_open_route_without_token(self):
        """Test open routes don't require token."""
        from api.main import TokenVerificationMiddleware

        app = FastAPI()
        middleware = TokenVerificationMiddleware(app)

        class MockRequest:
            url = MagicMock()
            url.path = "/api/v1/auth/token"

        async def mock_call_next(request):
            return MagicMock()

        result = middleware.dispatch(MockRequest(), mock_call_next)
        assert result is not None

    def test_protected_route_without_token(self):
        """Test protected routes reject requests without token."""
        from api.main import TokenVerificationMiddleware

        app = FastAPI()
        middleware = TokenVerificationMiddleware(app)

        class MockRequest:
            url = MagicMock()
            url.path = "/api/v1/protected"
            headers = {}

        async def mock_call_next(request):
            return MagicMock()

        result = middleware.dispatch(MockRequest(), mock_call_next)
        assert result is not None
        # Should return 401 for missing token
        assert hasattr(result, "status_code")


class TestAppStructure:
    """Tests for FastAPI app structure."""

    def test_app_has_title(self):
        """Test app has title configured."""
        from api.main import app

        assert app.title == "FinOps Orchestrator API"

    def test_app_has_version(self):
        """Test app has version configured."""
        from api.main import app

        assert app.version is not None

    def test_app_has_routes(self):
        """Test app has routes defined."""
        from api.main import app

        assert len(app.routes) > 0


class TestAppLifespan:
    """Tests for application lifespan."""

    def test_lifespan_exists(self):
        """Test lifespan is configured in app."""
        from api.main import app
        from api.main import lifespan

        assert lifespan is not None


class TestAppConfiguration:
    """Tests for app configuration."""

    def test_cors_middleware(self):
        """Test CORS middleware is configured."""
        from api.main import app

        # Check that CORS middleware exists
        cors_found = False
        for middleware in app.user_middleware:
            if "CORS" in str(middleware):
                cors_found = True
                break
        assert cors_found, "CORS middleware not found"

    def test_rate_limit_middleware(self):
        """Test rate limit middleware is configured."""
        from api.main import app

        rate_limit_found = False
        for middleware in app.user_middleware:
            if "RateLimit" in str(middleware):
                rate_limit_found = True
                break
        assert rate_limit_found, "RateLimit middleware not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
