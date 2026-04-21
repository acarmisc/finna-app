"""Alert management endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from .. import auth as auth_module
require_auth = auth_module.require_auth
from ..db import query_all

router = APIRouter()


@router.get("/alerts", dependencies=[Depends(require_auth)])
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status: firing, resolved, all"),
    severity: Optional[str] = Query(None, description="Filter by severity: err, warn, ok"),
    limit: int = Query(50, le=100),
) -> dict[str, Any]:
    """Get alerts with filtering."""
    sql = """
    SELECT * FROM alerts
    WHERE (%s::TEXT IS NULL OR status = %s)
      AND (%s::TEXT IS NULL OR severity = %s)
    ORDER BY created_at DESC
    LIMIT %s
    """
    rows = query_all(sql, (status, status, severity, severity, limit))
    return {"alerts": rows, "count": len(rows)}


@router.get("/alerts/stats", dependencies=[Depends(require_auth)])
async def get_alert_stats() -> dict[str, Any]:
    """Get alert statistics."""
    sql = """
    SELECT status, severity, COUNT(*) as count
    FROM alerts
    GROUP BY status, severity
    """
    rows = query_all(sql)
    return {"stats": rows}


@router.get("/alerts/active", dependencies=[Depends(require_auth)])
async def get_active_alerts() -> dict[str, Any]:
    """Get active firing alerts."""
    sql = """
    SELECT * FROM alerts
    WHERE status = 'firing'
    ORDER BY created_at DESC
    """
    rows = query_all(sql)
    return {"alerts": rows, "count": len(rows)}
