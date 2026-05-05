"""Alert-specific database queries."""

from __future__ import annotations

from typing import Any

from .base import query_all as _query_all
from .base import query_one as _query_one


def query_all_alerts(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """Execute an alert query and return all results."""
    return _query_all(sql, params)


def query_one_alert(sql: str, params: tuple | None = None) -> dict[str, Any] | None:
    """Execute an alert query and return one result."""
    return _query_one(sql, params)
