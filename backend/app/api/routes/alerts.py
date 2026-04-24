"""Alert management endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import auth as auth_module
require_auth = auth_module.require_auth
get_current_user = auth_module.get_current_user
from ..db import query_all, query_one

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
async def get_active_alerts(
    user: dict[str, Any] = Depends(require_auth),
) -> dict[str, Any]:
    """Get active firing alerts."""
    sql = """
    SELECT * FROM alerts
    WHERE status = 'firing' AND acknowledged_at IS NULL
    ORDER BY created_at DESC
    """
    rows = query_all(sql)
    return {"alerts": rows, "count": len(rows)}


@router.post("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_auth)])
async def acknowledge_alert(
    alert_id: str,
    user: dict[str, Any] = Depends(require_auth),
) -> dict[str, Any]:
    """Acknowledge a single alert."""
    sql = """
    UPDATE alerts
    SET acknowledged_at = now(), acknowledged_by = %s
    WHERE id = %s AND acknowledged_at IS NULL
    RETURNING id
    """
    row = query_one(sql, (user.get("username", "unknown"), alert_id))
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")
    return {"id": alert_id, "acknowledged": True}


@router.post("/alerts/acknowledge-all", dependencies=[Depends(require_auth)])
async def acknowledge_all_alerts(
    user: dict[str, Any] = Depends(require_auth),
) -> dict[str, Any]:
    """Bulk acknowledge all firing alerts."""
    sql = """
    UPDATE alerts
    SET acknowledged_at = now(), acknowledged_by = %s
    WHERE status = 'firing' AND acknowledged_at IS NULL
    RETURNING id
    """
    rows = query_all(sql, (user.get("username", "unknown"),))
    return {"acknowledged_count": len(rows), "ids": [r["id"] for r in rows]}
