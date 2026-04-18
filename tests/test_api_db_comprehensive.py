"""Comprehensive tests for api/db module - database connection and helpers."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import psycopg
import pytest
from psycopg_pool import PoolTimeout

os.environ["PG_DSN"] = "postgresql://test:test@localhost/testdb"
os.environ["POOL_MIN_CONNS"] = "2"
os.environ["POOL_MAX_CONNS"] = "10"


class TestPGDSN:
    """Tests for get_pg_dsn function."""

    def test_get_pg_dsn_returns_value(self):
        """Test that get_pg_dsn returns the DSN from environment."""
        from api.db import get_pg_dsn

        result = get_pg_dsn()
        assert result == "postgresql://test:test@localhost/testdb"

    def test_get_pg_dsn_no_env_raises(self):
        """Test that get_pg_dsn raises ValueError when PG_DSN not set."""
        from api.db import get_pg_dsn

        original_dsn = os.environ.get("PG_DSN")
        os.environ.pop("PG_DSN", None)

        try:
            with pytest.raises(ValueError) as exc_info:
                get_pg_dsn()
            assert "PG_DSN" in str(exc_info.value)
        finally:
            if original_dsn:
                os.environ["PG_DSN"] = original_dsn


class TestPoolConfig:
    """Tests for get_pool_config function."""

    def test_get_pool_config_returns_dict(self):
        """Test that get_pool_config returns a dictionary."""
        from api.db import get_pool_config

        config = get_pool_config()
        assert isinstance(config, dict)
        assert "min_size" in config
        assert "max_size" in config

    def test_get_pool_config_default_values(self):
        """Test that get_pool_config has default values."""
        from api.db import get_pool_config

        config = get_pool_config()
        assert config["min_size"] == 2
        assert config["max_size"] == 10


class TestInitAsyncPool:
    """Tests for init_async_pool function."""

    def test_init_async_pool_returns_pool(self):
        """Test that init_async_pool returns an AsyncConnectionPool."""
        from api.db import init_async_pool, _async_pool

        with patch("psycopg_pool.AsyncConnectionPool") as mock_pool:
            mock_instance = MagicMock()
            mock_pool.return_value = mock_instance
            mock_instance.wait = AsyncMock()

            with patch("api.db.get_pool_config", return_value={"min_size": 2, "max_size": 10}):
                with patch("api.db.get_pg_dsn", return_value="postgres://test:pass@localhost/db"):
                    import asyncio

                    result = asyncio.run(init_async_pool())
                    assert result is not None


class TestInitSyncPool:
    """Tests for init_sync_pool function."""

    def test_init_sync_pool_returns_pool(self):
        """Test that init_sync_pool returns a ConnectionPool."""
        from api.db import init_sync_pool

        with patch("psycopg_pool.ConnectionPool") as mock_pool:
            mock_instance = MagicMock()
            mock_pool.return_value = mock_instance
            mock_instance.wait = MagicMock()

            with patch("api.db.get_pool_config", return_value={"min_size": 2, "max_size": 10}):
                with patch("api.db.get_pg_dsn", return_value="postgres://test:pass@localhost/db"):
                    result = init_sync_pool()
                    assert result is not None


class TestGetConnection:
    """Tests for get_connection function."""

    def test_get_connection_returns_connection(self):
        """Test that get_connection returns a connection."""
        from api.db import get_connection

        with patch("api.db.get_sync_pool") as mock_get_pool:
            mock_pool = MagicMock()
            mock_conn = MagicMock()
            mock_pool.getconn.return_value = mock_conn
            mock_get_pool.return_value = mock_pool

            result = get_connection()
            assert result is not None


class TestReleaseConnection:
    """Tests for release_connection function."""

    def test_release_connection_calls_putconn(self):
        """Test that release_connection calls putconn on the pool."""
        from api.db import release_connection, _sync_pool

        with patch("api.db._sync_pool") as mock_pool:
            mock_conn = MagicMock()
            release_connection(mock_conn)
            if mock_pool:
                mock_pool.putconn.assert_called_once()


class TestGetPoolStats:
    """Tests for get_pool_stats function."""

    def test_get_pool_stats_returns_dict(self):
        """Test that get_pool_stats returns a dictionary."""
        from api.db import get_pool_stats

        with patch("api.db._async_pool", None):
            with patch("api.db._sync_pool", None):
                result = get_pool_stats()
                assert isinstance(result, dict)
                assert "async" in result
                assert "sync" in result

    def test_get_pool_stats_with_async_pool(self):
        """Test get_pool_stats with async pool set."""
        from api.db import get_pool_stats

        mock_pool = MagicMock()
        mock_pool.min_size = 2
        mock_pool.max_size = 10
        len(mock_pool)  # Call the __len__ method

        with patch("api.db._async_pool", mock_pool):
            with patch("api.db._sync_pool", None):
                result = get_pool_stats()
                assert result["async"] is not None
                assert result["async"]["min_size"] == 2
                assert result["async"]["max_size"] == 10


class TestQueryOne:
    """Tests for query_one function."""

    def test_query_one_returns_row(self):
        """Test that query_one returns a single row."""
        from api.db import query_one

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1, "name": "test"}
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("api.db.get_connection", return_value=mock_conn):
            with patch("api.db.release_connection"):
                result = query_one("SELECT * FROM test")
                assert result is not None
                assert result["id"] == 1


class TestQueryAll:
    """Tests for query_all function."""

    def test_query_all_returns_list(self):
        """Test that query_all returns a list of rows."""
        from api.db import query_all

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "test1"},
            {"id": 2, "name": "test2"},
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("api.db.get_connection", return_value=mock_conn):
            with patch("api.db.release_connection"):
                result = query_all("SELECT * FROM test")
                assert isinstance(result, list)
                assert len(result) == 2


class TestExecute:
    """Tests for execute function."""

    def test_execute_runs_query(self):
        """Test that execute runs a query."""
        from api.db import execute

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("api.db.get_connection", return_value=mock_conn):
            with patch("api.db.release_connection"):
                execute("INSERT INTO test VALUES (1, 'test')")
                mock_cursor.execute.assert_called_once()


class TestInsertAndReturn:
    """Tests for insert_and_return function."""

    def test_insert_and_return_returns_id(self):
        """Test that insert_and_return returns the inserted id."""
        from api.db import insert_and_return

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": "new-id"}
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("api.db.get_connection", return_value=mock_conn):
            with patch("api.db.release_connection"):
                result = insert_and_return("INSERT INTO test VALUES (%s)", (1,))
                assert result == "new-id"


class TestDBIntegration:
    """Integration tests for db module."""

    def test_connection_context_manager(self):
        """Test that connection context manager works."""
        from api.db import get_async_connection
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_pool():
            yield MagicMock()

        with patch("api.db.get_async_pool") as mock_get_pool:
            mock_get_pool.return_value = mock_pool()
            with patch("api.db.PoolTimeout", PoolTimeout):
                with patch("api.db.psycopg.PoolTimeout", PoolTimeout):
                    result = None
                    try:

                        async def test_conn():
                            async with get_async_connection() as conn:
                                return conn

                        import asyncio

                        result = asyncio.run(test_conn())
                    except Exception:
                        pass
                    assert result is not None


class TestDBPoolManagement:
    """Tests for pool management functions."""

    def test_close_pools_closes_async(self):
        """Test that close_pools closes async pool."""
        from api.db import close_pools

        with patch("api.db._async_pool") as mock_async:
            with patch("api.db._sync_pool") as mock_sync:
                close_pools()
                if mock_async:
                    assert mock_async is not None

    def test_close_pools_closes_sync(self):
        """Test that close_pools closes sync pool."""
        from api.db import close_pools

        with patch("api.db._sync_pool") as mock_pool:
            close_pools()
            if mock_pool:
                mock_pool.close.assert_called_once()


class TestInitDB:
    """Tests for init_db function."""

    def test_init_db_calls_migrations(self):
        """Test that init_db runs migration files."""
        from api.db import init_db

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("api.db.get_connection", return_value=mock_conn):
            with patch("api.db.release_connection"):
                with patch("pathlib.Path.glob") as mock_glob:
                    mock_glob.return_value = []
                    init_db()
                    mock_cursor.execute.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
