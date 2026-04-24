"""Extractor registry CRUD + trigger endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from .. import auth as auth_module

require_auth = auth_module.require_auth
from ..db import execute, insert_and_return, query_all, query_one
from ..runner import start_extractor

router = APIRouter()


# ─── Registry listing ─────────────────────────────────────────────────────────

@router.get("/extractors", dependencies=[Depends(require_auth)])
async def list_extractors(
    provider: Optional[str] = None,
    limit: int = 50,
) -> dict[str, Any]:
    """List extractor registry entries."""
    sql = """
    SELECT e.id, e.name, e.provider, e.config_id, e.enabled,
           e.schedule, e.created_at, e.updated_at,
           c.name AS config_name
    FROM extractors_registry e
    LEFT JOIN cloud_config c ON c.id = e.config_id
    WHERE (%s::TEXT IS NULL OR e.provider = %s)
    ORDER BY e.provider, e.name
    LIMIT %s
    """
    rows = query_all(sql, (provider, provider, limit))
    return {
        "data": [
            {
                "id": r["id"],
                "name": r["name"],
                "provider": r["provider"],
                "config_id": r["config_id"],
                "config_name": r["config_name"],
                "enabled": r["enabled"],
                "schedule": r["schedule"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ],
        "count": len(rows),
    }


# ─── Registry create ──────────────────────────────────────────────────────────

@router.post("/extractors", dependencies=[Depends(require_auth)], status_code=201)
async def create_extractor(data: dict[str, Any]) -> dict[str, Any]:
    """Register a new extractor."""
    name = data.get("name", "")
    provider = data.get("provider", "")
    config_id = data.get("config_id")
    enabled = data.get("enabled", True)
    schedule = data.get("schedule", "0 0 * * *")

    if not name or not provider:
        raise HTTPException(status_code=400, detail="name and provider are required")

    eid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    sql = """
    INSERT INTO extractors_registry (id, name, provider, config_id, enabled, schedule, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    insert_and_return(sql, (eid, name, provider, config_id, enabled, schedule, now, now))
    return {
        "id": eid,
        "name": name,
        "provider": provider,
        "config_id": config_id,
        "enabled": enabled,
        "schedule": schedule,
        "created_at": now,
        "updated_at": now,
    }


# ─── Registry get ─────────────────────────────────────────────────────────────

@router.get("/extractors/{extractor_id}", dependencies=[Depends(require_auth)])
async def get_extractor(extractor_id: str) -> dict[str, Any]:
    """Get a single extractor registry entry."""
    sql = """
    SELECT e.id, e.name, e.provider, e.config_id, e.enabled,
           e.schedule, e.created_at, e.updated_at,
           c.name AS config_name
    FROM extractors_registry e
    LEFT JOIN cloud_config c ON c.id = e.config_id
    WHERE e.id = %s
    """
    row = query_one(sql, (extractor_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Extractor not found")
    return {
        "id": row["id"],
        "name": row["name"],
        "provider": row["provider"],
        "config_id": row["config_id"],
        "config_name": row["config_name"],
        "enabled": row["enabled"],
        "schedule": row["schedule"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ─── Registry delete ──────────────────────────────────────────────────────────

@router.delete("/extractors/{extractor_id}", dependencies=[Depends(require_auth)], status_code=204)
async def delete_extractor(extractor_id: str) -> None:
    """Remove an extractor from the registry."""
    execute("DELETE FROM extractors_registry WHERE id = %s", (extractor_id,))


# ─── Trigger (delegates to runner) ────────────────────────────────────────────

@router.post("/extractors/{extractor_id}/trigger", dependencies=[Depends(require_auth)])
async def trigger_extractor(extractor_id: str) -> dict[str, Any]:
    """Trigger a run for the given extractor registry entry."""
    row = query_one(
        "SELECT config_id, provider FROM extractors_registry WHERE id = %s",
        (extractor_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Extractor not found")

    config_id = row["config_id"]
    provider = row["provider"]
    if not config_id:
        raise HTTPException(status_code=400, detail="Extractor has no linked config")

    run_id = start_extractor(
        config_id=config_id,
        provider=provider,
        extractor_type=provider,
    )
    return {"run_id": run_id, "status": "started"}
