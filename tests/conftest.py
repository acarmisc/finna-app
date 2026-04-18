"""Pytest fixtures for API integration tests."""

import os

os.environ["PG_DSN"] = "postgresql://test:test@localhost/testdb"
os.environ["POOL_MIN_CONNS"] = "1"
os.environ["POOL_MAX_CONNS"] = "5"
os.environ["ENCRYPTION_KEY"] = "fd7Em6qcDLS1FfjAgi0oSc6-keC5uK8r8rshY_UVw5I="
os.environ["JWT_SECRET"] = "test-secret-key"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRATION_MINUTES"] = "60"

from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


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


@pytest.fixture
def client(mock_connection, mock_sync_pool):
    """Create test client with mocked dependencies."""
    import api.db as db_module
    import api.main as main_module

    original_lifespan = main_module.app.router.lifespan_context

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    main_module.app.router.lifespan_context = noop_lifespan

    try:
        with patch.object(db_module, "get_connection", return_value=mock_connection):
            with patch.object(db_module, "release_connection"):
                with patch.object(db_module, "query_one", return_value=None):
                    with patch.object(db_module, "query_all", return_value=[]):
                        with patch.object(db_module, "execute"):
                            with patch.object(db_module, "insert_and_return", return_value="test-id"):
                                with TestClient(main_module.app, raise_server_exceptions=False) as test_client:
                                    yield test_client
    finally:
        main_module.app.router.lifespan_context = original_lifespan


@pytest.fixture
def auth_client(mock_connection, mock_sync_pool):
    """Create test client with mocked dependencies and authentication."""
    import api.db as db_module
    import api.main as main_module

    original_lifespan = main_module.app.router.lifespan_context

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    main_module.app.router.lifespan_context = noop_lifespan

    try:
        with patch.object(db_module, "get_connection", return_value=mock_connection):
            with patch.object(db_module, "release_connection"):
                with patch.object(db_module, "query_one", return_value=None):
                    with patch.object(db_module, "query_all", return_value=[]):
                        with patch.object(db_module, "execute"):
                            with patch.object(db_module, "insert_and_return", return_value="test-id"):
                                from api.auth import create_access_token
                                token = create_access_token(data={"sub": "testuser"})
                                auth_headers = {"Authorization": f"Bearer {token}"}

                                def patched_request(method, url, **kwargs):
                                    headers = kwargs.get("headers") or {}
                                    headers.update(auth_headers)
                                    kwargs["headers"] = headers
                                    return original_request(method, url, **kwargs)

                                with TestClient(main_module.app, raise_server_exceptions=False) as test_client:
                                    original_request = test_client.request
                                    test_client.request = lambda m, u, **kw: patched_request(m, u, **kw)
                                    yield test_client
    finally:
        main_module.app.router.lifespan_context = original_lifespan
