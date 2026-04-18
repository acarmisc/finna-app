"""Integration tests for /api/v1/extractors endpoints (run, status, health)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

SAMPLE_RUN = {
    "id": "run-001",
    "config_id": "cfg-001",
    "provider": "azure",
    "extractor_type": "azure_cost",
    "status": "running",
    "started_at": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    "finished_at": None,
    "records_extracted": 0,
    "error_message": None,
}

SAMPLE_RUN_COMPLETED = {
    "id": "run-002",
    "config_id": "cfg-001",
    "provider": "azure",
    "extractor_type": "azure_cost",
    "status": "success",
    "started_at": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    "finished_at": datetime(2026, 1, 1, 0, 5, 0, tzinfo=timezone.utc),
    "records_extracted": 26,
    "error_message": None,
}

SAMPLE_HEALTH = {
    "extractor_name": "azure",
    "status": "success",
    "last_run": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    "records_count": 26,
}


@pytest.fixture
def extractor_client():
    import api.db as db_module
    import api.main as main_module

    original_lifespan = main_module.app.router.lifespan_context

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    main_module.app.router.lifespan_context = noop_lifespan

    mock_connection = MagicMock()
    mock_connection.closed = False
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = {"id": "cfg-001"}
    cursor.fetchall.return_value = []
    mock_connection.cursor.return_value = cursor
    mock_connection.commit = MagicMock()
    mock_connection.rollback = MagicMock()

    from api.auth import create_access_token

    token = create_access_token(data={"sub": "testuser"})

    try:
        with patch.object(db_module, "get_connection", return_value=mock_connection):
            with patch.object(db_module, "release_connection"):
                with patch.object(db_module, "query_one", return_value=None):
                    with patch.object(db_module, "query_all", return_value=[]):
                        with patch.object(db_module, "execute"):
                            with patch.object(db_module, "insert_and_return", return_value="run-001"):
                                with TestClient(main_module.app, raise_server_exceptions=False) as client:
                                    client._auth_token = token
                                    client._mock_connection = mock_connection
                                    yield client
    finally:
        main_module.app.router.lifespan_context = original_lifespan


def _auth_headers(client):
    return {"Authorization": f"Bearer {client._auth_token}"}


class TestExtractorAuth:
    def test_run_returns_401_without_token(self, extractor_client):
        resp = extractor_client.post(
            "/api/v1/extractors/run",
            json={
                "provider": "azure",
            },
        )
        assert resp.status_code == 401

    def test_status_returns_401_without_token(self, extractor_client):
        resp = extractor_client.get("/api/v1/extractors/status")
        assert resp.status_code == 401

    def test_health_returns_401_without_token(self, extractor_client):
        resp = extractor_client.get("/api/v1/extractors/health")
        assert resp.status_code == 401

    def test_cancel_returns_401_without_token(self, extractor_client):
        resp = extractor_client.post("/api/v1/extractors/cancel/run-001")
        assert resp.status_code == 401


class TestExtractorRun:
    @patch("api.db.get_connection")
    @patch("api.routes.extractors.start_extractor", return_value="run-001")
    def test_run_extractor_success(self, mock_start, mock_conn, extractor_client):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": "cfg-001"}
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value = mock_connection

        resp = extractor_client.post(
            "/api/v1/extractors/run",
            json={"provider": "azure", "config_id": "cfg-001"},
            headers=_auth_headers(extractor_client),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert data["provider"] == "azure"

    @patch("api.db.get_connection")
    @patch("api.routes.extractors.start_extractor", side_effect=ValueError("Config not found"))
    def test_run_extractor_config_not_found(self, mock_start, mock_conn, extractor_client):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value = mock_connection

        resp = extractor_client.post(
            "/api/v1/extractors/run",
            json={"provider": "azure"},
            headers=_auth_headers(extractor_client),
        )
        assert resp.status_code in (404, 500)


class TestExtractorStatus:
    def test_get_status_list(self, extractor_client):
        with patch("api.routes.extractors.list_runs", return_value=[SAMPLE_RUN, SAMPLE_RUN_COMPLETED]):
            resp = extractor_client.get(
                "/api/v1/extractors/status",
                headers=_auth_headers(extractor_client),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["status"] == "running"
            assert data[1]["status"] == "success"
            assert data[1]["records_extracted"] == 26

    def test_get_status_with_provider_filter(self, extractor_client):
        with patch("api.routes.extractors.list_runs", return_value=[SAMPLE_RUN]):
            resp = extractor_client.get(
                "/api/v1/extractors/status?provider=azure",
                headers=_auth_headers(extractor_client),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1

    def test_get_run_detail(self, extractor_client):
        with patch("api.routes.extractors.get_run_status", return_value=SAMPLE_RUN_COMPLETED):
            resp = extractor_client.get(
                "/api/v1/extractors/status/run-002",
                headers=_auth_headers(extractor_client),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == "run-002"
            assert data["status"] == "success"
            assert data["records_extracted"] == 26

    def test_get_run_detail_not_found(self, extractor_client):
        with patch("api.routes.extractors.get_run_status", return_value=None):
            resp = extractor_client.get(
                "/api/v1/extractors/status/nonexistent",
                headers=_auth_headers(extractor_client),
            )
            assert resp.status_code == 404


class TestExtractorCancel:
    def test_cancel_running_extractor(self, extractor_client):
        with patch("api.routes.extractors.cancel_run", return_value=True):
            resp = extractor_client.post(
                "/api/v1/extractors/cancel/run-001",
                headers=_auth_headers(extractor_client),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "cancelled"

    def test_cancel_finished_extractor(self, extractor_client):
        with patch("api.routes.extractors.cancel_run", return_value=False):
            resp = extractor_client.post(
                "/api/v1/extractors/cancel/run-002",
                headers=_auth_headers(extractor_client),
            )
            assert resp.status_code == 404


class TestExtractorHealth:
    def test_get_health(self, extractor_client):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "extractor_name": "azure",
                "status": "success",
                "last_run": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                "records_count": 26,
            },
        ]
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("api.db.get_connection", return_value=mock_connection):
            resp = extractor_client.get(
                "/api/v1/extractors/health",
                headers=_auth_headers(extractor_client),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["name"] == "azure"
            assert data[0]["status"] == "success"
            assert data[0]["records_count"] == 26

    def test_get_health_empty(self, extractor_client):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("api.db.get_connection", return_value=mock_connection):
            resp = extractor_client.get(
                "/api/v1/extractors/health",
                headers=_auth_headers(extractor_client),
            )
            assert resp.status_code == 200
            assert resp.json() == []
