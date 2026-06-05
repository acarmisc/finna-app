"""API tests for the /api/v1/wastage endpoints."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# --- path setup (mirror existing test pattern) ---
backend_path = Path(__file__).parent.parent.parent / "backend" / "app"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

os.environ["TESTING"] = "1"
os.environ.setdefault("PG_DSN", "postgresql://test:***@localhost/testdb")
os.environ.setdefault("POOL_MIN_CONNS", "1")
os.environ.setdefault("POOL_MAX_CONNS", "5")
os.environ.setdefault("ENCRYPTION_KEY", "fd7Em6qcDLS1FfjAgi0oSc6-keC5uK8r8rshY_UVw5I=")
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRATION_MINUTES", "60")

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.api.auth import create_access_token  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    from backend.app.api import main as main_module

    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def auth_client(client):  # type: ignore[redefined-outer-name]
    token = create_access_token(data={"sub": "testuser"})
    headers = {"Authorization": f"Bearer {token}"}
    original = client.request

    def patched(method, url, **kwargs):
        h = dict(kwargs.get("headers") or {})
        h.update(headers)
        kwargs["headers"] = h
        return original(method, url, **kwargs)

    client.request = lambda m, u, **kw: patched(m, u, **kw)
    yield client
    client.request = original


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW_ISO = datetime.now(timezone.utc).isoformat()

_MOCK_FINDING = {
    "finding_id": "abc123",
    "provider": "azure",
    "account_id": "sub-001",
    "resource_group": "rg-prod",
    "region": "westeurope",
    "resource_id": "/subscriptions/sub-001/resourceGroups/rg-prod/providers/Microsoft.Compute/disks/disk-orphan",
    "resource_type": "Microsoft.Compute/disks",
    "rule_id": "azure.disk.orphan",
    "severity": "high",
    "category": "storage",
    "estimated_monthly_usd": 45.0,
    "currency": "USD",
    "evidence": {"size_gb": 128, "sku": "Premium_LRS"},
    "first_seen_at": NOW_ISO,
    "last_seen_at": NOW_ISO,
    "status": "open",
    "tags": {},
}

_MOCK_FINDINGS = [_MOCK_FINDING]
_MOCK_SUMMARY = [
    {
        "category": "storage",
        "finding_count": 3,
        "total_monthly_usd": 135.0,
    }
]
_MOCK_SCANS = [
    {
        "id": "run-001",
        "provider": "azure",
        "started_at": NOW_ISO,
        "finished_at": NOW_ISO,
        "status": "done",
        "findings_count": 3,
        "error": None,
    }
]


# ---------------------------------------------------------------------------
# Authentication guard tests
# ---------------------------------------------------------------------------


class TestWastageAuth:
    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/wastage")
        assert resp.status_code == 401

    def test_summary_requires_auth(self, client):
        resp = client.get("/api/v1/wastage/summary")
        assert resp.status_code == 401

    def test_rules_requires_auth(self, client):
        resp = client.get("/api/v1/wastage/rules")
        assert resp.status_code == 401

    def test_scans_requires_auth(self, client):
        resp = client.get("/api/v1/wastage/scans")
        assert resp.status_code == 401

    def test_finding_detail_requires_auth(self, client):
        resp = client.get("/api/v1/wastage/abc123")
        assert resp.status_code == 401

    def test_ack_requires_auth(self, client):
        resp = client.post("/api/v1/wastage/abc123/ack")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestWastageListFindings:
    def test_list_returns_findings(self, auth_client):
        with (
            patch("backend.app.api.routes.wastage.list_wastage_findings", return_value=_MOCK_FINDINGS),
            patch("backend.app.api.routes.wastage.count_wastage_findings", return_value=1),
        ):
            resp = auth_client.get("/api/v1/wastage")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["total"] == 1
        assert data["data"][0]["finding_id"] == "abc123"

    def test_list_empty(self, auth_client):
        with (
            patch("backend.app.api.routes.wastage.list_wastage_findings", return_value=[]),
            patch("backend.app.api.routes.wastage.count_wastage_findings", return_value=0),
        ):
            resp = auth_client.get("/api/v1/wastage")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_filter_by_provider(self, auth_client):
        with (
            patch("backend.app.api.routes.wastage.list_wastage_findings", return_value=_MOCK_FINDINGS) as mock_list,
            patch("backend.app.api.routes.wastage.count_wastage_findings", return_value=1),
        ):
            resp = auth_client.get("/api/v1/wastage?provider=azure")
        assert resp.status_code == 200
        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs.get("provider") == "azure"

    def test_filter_by_severity(self, auth_client):
        with (
            patch("backend.app.api.routes.wastage.list_wastage_findings", return_value=[]) as mock_list,
            patch("backend.app.api.routes.wastage.count_wastage_findings", return_value=0),
        ):
            resp = auth_client.get("/api/v1/wastage?severity=high")
        assert resp.status_code == 200
        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs.get("severity") == "high"

    def test_filter_by_status(self, auth_client):
        with (
            patch("backend.app.api.routes.wastage.list_wastage_findings", return_value=[]) as mock_list,
            patch("backend.app.api.routes.wastage.count_wastage_findings", return_value=0),
        ):
            resp = auth_client.get("/api/v1/wastage?status=open")
        assert resp.status_code == 200
        assert mock_list.call_args.kwargs.get("status") == "open"

    def test_pagination_params(self, auth_client):
        with (
            patch("backend.app.api.routes.wastage.list_wastage_findings", return_value=[]) as mock_list,
            patch("backend.app.api.routes.wastage.count_wastage_findings", return_value=100),
        ):
            resp = auth_client.get("/api/v1/wastage?limit=10&offset=20")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 10
        assert data["offset"] == 20
        assert data["has_prev"] is True
        assert data["has_next"] is True
        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs.get("limit") == 10
        assert call_kwargs.get("offset") == 20


class TestWastageSummary:
    def test_summary_returns_categories(self, auth_client):
        with patch("backend.app.api.routes.wastage.get_wastage_summary", return_value=_MOCK_SUMMARY):
            resp = auth_client.get("/api/v1/wastage/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data
        assert "total_monthly_usd" in data
        assert data["total_monthly_usd"] == 135.0
        assert data["total_finding_count"] == 3
        assert data["categories"][0]["category"] == "storage"

    def test_summary_empty(self, auth_client):
        with patch("backend.app.api.routes.wastage.get_wastage_summary", return_value=[]):
            resp = auth_client.get("/api/v1/wastage/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_monthly_usd"] == 0.0
        assert data["categories"] == []


class TestWastageRules:
    def test_rules_returns_catalog(self, auth_client):
        from backend.app.wastage.rules import Rule

        mock_registry = {
            "azure.disk.orphan": Rule(
                id="azure.disk.orphan",
                severity="high",
                category="storage",
                description="Orphaned managed disk",
                fn=lambda row, pricing: None,
            ),
        }
        with patch("backend.app.wastage.rules.REGISTRY", mock_registry):
            resp = auth_client.get("/api/v1/wastage/rules")
        assert resp.status_code == 200
        data = resp.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)
        assert any(r["id"] == "azure.disk.orphan" for r in data["rules"])

    def test_rules_returns_200_even_if_registry_empty(self, auth_client):
        with patch("backend.app.wastage.rules.REGISTRY", {}):
            resp = auth_client.get("/api/v1/wastage/rules")
        assert resp.status_code == 200


class TestWastageFindingDetail:
    def test_get_finding_success(self, auth_client):
        with patch("backend.app.api.routes.wastage.get_wastage_finding", return_value=_MOCK_FINDING):
            resp = auth_client.get("/api/v1/wastage/abc123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["finding_id"] == "abc123"
        assert data["provider"] == "azure"

    def test_get_finding_not_found(self, auth_client):
        with patch("backend.app.api.routes.wastage.get_wastage_finding", return_value=None):
            resp = auth_client.get("/api/v1/wastage/nonexistent")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestWastageStatusActions:
    def test_ack_success(self, auth_client):
        with patch("backend.app.api.routes.wastage.set_finding_status", return_value=True):
            resp = auth_client.post("/api/v1/wastage/abc123/ack")
        assert resp.status_code == 200
        assert resp.json()["status"] == "acked"

    def test_ack_not_found(self, auth_client):
        with patch("backend.app.api.routes.wastage.set_finding_status", return_value=False):
            resp = auth_client.post("/api/v1/wastage/nonexistent/ack")
        assert resp.status_code == 404

    def test_resolve_success(self, auth_client):
        with patch("backend.app.api.routes.wastage.set_finding_status", return_value=True):
            resp = auth_client.post("/api/v1/wastage/abc123/resolve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    def test_ignore_with_reason(self, auth_client):
        with patch("backend.app.api.routes.wastage.set_finding_status", return_value=True):
            resp = auth_client.post(
                "/api/v1/wastage/abc123/ignore",
                json={"reason": "Not our resource"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "Not our resource"

    def test_ignore_not_found(self, auth_client):
        with patch("backend.app.api.routes.wastage.set_finding_status", return_value=False):
            resp = auth_client.post("/api/v1/wastage/nope/ignore", json={"reason": "test"})
        assert resp.status_code == 404


class TestWastageScans:
    def test_list_scans_success(self, auth_client):
        with patch("backend.app.api.routes.wastage.list_scan_runs", return_value=_MOCK_SCANS):
            resp = auth_client.get("/api/v1/wastage/scans")
        assert resp.status_code == 200
        data = resp.json()
        assert "scans" in data
        assert data["count"] == 1
        assert data["scans"][0]["id"] == "run-001"

    def test_list_scans_empty(self, auth_client):
        with patch("backend.app.api.routes.wastage.list_scan_runs", return_value=[]):
            resp = auth_client.get("/api/v1/wastage/scans")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestWastageScanTrigger:
    def test_scan_returns_503_if_runner_missing(self, auth_client):
        import backend.app.api.routes.wastage as _w

        orig = _w._RUNNER_AVAILABLE
        _w._RUNNER_AVAILABLE = False
        try:
            resp = auth_client.post("/api/v1/wastage/scan", json={"provider": "azure"})
        finally:
            _w._RUNNER_AVAILABLE = orig
        assert resp.status_code == 503

    def test_scan_succeeds_with_runner(self, auth_client):
        import types

        import backend.app.api.routes.wastage as _w

        mock_runner = types.SimpleNamespace(run_scan=lambda provider, run_id: None)
        orig_runner = _w._wastage_runner
        orig_avail = _w._RUNNER_AVAILABLE
        _w._wastage_runner = mock_runner
        _w._RUNNER_AVAILABLE = True
        try:
            with patch("backend.app.api.routes.wastage.create_scan_run", return_value="run-123"):
                resp = auth_client.post("/api/v1/wastage/scan", json={"provider": "azure"})
        finally:
            _w._wastage_runner = orig_runner
            _w._RUNNER_AVAILABLE = orig_avail
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["provider"] == "azure"
        assert "run_id" in data
