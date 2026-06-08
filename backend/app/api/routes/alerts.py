"""Alert management endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import auth as auth_module
from ..db import query_all, query_one
from .openapi_extensions import ERROR_RESPONSE_404, ERROR_RESPONSE_422, PaginationHeadersSchema

require_auth = auth_module.require_auth
get_current_user = auth_module.get_current_user

router = APIRouter()

# Add OpenAPI response documentation
_alert_responses = {
    200: {"description": "Alerts retrieved", "headers": PaginationHeadersSchema},
    404: ERROR_RESPONSE_404,
    422: ERROR_RESPONSE_422,
}

@router.get("/alerts", dependencies=[Depends(require_auth)], responses=_alert_responses)  # type: ignore[arg-type]
async def list_alerts(
    status: str | None = Query(None, description="Filter by status: firing, resolved, all"),
    severity: str | None = Query(None, description="Filter by severity: err, warn, ok"),
    limit: int = Query(50, le=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
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
    data = []
    for r in rows:
        data.append({
            "id": r.get("id"),
            "status": r.get("status") or "firing",
            "severity": r.get("severity") or "warning",
            "description": r.get("description") or r.get("body") or r.get("title") or "",
            "rule": r.get("rule") or "",
            "project": r.get("project") or "",
            "triggered_at": r["triggered_at"].isoformat() if r.get("triggered_at") else None,
            "cost_impact": float(r.get("cost_impact") or 0.0),
            "resource": r.get("resource") or "",
            "service": r.get("service") or "",
            "provider": r.get("provider") or "",
            "is_acknowledged": r.get("acknowledged_at") is not None,
            "first_seen": r["created_at"].isoformat() if r.get("created_at") else None,
            "last_seen": (
                r["updated_at"].isoformat()
                if r.get("updated_at")
                else (r["created_at"].isoformat() if r.get("created_at") else None)
            ),
        })
    total = len(data)
    return {
        "alerts": data,
        "count": total,
        # CLI-compatibility wrapper
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": total > page * page_size,
        "has_prev": page > 1,
    }


@router.get("/alerts/stats", dependencies=[Depends(require_auth)])
async def get_alert_stats() -> dict[str, Any]:
    """Get alert statistics."""
    sql = """
    SELECT status, severity, COUNT(*) as count
    FROM alerts
    GROUP BY status, severity
    """
    rows = query_all(sql)
    by_status: dict[str, int] = {"firing": 0, "ack": 0, "resolved": 0}
    by_severity: dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
    total = 0
    for r in rows:
        count = int(r["count"] or 0)
        total += count
        sev = r["severity"] or "warning"
        status_val = r["status"] or "firing"
        by_status[status_val] = by_status.get(status_val, 0) + count
        by_severity[sev] = by_severity.get(sev, 0) + count
    return {
        "total": total,
        "by_status": by_status,
        "by_severity": by_severity,
        "stats": rows,
    }


@router.get("/alerts/active", dependencies=[Depends(require_auth)])
async def get_active_alerts(
    user: dict[str, Any] = Depends(require_auth),  # noqa: B008
) -> dict[str, Any]:
    """Get active firing alerts."""
    sql = """
    SELECT * FROM alerts
    WHERE status = 'firing' AND acknowledged_at IS NULL
    ORDER BY created_at DESC
    """
    rows = query_all(sql)
    data = []
    for r in rows:
        data.append({
            "id": r.get("id"),
            "status": r.get("status") or "firing",
            "severity": r.get("severity") or "warning",
            "description": r.get("description") or r.get("body") or r.get("title") or "",
            "rule": r.get("rule") or "",
            "project": r.get("project") or "",
            "triggered_at": r["triggered_at"].isoformat() if r.get("triggered_at") else None,
            "cost_impact": float(r.get("cost_impact") or 0.0),
            "resource": r.get("resource") or "",
            "service": r.get("service") or "",
            "provider": r.get("provider") or "",
            "is_acknowledged": r.get("acknowledged_at") is not None,
            "first_seen": r["created_at"].isoformat() if r.get("created_at") else None,
            "last_seen": (
                r["updated_at"].isoformat()
                if r.get("updated_at")
                else (r["created_at"].isoformat() if r.get("created_at") else None)
            ),
        })
    return {"alerts": data, "count": len(data)}


@router.post("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_auth)])
async def acknowledge_alert(
    alert_id: str,
    user: dict[str, Any] = Depends(require_auth),  # noqa: B008
) -> dict[str, Any]:
    """Acknowledge a single alert."""
    sql = """
    UPDATE alerts
    SET status = 'ack', acknowledged_at = now(), acknowledged_by = %s
    WHERE id = %s AND acknowledged_at IS NULL
    RETURNING id
    """
    row = query_one(sql, (user.get("username", "unknown"), alert_id))
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")
    return {"id": alert_id, "acknowledged": True}


@router.post("/alerts/acknowledge-all", dependencies=[Depends(require_auth)])
async def acknowledge_all_alerts(
    user: dict[str, Any] = Depends(require_auth),  # noqa: B008
) -> dict[str, Any]:
    """Bulk acknowledge all firing alerts."""
    sql = """
    UPDATE alerts
    SET status = 'ack', acknowledged_at = now(), acknowledged_by = %s
    WHERE status = 'firing' AND acknowledged_at IS NULL
    RETURNING id
    """
    rows = query_all(sql, (user.get("username", "unknown"),))
    return {"acknowledged_count": len(rows), "ids": [r["id"] for r in rows]}
