"""Pytest fixtures for API integration tests."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

backend_path = Path(__file__).parent.parent / "backend" / "app"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

os.environ["PG_DSN"] = "postgresql://test:***@localhost/testdb"
os.environ["POOL_MIN_CONNS"] = "1"
os.environ["POOL_MAX_CONNS"] = "5"
os.environ["ENCRYPTION_KEY"] = "fd7Em6qcDLS1FfjAgi0oSc6-keC5uK8r8rshY_UVw5I="
os.environ["JWT_SECRET"] = "test-secret-key"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRATION_MINUTES"] = "60"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def mock_sync_pool():
    """Mock sync connection pool."""
    mock = MagicMock()
    mock.min_size = 2
    mock.max_size = 10
    mock.__len__ = lambda self: 5
    return mock


@pytest.fixture
def mock_connection():
    """Mock database connection."""
    mock = MagicMock()
    mock.closed = False

    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []
    mock.cursor.return_value = cursor

    mock.commit = MagicMock()
    mock.rollback = MagicMock()

    return mock


def _make_mock_async_pool():
    """Create a mock async pool whose connection() returns an async context manager."""
    mock_conn = MagicMock()
    mock_pool = MagicMock()

    async_conn_cm = AsyncMock()
    async_conn_cm.__aenter__.return_value = mock_conn
    async_conn_cm.__aexit__.return_value = False
    mock_pool.connection.return_value = async_conn_cm

    return mock_pool, mock_conn


@pytest.fixture
def client(mock_connection, mock_sync_pool):
    """Create test client with mocked dependencies."""
    from backend.app.api import db as db_module
    from backend.app.api import main as main_module

    original_lifespan = main_module.app.router.lifespan_context
    original_async_pool = db_module._async_pool
    original_sync_pool = db_module._sync_pool

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    main_module.app.router.lifespan_context = noop_lifespan

    mock_pool, mock_conn = _make_mock_async_pool()
    db_module._async_pool = mock_pool
    db_module._sync_pool = mock_sync_pool

    try:
        with TestClient(main_module.app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        main_module.app.router.lifespan_context = original_lifespan
        db_module._async_pool = original_async_pool
        db_module._sync_pool = original_sync_pool


@pytest.fixture
def auth_client(mock_connection, mock_sync_pool):
    """Create test client with mocked dependencies and authentication."""
    from backend.app.api import db as db_module
    from backend.app.api import main as main_module
    from backend.app.api.auth import create_access_token

    original_lifespan = main_module.app.router.lifespan_context
    original_async_pool = db_module._async_pool
    original_sync_pool = db_module._sync_pool

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    main_module.app.router.lifespan_context = noop_lifespan

    mock_pool, mock_conn = _make_mock_async_pool()
    db_module._async_pool = mock_pool
    db_module._sync_pool = mock_sync_pool

    try:
        token = create_access_token(data={"sub": "testuser"})
        auth_headers = {"Authorization": f"Bearer {token}"}

        with TestClient(main_module.app, raise_server_exceptions=False) as test_client:
            original_request = test_client.request

            def patched_request(method, url, **kwargs):
                headers = kwargs.get("headers") or {}
                headers.update(auth_headers)
                kwargs["headers"] = headers
                return original_request(method, url, **kwargs)

            test_client.request = lambda m, u, **kw: patched_request(m, u, **kw)
            yield test_client
    finally:
        main_module.app.router.lifespan_context = original_lifespan
        db_module._async_pool = original_async_pool
        db_module._sync_pool = original_sync_pool
