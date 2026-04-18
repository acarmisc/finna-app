"""Pytest fixtures for API integration tests."""

import os

os.environ["PG_DSN"] = "postgresql://test:test@localhost/testdb"
os.environ["POOL_MIN_CONNS"] = "1"
os.environ["POOL_MAX_CONNS"] = "5"
os.environ["ENCRYPTION_KEY"] = "fd7Em6qcDLS1FfjAgi0oSc6-keC5uK8r8rshY_UVw5I="

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
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
    # We need to completely replace the app's lifespan function
    import api.main as main_module
    import api.db as db_module

    # Save original lifespan
    original_lifespan = main_module.app.router.lifespan_context

    # Create an async no-op lifespan
    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    # Replace it
    main_module.app.router.lifespan_context = noop_lifespan

    # Create client
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
        # Restore
        main_module.app.router.lifespan_context = original_lifespan
