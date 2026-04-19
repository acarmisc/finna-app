"""Alert management endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from api.auth import require_auth
from api.db import query_all

router = APIRouter()


@router.get("/alerts", dependencies=[Depends(require_auth)])
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status: firing, resolved, all"),
    severity: Optional[str] = Query(None, description="Filter by severity: err, warn, ok"),
    limit: int = Query(50, le=100),
) -> dict[str, Any]:
    """Get alerts with optional filtering."""
    conditions = []
    params = []
    
    # Get alert status from database
    sql = """
        SELECT 
            id,
            title,
            severity,
            body,
            rule,
            firing_at,
            resolved_at,
            channels,
            status
        FROM alerts
        ORDER BY firing_at DESC NULLS LAST
        LIMIT %s
    """
    
    results = query_all(sql, (limit,))
    
    alerts = []
    for row in results:
        firing = None
        if row["firing_at"]:
            if isinstance(row["firing_at"], datetime):
                firing = row["firing_at"].isoformat()
            else:
                firing = row["firing_at"]
        
        alerts.append({
            "id": row["id"],
            "severity": row["severity"],
            "title": row["title"],
            "body": row["body"],
            "rule": row["rule"],
            "firing": firing,
            "channels": row["channels"] or [],
        })
    
    firing_count = sum(1 for a in alerts if a["severity"] != "ok")
    
    return {
        "alerts": alerts,
        "firingCount": firing_count,
        "total": len(alerts),
    }


@router.get("/alerts/stats", dependencies=[Depends(require_auth)])
async def get_alert_stats() -> dict[str, Any]:
    """Get alert statistics."""
    sql = """
        SELECT 
            severity,
            COUNT(*) as count,
            SUM(CASE WHEN firing_at IS NOT NULL THEN 1 ELSE 0 END) as firing
        FROM alerts
        GROUP BY severity
    """
    
    results = query_all(sql)
    
    stats = {"err": 0, "warn": 0, "ok": 0}
    for row in results:
        stats[row["severity"]] = {
            "total": row["count"],
            "firing": row["firing"],
        }
    
    return {"stats": stats}


@router.get("/alerts/active", dependencies=[Depends(require_auth)])
async def get_active_alerts() -> list[dict[str, Any]]:
    """Get currently firing alerts."""
    sql = """
        SELECT 
            id,
            title,
            severity,
            body,
            rule,
            firing_at,
            channels
        FROM alerts
        WHERE firing_at IS NOT NULL
        ORDER BY firing_at DESC
        LIMIT 20
    """
    
    results = query_all(sql)
    
    return [
        {
            "id": row["id"],
            "severity": row["severity"],
            "title": row["title"],
            "body": row["body"],
            "rule": row["rule"],
            "firing": row["firing_at"].isoformat() if row["firing_at"] else None,
            "channels": row["channels"] or [],
        }
        for row in results
    ]


@router.get("/alerts/health", dependencies=[Depends(require_auth)])
async def get_extractor_health() -> dict[str, Any]:
    """Get extractor health status (for alert rules)."""
    sql = """
        SELECT 
            extractor_name,
            status,
            last_run_start,
            last_run_end,
            records_extracted,
            error_count
        FROM extractor_health
        ORDER BY extractor_name
    """
    
    results = query_all(sql)
    
    health = []
    for row in results:
        last_run = None
        if row["last_run_end"]:
            if isinstance(row["last_run_end"], datetime):
                last_run = row["last_run_end"].isoformat()
            else:
                last_run = row["last_run_end"]
        
        health.append({
            "name": row["extractor_name"],
            "status": row["status"],
            "lastRun": last_run,
            "recordsCount": row["records_extracted"],
            "errorCount": row["error_count"],
        })
    
    return {"health": health, "total": len(health)}
