"""Comprehensive unit tests for api/main.py - FastAPI application setup."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    def test_rate_limit_middleware_passes_through(self):
        """Test middleware passes through正常 requests."""
        from api.main import RateLimitMiddleware

        class MockRequest:
            url = MagicMock()
            url.path = "/api/v1/healthz"

        class MockCallNext:
            async def __call__(self, request):
                return MagicMock()

        middleware = RateLimitMiddleware(MagicMock())
        request = MockRequest()

        with patch("api.main.RateLimitExceeded"):
            result = middleware.dispatch(request, MockCallNext().__call__)
            assert result is not None

    def test_rate_limit_middleware_handles_exception(self):
        """Test middleware handles RateLimitExceeded exception."""
        from api.main import RateLimitMiddleware
        from slowapi.errors import RateLimitExceeded

        class MockRequest:
            url = MagicMock()
            url.path = "/api/v1/test"

        async def mock_call_next(request):
            raise RateLimitExceeded("Rate limit exceeded")

        middleware = RateLimitMiddleware(MagicMock())
        result = middleware.dispatch(MockRequest(), mock_call_next)

        assert result.status_code == 429
        assert "rate_limit_exceeded" in result.body.decode()


class TestTokenVerificationMiddleware:
    """Tests for TokenVerificationMiddleware."""

    def test_token_verification_passes_for_open_routes(self):
        """Test middleware allows open routes without token."""
        from api.main import TokenVerificationMiddleware

        class MockRequest:
            url = MagicMock()
            url.path = "/api/v1/auth/token"

        async def mock_call_next(request):
            return MagicMock()

        middleware = TokenVerificationMiddleware(MagicMock())
        result = middleware.dispatch(MockRequest(), mock_call_next)
        assert result is not None

    def test_token_verification_handles_missing_token(self):
        """Test middleware rejects requests without token."""
        from api.main import TokenVerificationMiddleware

        class MockRequest:
            url = MagicMock()
            url.path = "/api/v1/protected"

        async def mock_call_next(request):
            return MagicMock()

        middleware = TokenVerificationMiddleware(MagicMock())
        result = middleware.dispatch(MockRequest(), mock_call_next)

        assert result.status_code == 401
        assert "missing_token" in result.body.decode()

    def test_token_verification_handles_invalid_token(self):
        """Test middleware rejects requests with invalid token."""
        from api.main import TokenVerificationMiddleware

        class MockRequest:
            url = MagicMock()
            url.path = "/api/v1/protected"
            headers = {"Authorization": "Bearer invalid.token.here"}

        async def mock_call_next(request):
            return MagicMock()

        with patch("api.main.decode_token") as mock_decode:
            mock_decode.side_effect = MagicMock()
            from fastapi import HTTPException

            mock_decode.side_effect = HTTPException(status_code=401)

            middleware = TokenVerificationMiddleware(MagicMock())
            result = middleware.dispatch(MockRequest(), mock_call_next)

            assert result.status_code == 401


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


class TestAppConfiguration:
    """Tests for FastAPI app configuration."""

    def test_app_has_lifespan(self):
        """Test that app has lifespan context manager."""
        from api.main import app

        assert hasattr(app, "lifespan")
        assert app.lifespan is not None

    def test_app_has_routers(self):
        """Test that app includes required routers."""
        from api.main import app

        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert any("/api/v1" in r for r in routes)

    def test_app_has_middleware(self):
        """Test that app has required middleware."""
        from api.main import app

        middleware_types = [type(m.middleware_class) for m in app.user_middleware]
        assert any("CORSMiddleware" in str(t) for t in middleware_types)


class TestLifespan:
    """Tests for application lifespan initialization."""

    def test_lifespan_initializes_database(self):
        """Test lifespan initializes database connection pool."""
        from api.main import lifespan
        from fastapi import FastAPI

        app = FastAPI()

        with patch("api.main.init_sync_pool") as mock_init:
            with patch("api.main.init_db") as mock_init_db:
                with patch("api.main.close_pools"):
                    with patch("api.main.query_all") as mock_query:
                        mock_query.return_value = []
                        list(lifespan(app))
                        mock_init.assert_called_once()

    def test_lifespan_handles_db_init_failure(self):
        """Test lifespan handles database initialization failure gracefully."""
        from api.main import lifespan
        from fastapi import FastAPI

        app = FastAPI()

        with patch("api.main.init_sync_pool") as mock_init:
            mock_init.side_effect = Exception("DB connection failed")
            with patch("api.main.init_db") as mock_init_db:
                with patch("api.main.close_pools"):
                    with patch("api.main.query_all") as mock_query:
                        mock_query.return_value = []
                        list(lifespan(app))
                        mock_init.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
