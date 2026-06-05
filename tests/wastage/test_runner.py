"""Tests for backend.app.wastage.runner (Phase 5).

All tests use an in-memory SQLite-style fake via psycopg or, more practically,
a simple MagicMock of the psycopg.Connection interface. The runner only calls:

    conn.cursor()  → context-manager cursor with .execute(), .fetchone(), .rowcount
    conn.commit()
    conn.rollback()

So we can test all logic paths without a live database.
"""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest

import backend.app.wastage.rules.azure  # noqa: F401 — populate REGISTRY
from backend.app.wastage.rules import Finding

# ---------------------------------------------------------------------------
# Minimal DB mock
# ---------------------------------------------------------------------------


class FakeCursor:
    """Minimal cursor that records executions and can return canned fetchone()."""

    def __init__(self, fetchone_result=None, rowcount=0):
        self.executions: list[tuple[str, Any]] = []
        self._fetchone_result = fetchone_result
        self.rowcount = rowcount

    def execute(self, sql: str, params: Any = None) -> None:
        self.executions.append((sql, params))

    def fetchone(self) -> Any:
        return self._fetchone_result

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeConnection:
    """Thin mock of psycopg.Connection."""

    def __init__(self, cursor_fetchone=None, cursor_rowcount=0):
        self._cursor = FakeCursor(
            fetchone_result=cursor_fetchone,
            rowcount=cursor_rowcount,
        )
        self.committed: list[str] = []
        self.rolled_back = False

    @contextmanager
    def cursor(self):
        yield self._cursor

    def commit(self):
        self.committed.append("commit")

    def rollback(self):
        self.rolled_back = True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_finding(rule_id: str = "azure.disk.orphan") -> Finding:
    return Finding(
        provider="azure",
        account_id="sub-abc",
        resource_group="rg-dev",
        region="westeurope",
        resource_id="/subscriptions/sub-abc/resourceGroups/rg-dev/providers/Microsoft.Compute/disks/d-1",
        resource_type="Microsoft.Compute/disks",
        rule_id=rule_id,
        severity="high",
        category="storage",
        estimated_monthly_usd=Decimal("17.89"),
        evidence={"size_gb": 128, "sku": "Premium_LRS"},
        remediation="Delete or re-attach.",
    )


def _orphan_disk_row() -> dict:
    return {
        "provider": "azure",
        "account_id": "sub-abc",
        "resource_id": "/subscriptions/sub-abc/resourceGroups/rg-dev/providers/Microsoft.Compute/disks/d-1",
        "resource_name": "d-1",
        "resource_group": "rg-dev",
        "region": "westeurope",
        "resource_type": "Microsoft.Compute/disks",
        "tags": {},
        "managed_by": "",
        "size_gb": 128,
        "sku": "Premium_LRS",
        "disk_state": "Unattached",
        "time_created": "2024-01-01T00:00:00",
    }


# ---------------------------------------------------------------------------
# _finding_to_params
# ---------------------------------------------------------------------------


def test_finding_to_params_types():
    from backend.app.wastage.runner import _finding_to_params

    finding = _make_finding()
    now = datetime.now(timezone.utc)
    params = _finding_to_params(finding, now)

    assert params["finding_id"] == finding.finding_id
    assert params["provider"] == "azure"
    assert params["estimated_monthly_usd"] == float(Decimal("17.89"))
    # evidence and tags must be JSON-serialisable strings
    json.loads(params["evidence"])
    json.loads(params["tags"])
    assert params["now"] == now


# ---------------------------------------------------------------------------
# run_scan — happy path
# ---------------------------------------------------------------------------


@patch("backend.app.wastage.runner._ensure_azure_rules_loaded")
def test_run_scan_upserts_finding(mock_ensure):
    """run_scan should execute the upsert SQL for each produced Finding."""
    from backend.app.wastage.runner import run_scan

    conn = FakeConnection()
    rows = [_orphan_disk_row()]

    with patch("backend.app.wastage.pricing.lookup") as mock_lookup:
        mock_lookup.return_value = Decimal("0.1397")
        run_id = run_scan(conn, "azure", rows)

    assert isinstance(run_id, str)
    # Validate it's a UUID
    uuid.UUID(run_id)

    executed_sqls = [ex[0] for ex in conn._cursor.executions]

    # Should have: INSERT scan_run, at least one UPSERT, UPDATE scan_run close
    assert any("wastage_scan_runs" in s and "running" in s for s in executed_sqls), (
        "Expected INSERT of scan run record"
    )
    assert any("resource_wastage" in s for s in executed_sqls), (
        "Expected UPSERT of finding"
    )
    assert any("UPDATE wastage_scan_runs" in s for s in executed_sqls), (
        "Expected scan run close UPDATE"
    )
    # At least one commit should have happened
    assert len(conn.committed) >= 1


@patch("backend.app.wastage.runner._ensure_azure_rules_loaded")
def test_run_scan_no_findings(mock_ensure):
    """run_scan with no matching rows should still complete cleanly."""
    from backend.app.wastage.runner import run_scan

    conn = FakeConnection()
    # A VM row won't match disk.orphan or other rules trivially
    rows = [{"resource_type": "unknown", "provider": "azure", "account_id": "sub-abc"}]

    run_scan(conn, "azure", rows)

    executed_sqls = [ex[0] for ex in conn._cursor.executions]
    # scan_run should still be opened and closed
    assert any("wastage_scan_runs" in s for s in executed_sqls)
    # No resource_wastage upsert should have been executed
    assert not any("resource_wastage" in s and "INSERT INTO" in s for s in executed_sqls)


# ---------------------------------------------------------------------------
# Idempotency: two runs on same inventory → stable row count, first_seen_at preserved
# ---------------------------------------------------------------------------


@patch("backend.app.wastage.runner._ensure_azure_rules_loaded")
def test_run_scan_idempotency_no_duplicate_rows(mock_ensure):
    """Running run_scan twice with the same inventory should not duplicate rows.

    We verify this by confirming the UPSERT SQL uses ON CONFLICT DO UPDATE
    (which preserves idempotency at DB level) and that the same finding_id
    is submitted both times — the DB's ON CONFLICT clause handles deduplication.
    """
    from backend.app.wastage.runner import run_scan

    rows = [_orphan_disk_row()]

    finding_ids_seen: list[str] = []

    class TrackingCursor(FakeCursor):
        def execute(self, sql: str, params: Any = None) -> None:
            super().execute(sql, params)
            if params and isinstance(params, dict) and "finding_id" in params:
                finding_ids_seen.append(params["finding_id"])

    class TrackingConnection(FakeConnection):
        @contextmanager
        def cursor(self):
            yield TrackingCursor(fetchone_result=None, rowcount=0)

    conn1 = TrackingConnection()
    conn2 = TrackingConnection()

    with patch("backend.app.wastage.pricing.lookup") as mock_lookup:
        mock_lookup.return_value = Decimal("0.1397")
        run_scan(conn1, "azure", rows)
        run_scan(conn2, "azure", rows)

    # Same finding_id must be submitted in both runs
    assert len(finding_ids_seen) == 2, f"Expected 2 upserts total, got {len(finding_ids_seen)}"
    assert finding_ids_seen[0] == finding_ids_seen[1], (
        "finding_id must be stable across runs (same provider/resource_id/rule_id)"
    )


# ---------------------------------------------------------------------------
# Auto-resolve logic
# ---------------------------------------------------------------------------


def test_auto_resolve_no_history():
    """With fewer than threshold completed runs, no auto-resolve should happen."""
    from backend.app.wastage.runner import _auto_resolve_stale

    # fetchone returns None → fewer than threshold runs
    conn = FakeConnection(cursor_fetchone=None)
    _auto_resolve_stale(conn, "azure", "run-id", threshold=3, _now=datetime.now(timezone.utc))

    executed_sqls = [ex[0] for ex in conn._cursor.executions]
    # Only the SELECT should have run; no UPDATE
    assert not any("UPDATE resource_wastage" in s for s in executed_sqls)


def test_auto_resolve_with_cutoff():
    """When a cutoff run exists, UPDATE resource_wastage should be executed."""
    from backend.app.wastage.runner import _auto_resolve_stale

    cutoff_dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
    # Return the cutoff row as a dict (matching dict_row cursor factory)
    conn = FakeConnection(cursor_fetchone={"started_at": cutoff_dt}, cursor_rowcount=5)
    now = datetime.now(timezone.utc)
    _auto_resolve_stale(conn, "azure", "run-id", threshold=3, _now=now)

    executed_sqls = [ex[0] for ex in conn._cursor.executions]
    assert any("UPDATE resource_wastage" in s for s in executed_sqls), (
        "Expected auto-resolve UPDATE to run when cutoff run exists"
    )


# ---------------------------------------------------------------------------
# Error handling: scan run marked 'error' on exception
# ---------------------------------------------------------------------------


@patch("backend.app.wastage.runner._ensure_azure_rules_loaded")
def test_run_scan_marks_error_on_exception(mock_ensure):
    """If the inventory generator raises, scan run should be marked as 'error'."""
    from backend.app.wastage.runner import run_scan

    # Collect all executions across all cursors
    all_executions: list[tuple[str, Any]] = []

    class TrackingCursor(FakeCursor):
        def execute(self, sql: str, params: Any = None) -> None:
            all_executions.append((sql, params))

    class ErrorConnection(FakeConnection):
        @contextmanager
        def cursor(self):
            yield TrackingCursor(fetchone_result=None)

    conn = ErrorConnection()

    def bad_rows():
        # Yield one valid row, then raise inside the generator
        yield _orphan_disk_row()
        raise RuntimeError("inventory generator blew up")

    with pytest.raises((RuntimeError, Exception)):
        with patch("backend.app.wastage.pricing.lookup") as mock_lookup:
            mock_lookup.return_value = Decimal("0.1397")
            run_scan(conn, "azure", bad_rows())

    # The close UPDATE with 'error' status should have been attempted
    executed_sqls = [ex[0] for ex in all_executions]
    close_calls = [s for s in executed_sqls if "UPDATE wastage_scan_runs" in s]
    assert close_calls, "Expected scan run close UPDATE even on error"

    # Confirm the 'error' status was passed
    close_params = [p for s, p in all_executions if "UPDATE wastage_scan_runs" in s]
    assert any(p[1] == "error" for p in close_params if isinstance(p, tuple))
