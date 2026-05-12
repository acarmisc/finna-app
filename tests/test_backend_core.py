"""Unit tests for core backend modules: pagination, queries/base, db utilities, auth, errors."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Request, Response
from starlette.datastructures import Headers

os.environ["JWT_SECRET"] = "test-jwt-secret-key"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRATION_MINUTES"] = "30"

# ─────────────────────────────────────────────────────────────────────────────
# pagination.py
# ─────────────────────────────────────────────────────────────────────────────


def test_add_pagination_headers_first_page():
    from backend.app.api.pagination import add_pagination_headers

    response = Response()
    result = add_pagination_headers(response, total=100, limit=10, offset=0)
    assert result.headers["Link"] == '<?limit=10&offset=0>; rel="self", <?limit=10&offset=10>; rel="next"'
    assert result.headers["X-Total-Count"] == "100"
    assert result.headers["X-Page"] == "1"
    assert result.headers["X-Page-Count"] == "10"
    assert result.headers["X-Limit"] == "10"


def test_add_pagination_headers_last_page():
    from backend.app.api.pagination import add_pagination_headers

    response = Response()
    result = add_pagination_headers(response, total=100, limit=10, offset=90)
    assert result.headers["Link"] == '<?limit=10&offset=90>; rel="self", <?limit=10&offset=80>; rel="prev"'
    assert result.headers["X-Page"] == "10"
    assert result.headers["X-Page-Count"] == "10"


def test_add_pagination_headers_middle_page():
    from backend.app.api.pagination import add_pagination_headers

    response = Response()
    result = add_pagination_headers(response, total=100, limit=10, offset=50)
    assert '?limit=10&offset=50>; rel="self"' in result.headers["Link"]
    assert '?limit=10&offset=40>; rel="prev"' in result.headers["Link"]
    assert '?limit=10&offset=60>; rel="next"' in result.headers["Link"]


def test_add_pagination_headers_zero_total():
    from backend.app.api.pagination import add_pagination_headers

    response = Response()
    result = add_pagination_headers(response, total=0, limit=10, offset=0)
    assert result.headers["X-Page-Count"] == "1"
    assert result.headers["X-Page"] == "1"


def test_add_pagination_headers_limit_zero():
    from backend.app.api.pagination import add_pagination_headers

    response = Response()
    result = add_pagination_headers(response, total=100, limit=0, offset=0)
    assert result.headers["X-Page-Count"] == "1"
    assert result.headers["X-Page"] == "1"


def test_get_pagination_params_defaults():
    from backend.app.api.pagination import get_pagination_params

    request = MagicMock(spec=Request)
    request.query_params = {"limit": "20", "offset": "5"}
    limit, offset = get_pagination_params(request)
    assert limit == 20
    assert offset == 5


def test_get_pagination_params_max_limit():
    from backend.app.api.pagination import get_pagination_params

    request = MagicMock(spec=Request)
    request.query_params = {"limit": "500"}
    limit, offset = get_pagination_params(request, default_limit=50, max_limit=100)
    assert limit == 100
    assert offset == 0


def test_get_pagination_params_no_values():
    from backend.app.api.pagination import get_pagination_params

    request = MagicMock(spec=Request)
    request.query_params = {}
    limit, offset = get_pagination_params(request)
    assert limit == 50
    assert offset == 0


def test_paginate_response():
    from backend.app.api.pagination import paginate_response

    request = MagicMock(spec=Request)
    request.query_params = {"limit": "10", "offset": "20"}
    data = [{"id": 1}, {"id": 2}]
    result = paginate_response(data, total=100, request=request)
    assert result["data"] == data
    assert result["pagination"]["total"] == 100
    assert result["pagination"]["limit"] == 10
    assert result["pagination"]["offset"] == 20
    assert result["pagination"]["page"] == 3
    assert result["pagination"]["page_count"] == 10
    assert result["pagination"]["has_previous"] is True
    assert result["pagination"]["has_next"] is True


# ─────────────────────────────────────────────────────────────────────────────
# queries/base.py
# ─────────────────────────────────────────────────────────────────────────────


def test_query_one_returns_row():
    from backend.app.api.queries.base import query_one

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchone.return_value = {"id": 1, "name": "test"}
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.queries.base.get_connection", return_value=mock_conn), \
         patch("backend.app.api.queries.base.release_connection") as mock_release:
        result = query_one("SELECT * FROM foo WHERE id=%s", (1,))
        assert result == {"id": 1, "name": "test"}
        mock_release.assert_called_once_with(mock_conn)


def test_query_one_returns_none():
    from backend.app.api.queries.base import query_one

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchone.return_value = None
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.queries.base.get_connection", return_value=mock_conn), \
         patch("backend.app.api.queries.base.release_connection") as mock_release:
        result = query_one("SELECT * FROM foo WHERE id=%s", (1,))
        assert result is None


def test_query_one_json_parsing():
    from backend.app.api.queries.base import query_one

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchone.return_value = {"data": '{"key":"value"}', "plain": "text"}
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.queries.base.get_connection", return_value=mock_conn), \
         patch("backend.app.api.queries.base.release_connection"):
        result = query_one("SELECT * FROM foo")
        assert result["data"] == {"key": "value"}
        assert result["plain"] == "text"


def test_query_one_invalid_json_fallback():
    from backend.app.api.queries.base import query_one

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchone.return_value = {"data": '{"invalid}'}
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.queries.base.get_connection", return_value=mock_conn), \
         patch("backend.app.api.queries.base.release_connection"):
        result = query_one("SELECT * FROM foo")
        assert result["data"] == '{"invalid}'


def test_query_one_dict_param():
    from backend.app.api.queries.base import query_one

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchone.return_value = {"id": 1}
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.queries.base.get_connection", return_value=mock_conn), \
         patch("backend.app.api.queries.base.release_connection"):
        result = query_one("INSERT INTO foo(data) VALUES (%s)", ({"a": 1},))
        assert result == {"id": 1}
        # Verify json.dumps was used for dict param
        call_args = mock_cur.execute.call_args
        assert isinstance(call_args[0][1][0], str)


def test_query_all_returns_rows():
    from backend.app.api.queries.base import query_all

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchall.return_value = [{"id": 1}, {"id": 2}]
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.queries.base.get_connection", return_value=mock_conn), \
         patch("backend.app.api.queries.base.release_connection") as mock_release:
        result = query_all("SELECT * FROM foo")
        assert len(result) == 2
        mock_release.assert_called_once_with(mock_conn)


def test_query_all_empty():
    from backend.app.api.queries.base import query_all

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.queries.base.get_connection", return_value=mock_conn), \
         patch("backend.app.api.queries.base.release_connection"):
        result = query_all("SELECT * FROM foo")
        assert result == []


def test_execute_commit():
    from backend.app.api.queries.base import execute

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.queries.base.get_connection", return_value=mock_conn), \
         patch("backend.app.api.queries.base.release_connection"):
        execute("DELETE FROM foo WHERE id=%s", (1,))
        mock_conn.commit.assert_called_once()


def test_execute_rollback_on_error():
    from backend.app.api.queries.base import execute

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute.side_effect = Exception("Boom")
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.queries.base.get_connection", return_value=mock_conn), \
         patch("backend.app.api.queries.base.release_connection"):
        with pytest.raises(Exception, match="Boom"):
            execute("DELETE FROM foo WHERE id=%s", (1,))
        mock_conn.rollback.assert_called_once()


def test_insert_and_return_success():
    from backend.app.api.queries.base import insert_and_return

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchone.return_value = {"id": "42"}
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.queries.base.get_connection", return_value=mock_conn), \
         patch("backend.app.api.queries.base.release_connection"):
        result = insert_and_return("INSERT INTO foo(name) VALUES (%s) RETURNING id", ("bar",), returning="id")
        assert result == "42"
        mock_conn.commit.assert_called_once()


def test_insert_and_return_no_result():
    from backend.app.api.queries.base import insert_and_return

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchone.return_value = None
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.queries.base.get_connection", return_value=mock_conn), \
         patch("backend.app.api.queries.base.release_connection"):
        with pytest.raises(ValueError, match="No result returned"):
            insert_and_return("INSERT INTO foo(name) VALUES (%s) RETURNING id", ("bar",), returning="id")
        mock_conn.rollback.assert_called_once()


def test_insert_and_return_with_dict_param():
    from backend.app.api.queries.base import insert_and_return

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()
    mock_cur.fetchone.return_value = {"id": "99"}
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.app.api.queries.base.get_connection", return_value=mock_conn), \
         patch("backend.app.api.queries.base.release_connection"):
        result = insert_and_return("INSERT INTO foo(data) VALUES (%s) RETURNING id", ({"key": "val"},), returning="id")
        assert result == "99"


# ─────────────────────────────────────────────────────────────────────────────
# queries wrapper modules (thin wrappers around base)
# ─────────────────────────────────────────────────────────────────────────────


def test_alert_queries():
    from backend.app.api.queries import alert_queries

    with patch("backend.app.api.queries.alert_queries._query_all", return_value=[{"id": 1}]) as mock_all, \
         patch("backend.app.api.queries.alert_queries._query_one", return_value={"id": 2}) as mock_one:
        assert alert_queries.query_all_alerts("SELECT *") == [{"id": 1}]
        assert alert_queries.query_one_alert("SELECT *") == {"id": 2}
        mock_all.assert_called_once()
        mock_one.assert_called_once()


def test_auth_queries():
    from backend.app.api.queries import auth_queries

    with patch("backend.app.api.queries.auth_queries._query_one", return_value={"id": 1}) as mock_one, \
         patch("backend.app.api.queries.auth_queries._insert_and_return", return_value="42") as mock_insert:
        assert auth_queries.query_one_user("SELECT *", (1,)) == {"id": 1}
        assert auth_queries.insert_user_and_return("INSERT", ("a",), "id") == "42"


def test_config_queries():
    from backend.app.api.queries import config_queries

    with patch("backend.app.api.queries.config_queries._query_all", return_value=[{"id": 1}]), \
         patch("backend.app.api.queries.config_queries._query_one", return_value={"id": 2}), \
         patch("backend.app.api.queries.config_queries._execute"), \
         patch("backend.app.api.queries.config_queries._insert_and_return", return_value="99"):
        assert config_queries.query_all_configs("SELECT *") == [{"id": 1}]
        assert config_queries.query_one_config("SELECT *") == {"id": 2}
        config_queries.execute_config("DELETE")
        assert config_queries.insert_config_and_return("INSERT", ("a",), "id") == "99"


def test_cost_queries():
    from backend.app.api.queries import cost_queries

    with patch("backend.app.api.queries.cost_queries._query_all", return_value=[{"id": 1}]), \
         patch("backend.app.api.queries.cost_queries._query_one", return_value={"id": 2}):
        assert cost_queries.query_all_costs("SELECT *") == [{"id": 1}]
        assert cost_queries.query_one_cost("SELECT *") == {"id": 2}


def test_extractor_queries():
    from backend.app.api.queries import extractor_queries

    with patch("backend.app.api.queries.extractor_queries._query_all", return_value=[{"id": 1}]), \
         patch("backend.app.api.queries.extractor_queries._query_one", return_value={"id": 2}), \
         patch("backend.app.api.queries.extractor_queries._execute"), \
         patch("backend.app.api.queries.extractor_queries._insert_and_return", return_value="88"):
        assert extractor_queries.query_all_extractors("SELECT *") == [{"id": 1}]
        assert extractor_queries.query_one_extractor("SELECT *") == {"id": 2}
        extractor_queries.execute_extractor("DELETE")
        assert extractor_queries.insert_extractor_and_return("INSERT", ("a",), "id") == "88"


# ─────────────────────────────────────────────────────────────────────────────
# db.py utilities
# ─────────────────────────────────────────────────────────────────────────────


def test_get_pg_dsn():
    from backend.app.api.db import get_pg_dsn

    os.environ["PG_DSN"] = "postgres://user:pass@host/db"
    assert get_pg_dsn() == "postgres://user:pass@host/db"

    del os.environ["PG_DSN"]
    with pytest.raises(ValueError, match="PG_DSN"):
        get_pg_dsn()
    os.environ["PG_DSN"] = "postgresql://test:***@localhost/testdb"


def test_get_pool_config():
    from backend.app.api.db import get_pool_config

    os.environ["POOL_MIN_CONNS"] = "5"
    os.environ["POOL_MAX_CONNS"] = "20"
    config = get_pool_config()
    assert config == {"min_size": 5, "max_size": 20}


def test_get_pool_stats_empty():
    from backend.app.api.db import get_pool_stats

    stats = get_pool_stats()
    assert stats == {"async": None, "sync": None}


def test_close_pools():
    from backend.app.api.db import close_pools, _async_pool, _sync_pool

    # Ensure pools are None before test
    with patch("backend.app.api.db._async_pool", None), \
         patch("backend.app.api.db._sync_pool", None):
        close_pools()
        assert True  # No exception


def test_release_connection_with_pool():
    from backend.app.api.db import release_connection

    mock_pool = MagicMock()
    mock_pool.putconn = MagicMock()
    mock_conn = MagicMock()

    with patch("backend.app.api.db._sync_pool", mock_pool):
        release_connection(mock_conn)
        mock_pool.putconn.assert_called_once_with(mock_conn)


def test_release_connection_putconn_error():
    from backend.app.api.db import release_connection

    mock_pool = MagicMock()
    mock_pool.putconn.side_effect = Exception("pool closed")
    mock_conn = MagicMock()

    with patch("backend.app.api.db._sync_pool", mock_pool):
        # Should not raise
        release_connection(mock_conn)
        mock_conn.close.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# auth.py
# ─────────────────────────────────────────────────────────────────────────────


def test_verify_password():
    from backend.app.api.auth import verify_password, get_password_hash

    hashed = get_password_hash("secret123")
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_access_token():
    from backend.app.api.auth import create_access_token

    token = create_access_token({"sub": "user1"})
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_with_expiry():
    from backend.app.api.auth import create_access_token

    token = create_access_token({"sub": "user1"}, expires_delta=timedelta(minutes=5))
    assert isinstance(token, str)


def test_decode_token_valid():
    from backend.app.api.auth import create_access_token, decode_token

    token = create_access_token({"sub": "user1"})
    payload = decode_token(token)
    assert payload["sub"] == "user1"


def test_decode_token_invalid():
    from backend.app.api.auth import decode_token

    with pytest.raises(HTTPException) as exc_info:
        decode_token("not.a.valid.token")
    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED


def test_get_current_user_success():
    from backend.app.api.auth import get_current_user, create_access_token
    import asyncio

    token = create_access_token({"sub": "alice"})

    async def check():
        user = await get_current_user(token)
        assert user["username"] == "alice"

    asyncio.run(check())


def test_get_current_user_missing_sub():
    from backend.app.api.auth import get_current_user, create_access_token
    import asyncio

    token = create_access_token({"no_sub": "alice"})

    async def check():
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token)
        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED

    asyncio.run(check())


def _fake_httpx_client(response: MagicMock):
    """Build a fake httpx.AsyncClient that returns the given response."""

    class FakeClient:
        def __init__(self, response):
            self._response = response
        async def __aenter__(self):
            return self
        async def __aexit__(self, *exc_info):
            pass
        async def get(self, *args, **kwargs):
            return self._response
        async def post(self, *args, **kwargs):
            return self._response

    return FakeClient(response)


def test_get_github_redirect_url():
    from backend.app.api import auth as auth_module
    with patch.object(auth_module, "GITHUB_CLIENT_ID", "gh_client_id"):
        url = auth_module.get_github_redirect_url()
        assert url is not None
        assert "github.com/login/oauth/authorize" in url
        assert "client_id=gh_client_id" in url


def test_get_github_redirect_url_no_client_id():
    from backend.app.api import auth as auth_module
    with patch.object(auth_module, "GITHUB_CLIENT_ID", ""):
        url = auth_module.get_github_redirect_url()
        assert url is None


@pytest.mark.anyio
async def test_exchange_github_code_success():
    from backend.app.api import auth as auth_module

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "gh_token_123"}

    with patch.object(auth_module, "GITHUB_CLIENT_ID", "id"), \
         patch.object(auth_module, "GITHUB_CLIENT_SECRET", "secret"), \
         patch("httpx.AsyncClient", return_value=_fake_httpx_client(mock_response)):
        result = await auth_module.exchange_github_code("code123")
        assert result == {"access_token": "gh_token_123"}


@pytest.mark.anyio
async def test_exchange_github_code_failure():
    from backend.app.api import auth as auth_module

    mock_response = MagicMock()
    mock_response.status_code = 400

    with patch.object(auth_module, "GITHUB_CLIENT_ID", "id"), \
         patch.object(auth_module, "GITHUB_CLIENT_SECRET", "secret"), \
         patch("httpx.AsyncClient", return_value=_fake_httpx_client(mock_response)):
        result = await auth_module.exchange_github_code("bad_code")
        assert result is None


@pytest.mark.anyio
async def test_exchange_github_code_no_credentials():
    from backend.app.api import auth as auth_module

    with patch.object(auth_module, "GITHUB_CLIENT_ID", ""), \
         patch.object(auth_module, "GITHUB_CLIENT_SECRET", ""):
        result = await auth_module.exchange_github_code("code")
        assert result is None


@pytest.mark.anyio
async def test_get_github_user_success():
    from backend.app.api import auth as auth_module

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"login": "alice"}

    with patch("httpx.AsyncClient", return_value=_fake_httpx_client(mock_response)):
        result = await auth_module.get_github_user("token")
        assert result == {"login": "alice"}


@pytest.mark.anyio
async def test_get_github_user_failure():
    from backend.app.api import auth as auth_module

    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("httpx.AsyncClient", return_value=_fake_httpx_client(mock_response)):
        result = await auth_module.get_github_user("bad_token")
        assert result is None


@pytest.mark.anyio
async def test_get_github_user_emails_success():
    from backend.app.api import auth as auth_module

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"email": "a@b.com", "primary": True}]

    with patch("httpx.AsyncClient", return_value=_fake_httpx_client(mock_response)):
        result = await auth_module.get_github_user_emails("token")
        assert result == [{"email": "a@b.com", "primary": True}]


@pytest.mark.anyio
async def test_get_github_user_emails_failure():
    from backend.app.api import auth as auth_module

    mock_response = MagicMock()
    mock_response.status_code = 403

    with patch("httpx.AsyncClient", return_value=_fake_httpx_client(mock_response)):
        result = await auth_module.get_github_user_emails("token")
        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# errors.py
# ─────────────────────────────────────────────────────────────────────────────


def test_api_error_attributes():
    from backend.app.api.errors import APIError, NotFoundError, ForbiddenError, UnauthorizedError, ValidationError, RateLimitError

    exc = APIError(500, "internal", "boom")
    assert exc.status_code == 500
    assert exc.error == "internal"
    assert exc.message == "boom"
    assert exc.detail == {}

    exc2 = NotFoundError("User", "42")
    assert exc2.status_code == 404
    assert "42" in exc2.message

    exc3 = ForbiddenError("Nope")
    assert exc3.status_code == 403

    exc4 = UnauthorizedError()
    assert exc4.status_code == 401

    exc5 = ValidationError("bad input", {"field": "required"})
    assert exc5.detail == {"field": "required"}

    exc6 = RateLimitError(120)
    assert exc6.status_code == 429
    assert exc6.detail == {"retry_after": 120}


@pytest.mark.anyio
async def test_error_handler():
    from backend.app.api.errors import error_handler, APIError
    from fastapi import Request

    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    request.method = "GET"

    exc = APIError(400, "bad_request", "Invalid parameter")
    response = await error_handler(request, exc)
    assert response.status_code == 400
    body = response.body.decode()
    assert "bad_request" in body


@pytest.mark.anyio
async def test_validation_exception_handler():
    from backend.app.api.errors import validation_exception_handler
    from fastapi import Request

    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    request.method = "POST"

    exc = Exception("validation failed")
    response = await validation_exception_handler(request, exc)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_http_exception_handler():
    from backend.app.api.errors import http_exception_handler
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from fastapi import Request

    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    request.method = "GET"

    exc = StarletteHTTPException(status_code=403, detail="Forbidden")
    response = await http_exception_handler(request, exc)
    assert response.status_code == 403


@pytest.mark.anyio
async def test_generic_exception_handler():
    from backend.app.api.errors import generic_exception_handler
    from fastapi import Request

    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    request.method = "GET"

    exc = RuntimeError("something bad")
    response = await generic_exception_handler(request, exc)
    assert response.status_code == 500


def test_register_error_handlers():
    from backend.app.api.errors import register_error_handlers
    from fastapi import FastAPI

    app = FastAPI()
    register_error_handlers(app)
    # FastAPI doesn't expose a direct list, but calling it twice should not fail
    register_error_handlers(app)
    assert True


# ─────────────────────────────────────────────────────────────────────────────
# queries/__init__.py
# ─────────────────────────────────────────────────────────────────────────────


def test_queries_init_imports():
    from backend.app.api.queries import (
        query_all,
        query_one,
        execute,
        insert_and_return,
        query_all_costs,
        query_one_cost,
        query_all_configs,
        query_one_config,
        execute_config,
        insert_config_and_return,
        query_all_alerts,
        query_one_alert,
        query_one_user,
        insert_user_and_return,
        query_all_extractors,
        query_one_extractor,
        execute_extractor,
        insert_extractor_and_return,
    )
    assert callable(query_all)
    assert callable(query_one)
    assert callable(execute)
    assert callable(insert_and_return)
    assert callable(query_all_costs)
    assert callable(query_one_cost)
    assert callable(query_all_configs)
    assert callable(query_one_config)
    assert callable(execute_config)
    assert callable(insert_config_and_return)
    assert callable(query_all_alerts)
    assert callable(query_one_alert)
    assert callable(query_one_user)
    assert callable(insert_user_and_return)
    assert callable(query_all_extractors)
    assert callable(query_one_extractor)
    assert callable(execute_extractor)
    assert callable(insert_extractor_and_return)
