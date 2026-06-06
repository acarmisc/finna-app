"""Unit tests for database pooling, FastAPI main module, and runner utilities."""

from __future__ import annotations

import asyncio
import os
import secrets
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ["TESTING"] = "1"
os.environ["PG_DSN"] = "postgresql://test:***@localhost/testdb"
os.environ["POOL_MIN_CONNS"] = "1"
os.environ["POOL_MAX_CONNS"] = "5"
os.environ["JWT_SECRET"] = secrets.token_urlsafe(32)
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRATION_MINUTES"] = "60"

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "app"))

# ─────────────────────────────────────────────────────────────────────────────
# main.py
# ─────────────────────────────────────────────────────────────────────────────


def test_main_app_instance():
    from backend.app.api import main as main_module
    assert main_module.app is not None
    assert main_module.app.title == "Finna API"


def test_health_endpoint():
    from fastapi.testclient import TestClient

    from backend.app.api.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_api_health_endpoint_without_db():
    from fastapi.testclient import TestClient

    from backend.app.api import main as main_module

    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock(return_value=None)

    class FakeConnCtx:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *exc_info):
            return False

    mock_pool = MagicMock()
    mock_pool.connection.return_value = FakeConnCtx()

    async def fake_get_async_pool():
        return mock_pool

    with patch.object(main_module.db, "get_async_pool", fake_get_async_pool):
        client = TestClient(main_module.app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_api_health_endpoint_db_error():
    from fastapi.testclient import TestClient

    from backend.app.api.main import app

    with patch("backend.app.api.main.db.get_async_connection") as mock_ctx:
        mock_ctx.side_effect = Exception("connection refused")
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 503
        assert "degraded" in response.text


def test_db_stats_endpoint():
    from fastapi.testclient import TestClient

    from backend.app.api import main as main_module

    with patch.object(main_module.db, "get_pool_stats", return_value={"async": {"size": 2}, "sync": None}):
        client = TestClient(main_module.app)
        response = client.get("/api/v1/db/stats")
        assert response.status_code == 200
        assert response.json()["async"]["size"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# db.py sync pool utilities
# ─────────────────────────────────────────────────────────────────────────────


def test_get_connection_with_valid_conn():
    from backend.app.api.db import get_connection

    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_pool.getconn.return_value = mock_conn

    with patch("backend.app.api.db.get_sync_pool", return_value=mock_pool):
        conn = get_connection()
        assert conn is mock_conn


def test_get_connection_invalid_then_valid():
    from backend.app.api.db import get_connection

    mock_pool = MagicMock()
    bad_conn = MagicMock()
    bad_conn.closed = True
    good_conn = MagicMock()
    good_conn.closed = False
    mock_pool.getconn.side_effect = [bad_conn, good_conn]

    with patch("backend.app.api.db.get_sync_pool", return_value=mock_pool):
        conn = get_connection()
        assert conn is good_conn


def test_get_connection_all_invalid():
    import psycopg

    from backend.app.api.db import get_connection

    mock_pool = MagicMock()
    bad_conn = MagicMock()
    bad_conn.closed = True
    # Second getconn also returns closed -> should raise OperationalError
    mock_pool.getconn.side_effect = [bad_conn, bad_conn]

    with patch("backend.app.api.db.get_sync_pool", return_value=mock_pool):
        with pytest.raises(psycopg.OperationalError, match="Failed to obtain"):
            get_connection()


def test_get_connection_pool_timeout_retries():
    from psycopg_pool import PoolTimeout

    from backend.app.api.db import get_connection

    mock_pool = MagicMock()
    mock_pool.getconn.side_effect = PoolTimeout("timeout")

    with patch("backend.app.api.db.get_sync_pool", return_value=mock_pool), \
         patch("time.sleep"):
        with pytest.raises(PoolTimeout):
            get_connection()
        assert mock_pool.getconn.call_count == 3


def test_init_sync_pool_returns_existing():
    from backend.app.api.db import init_sync_pool

    fake_pool = MagicMock()
    with patch("backend.app.api.db._sync_pool", fake_pool):
        result = init_sync_pool()
        assert result is fake_pool


def test_get_sync_pool_initializes():
    from backend.app.api.db import get_sync_pool

    fake_pool = MagicMock()

    def fake_init():
        from backend.app.api import db
        db._sync_pool = fake_pool

    with patch("backend.app.api.db._sync_pool", None), \
         patch("backend.app.api.db.init_sync_pool", side_effect=fake_init):
        pool = get_sync_pool()
        assert pool is fake_pool


# ─────────────────────────────────────────────────────────────────────────────
# db.py async pool utilities
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_get_async_pool_initializes():
    from backend.app.api.db import get_async_pool

    fake_pool = MagicMock()

    def fake_init():
        from backend.app.api import db
        db._async_pool = fake_pool

    with patch("backend.app.api.db._async_pool", None), \
         patch("backend.app.api.db.init_async_pool", side_effect=fake_init):
        pool = await get_async_pool()
        assert pool is fake_pool


@pytest.mark.anyio
async def test_get_async_connection_success():
    from backend.app.api.db import get_async_connection

    fake_pool = MagicMock()
    fake_conn = MagicMock()

    # pool.connection() returns an async context manager
    class FakeCtx:
        async def __aenter__(self):
            return fake_conn
        async def __aexit__(self, *exc_info):
            return False

    fake_pool.connection.return_value = FakeCtx()

    with patch("backend.app.api.db.get_async_pool", return_value=fake_pool):
        async with get_async_connection() as conn:
            assert conn is fake_conn


@pytest.mark.anyio
async def test_get_async_connection_pool_timeout_retries():
    from psycopg_pool import PoolTimeout

    from backend.app.api.db import get_async_connection

    fake_pool = MagicMock()
    fake_pool.connection.side_effect = PoolTimeout("timeout")

    with patch("backend.app.api.db.get_async_pool", return_value=fake_pool), \
         patch("asyncio.sleep"):
        with pytest.raises(PoolTimeout):
            async with get_async_connection() as _:
                pass
        assert fake_pool.connection.call_count == 3


@pytest.mark.anyio
async def test_get_async_connection_psycopg_error():
    import psycopg

    from backend.app.api.db import get_async_connection

    fake_pool = MagicMock()
    fake_pool.connection.side_effect = psycopg.OperationalError("boom")

    with patch("backend.app.api.db.get_async_pool", return_value=fake_pool):
        with pytest.raises(psycopg.OperationalError, match="boom"):
            async with get_async_connection() as _:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# db.py query utilities (query_one / query_all / execute / insert_and_return)
# ─────────────────────────────────────────────────────────────────────────────


def test_db_query_one():
    from backend.app.api.db import query_one

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchone.return_value = {"id": 1, "name": "alice"}
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.db.get_connection", return_value=mock_conn), \
         patch("backend.app.api.db.release_connection") as mock_release:
        result = query_one("SELECT * FROM users WHERE id=%s", (1,))
        assert result == {"id": 1, "name": "alice"}
        mock_release.assert_called_once_with(mock_conn)


def test_db_query_all():
    from backend.app.api.db import query_all

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchall.return_value = [{"id": 1}, {"id": 2}]
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.db.get_connection", return_value=mock_conn), \
         patch("backend.app.api.db.release_connection") as mock_release:
        result = query_all("SELECT * FROM users")
        assert len(result) == 2
        mock_release.assert_called_once_with(mock_conn)


def test_db_execute_commit():
    from backend.app.api.db import execute

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.db.get_connection", return_value=mock_conn), \
         patch("backend.app.api.db.release_connection") as mock_release:
        execute("DELETE FROM users WHERE id=%s", (1,))
        mock_conn.commit.assert_called_once()
        mock_release.assert_called_once_with(mock_conn)


def test_db_execute_rollback_on_error():
    from backend.app.api.db import execute

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute.side_effect = Exception("boom")
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.db.get_connection", return_value=mock_conn), \
         patch("backend.app.api.db.release_connection"):
        with pytest.raises(Exception, match="boom"):
            execute("DELETE FROM users WHERE id=%s", (1,))
        mock_conn.rollback.assert_called_once()


def test_db_insert_and_return():
    from backend.app.api.db import insert_and_return

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchone.return_value = {"id": "42"}
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.db.get_connection", return_value=mock_conn), \
         patch("backend.app.api.db.release_connection"):
        result = insert_and_return("INSERT INTO users(name) VALUES (%s) RETURNING id", ("alice",), "id")
        assert result == "42"


def test_db_insert_and_return_no_result():
    from backend.app.api.db import insert_and_return

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchone.return_value = None
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.db.get_connection", return_value=mock_conn), \
         patch("backend.app.api.db.release_connection"):
        with pytest.raises(ValueError, match="No result returned"):
            insert_and_return("INSERT INTO users(name) VALUES (%s) RETURNING id", ("alice",), "id")
        mock_conn.rollback.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# db.py close_pools
# ─────────────────────────────────────────────────────────────────────────────


def test_close_pools_with_sync():
    from backend.app.api.db import close_pools

    mock_sync_pool = MagicMock()
    with patch("backend.app.api.db._async_pool", None), \
         patch("backend.app.api.db._sync_pool", mock_sync_pool):
        close_pools()
        mock_sync_pool.close.assert_called_once()


def test_close_pools_with_async_running_loop():
    from backend.app.api.db import close_pools

    mock_pool = MagicMock()
    mock_pool.close = AsyncMock()

    with patch("backend.app.api.db._async_pool", mock_pool), \
         patch("backend.app.api.db._sync_pool", None), \
         patch("asyncio.get_event_loop") as mock_loop:
        loop = MagicMock()
        loop.is_running.return_value = True
        mock_loop.return_value = loop
        close_pools()
        loop.create_task.assert_called_once()


def test_close_pools_async_timeout():
    from backend.app.api.db import close_pools

    mock_pool = MagicMock()
    mock_pool.close = MagicMock()

    with patch("backend.app.api.db._async_pool", mock_pool), \
         patch("backend.app.api.db._sync_pool", None), \
         patch("asyncio.get_event_loop") as mock_loop:
        loop = MagicMock()
        loop.is_running.return_value = True
        loop.create_task.side_effect = lambda c: MagicMock()
        mock_loop.return_value = loop
        # simulate timeout on wait_for
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            close_pools()
