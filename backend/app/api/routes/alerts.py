"""Alert management endpoints."""

from __future__ import annotations

from typing import Any, Optional

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
    status: Optional[str] = Query(None, description="Filter by status: firing, resolved, all"),
    severity: Optional[str] = Query(None, description="Filter by severity: err, warn, ok"),
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
    # Map to CLI Alert schema
    data = []
    for r in rows:
        data.append({
            "id": r.get("id"),
            "title": r.get("title") or r.get("type") or "Alert",
            "description": r.get("body") or r.get("description") or "",
            "severity": r.get("severity") or "warn",
            "resource": r.get("resource") or "",
            "service": r.get("service") or "",
            "provider": r.get("provider") or "",
            "cost_impact": float(r.get("cost_impact") or 0.0),
            "first_seen": (r.get("created_at").isoformat()) if r.get("created_at") else None,  # type: ignore[union-attr]
            "last_seen": (
                r.get("updated_at").isoformat()  # type: ignore[union-attr]
                if r.get("updated_at")
                else (r.get("created_at").isoformat() if r.get("created_at") else None)  # type: ignore[union-attr]
            ),
            "is_acknowledged": r.get("acknowledged_at") is not None,
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
    by_severity: dict[str, int] = {}
    by_provider: dict[str, int] = {}
    total = 0
    acknowledged = 0
    for r in rows:
        count = int(r["count"] or 0)
        total += count
        sev = r["severity"] or "unknown"
        by_severity[sev] = by_severity.get(sev, 0) + count
        # provider field not in alerts; use severity as proxy for by_provider
        by_provider[sev] = by_provider.get(sev, 0) + count
        if r["status"] == "resolved":
            acknowledged += count
    return {
        "total": total,
        "by_severity": by_severity,
        "by_provider": by_provider,
        "acknowledged": acknowledged,
        "pending": total - acknowledged,
        "stats": rows,
    }


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
    data = []
    for r in rows:
        data.append({
            "id": r.get("id"),
            "title": r.get("title") or r.get("type") or "Alert",
            "description": r.get("body") or r.get("description") or "",
            "severity": r.get("severity") or "warn",
            "resource": r.get("resource") or "",
            "service": r.get("service") or "",
            "provider": r.get("provider") or "",
            "cost_impact": float(r.get("cost_impact") or 0.0),
            "first_seen": (r.get("created_at").isoformat()) if r.get("created_at") else None,  # type: ignore[union-attr]
            "last_seen": (
                r.get("updated_at").isoformat()  # type: ignore[union-attr]
                if r.get("updated_at")
                else (r.get("created_at").isoformat() if r.get("created_at") else None)  # type: ignore[union-attr]
            ),
            "is_acknowledged": r.get("acknowledged_at") is not None,
        })
    return {"alerts": data, "count": len(data)}


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
