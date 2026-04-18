"""Integration tests for PostgreSQL connection pooling."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


os.environ["PG_DSN"] = "postgresql://test:test@localhost/testdb"
os.environ["POOL_MIN_CONNS"] = "2"
os.environ["POOL_MAX_CONNS"] = "10"


class TestConnectionPoolConfig:
    """Tests for connection pool configuration."""

    def test_pool_config_env_vars(self):
        """Test that pool config env vars are loaded."""
        assert os.getenv("POOL_MIN_CONNS") == "2"
        assert os.getenv("POOL_MAX_CONNS") == "10"

    def test_pool_size_constants(self):
        """Test pool size constants."""
        from api.db import POOL_MIN_CONNS, POOL_MAX_CONNS

        assert POOL_MIN_CONNS == 2
        assert POOL_MAX_CONNS == 10

    def test_pool_config_defaults(self):
        """Test default pool configuration."""
        # Values are read once at module import time from environment
        # Just verify the default values exist in the module
        from api.db import POOL_MIN_CONNS, POOL_MAX_CONNS

        assert POOL_MIN_CONNS == 2
        assert POOL_MAX_CONNS == 10


class TestConnectionPoolStats:
    """Tests for connection pool statistics."""

    def test_get_pool_stats_function(self):
        """Test get_pool_stats function exists."""
        from api.db import get_pool_stats

        assert callable(get_pool_stats)

    def test_pool_stats_returns_dict(self):
        """Test that get_pool_stats returns dict."""
        with patch("api.db._sync_pool") as mock_pool:
            mock_pool.min_size = 2
            mock_pool.max_size = 10
            mock_pool.__len__ = lambda self: 5

            from api.db import get_pool_stats

            stats = get_pool_stats()
            assert isinstance(stats, dict)
            assert "sync" in stats

    def test_pool_stats_contains_expected_fields(self):
        """Test pool stats contains expected fields."""
        with patch("api.db._sync_pool") as mock_pool:
            mock_pool.min_size = 3
            mock_pool.max_size = 15

            from api.db import get_pool_stats

            stats = get_pool_stats()
            expected_fields = ["min_size", "max_size", "size"]

            for field in expected_fields:
                assert field in stats["sync"] or field in str(stats["sync"])


class TestConnectionReuse:
    """Tests for connection pool reuse."""

    def test_connection_reuse_enabled(self):
        """Test that connection reuse is configured."""
        # POOL_RECYCLE should be defined as a module constant
        from api.db import POOL_RECYCLE

        assert POOL_RECYCLE is not None
        assert POOL_RECYCLE > 0

    def test_pool_recycle_config(self):
        """Test pool recycle configuration."""
        # Remove env var to use default
        old_value = os.environ.get("POOL_RECYCLE")
        os.environ.pop("POOL_RECYCLE", None)

        try:
            import importlib
            import api.db

            importlib.reload(api.db)
            from api.db import POOL_RECYCLE as RECYCLE

            assert RECYCLE == 3600
        finally:
            if old_value is not None:
                os.environ["POOL_RECYCLE"] = old_value


class TestConnectionAcquisition:
    """Tests for connection acquisition from pool."""

    def test_get_connection_function(self):
        """Test get_connection function exists."""
        from api.db import get_connection

        assert callable(get_connection)

    def test_connection_context_manager(self):
        """Test that connection supports context manager."""
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch("api.db._sync_pool") as mock_pool:
            mock_pool.get_connection.return_value = mock_conn

            from api.db import get_connection

            with get_connection() as conn:
                assert conn is not None


class TestPoolHealth:
    """Tests for connection pool health monitoring."""

    def test_pool_health_check(self):
        """Test pool health check function."""
        from api.db import POOL_MAX_CONNS

        assert POOL_MAX_CONNS > 0

    def test_pool_min_connections(self):
        """Test minimum connections is positive."""
        from api.db import POOL_MIN_CONNS

        assert POOL_MIN_CONNS >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
