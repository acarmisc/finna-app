"""Pytest fixtures for API integration tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent / "backend" / "app"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

os.environ["TESTING"] = "1"
os.environ["PG_DSN"] = "postgresql://test:***@localhost/testdb"
os.environ["POOL_MIN_CONNS"] = "1"
os.environ["POOL_MAX_CONNS"] = "5"
os.environ["ENCRYPTION_KEY"] = "fd7Em6qcDLS1FfjAgi0oSc6-keC5uK8r8rshY_UVw5I="
os.environ["JWT_SECRET"] = "test-secret-key"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRATION_MINUTES"] = "60"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.api.auth import create_access_token  # noqa: E402


@pytest.fixture
def client():
    """Create test client with TESTING env bypassing DB middleware."""
    from backend.app.api import main as main_module

    with TestClient(main_module.app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def auth_client(client):
    """Create test client that auto-injects auth headers."""
    token = create_access_token(data={"sub": "testuser"})
    auth_headers = {"Authorization": f"Bearer {token}"}

    original_request = client.request

    def patched_request(method, url, **kwargs):
        headers = kwargs.get("headers") or {}
        headers.update(auth_headers)
        kwargs["headers"] = headers
        return original_request(method, url, **kwargs)

    client.request = lambda m, u, **kw: patched_request(m, u, **kw)
    yield client
    client.request = original_request
