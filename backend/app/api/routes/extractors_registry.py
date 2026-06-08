"""Extractor registry CRUD + trigger endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from .. import auth as auth_module

require_auth = auth_module.require_auth
from ..db import execute, insert_and_return, query_all, query_one  # noqa: E402
from ..runner import cancel_run, get_run_status, list_runs, start_extractor  # noqa: E402

router = APIRouter()


# ─── Registry listing ─────────────────────────────────────────────────────────

@router.get("/extractors", dependencies=[Depends(require_auth)])
async def list_extractors(
    provider: str | None = None,
    limit: int = 50,
    page: int = 1,
    page_size: int = 50,
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
    total = len(rows)
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
                "last_run": r["updated_at"].isoformat() if r.get("updated_at") else None,
                "status": "idle",
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ],
        "count": total,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": total > page * page_size,
        "has_prev": page > 1,
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
    now = datetime.now(UTC)

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


# ─── Runs (moved from legacy extractors.py) ─────────────────────────────────────
# MUST be placed before /extractors/{extractor_id} to avoid path shadowing.

@router.get("/extractors/runs", dependencies=[Depends(require_auth)])
async def list_extractor_runs(
    limit: int = 50, provider: str | None = None
) -> dict[str, Any]:
    """List extractor runs."""
    runs = list_runs(limit=limit, provider=provider)
    return {"runs": runs, "count": len(runs)}


@router.get("/extractors/runs/{run_id}", dependencies=[Depends(require_auth)])
async def get_extractor_run(run_id: str) -> dict[str, Any]:
    """Get status of an extractor run."""
    run = get_run_status(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/extractors/runs/{run_id}/cancel", dependencies=[Depends(require_auth)])
async def cancel_extractor_run(run_id: str) -> dict[str, Any]:
    """Cancel an extractor run."""
    success = cancel_run(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found or already finished")
    return {"status": "cancelled"}


@router.get("/extractors/runs/{run_id}/logs", dependencies=[Depends(require_auth)])
async def get_extractor_run_logs(run_id: str) -> dict[str, Any]:
    """Get sanitized log output for an extractor run."""
    run = get_run_status(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    log_output = run.get("log_output") or ""
    return {"logs": log_output.splitlines() if log_output else []}


# ─── Legacy trigger (CLI compat; kept for frontend) ──────────────────────────

@router.post("/extractors/run", dependencies=[Depends(require_auth)])
async def run_extractor_via_post(data: dict[str, Any]) -> dict[str, Any]:
    """Run an extractor by config_id (legacy endpoint)."""
    provider = data.get("provider", "gcp")
    extractor_type = data.get("extractor_type", provider)
    config_id = data.get("config_id")

    if not config_id:
        raise HTTPException(status_code=400, detail="config_id is required")

    run_id = start_extractor(
        config_id=config_id,
        provider=provider,
        extractor_type=extractor_type,
    )
    return {"run_id": run_id, "status": "started"}


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
        "last_run": row["updated_at"].isoformat() if row.get("updated_at") else None,
        "status": "idle",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ─── Registry delete ──────────────────────────────────────────────────────────

@router.delete("/extractors/{extractor_id}", dependencies=[Depends(require_auth)], status_code=204)
async def delete_extractor(extractor_id: str) -> None:
    """Remove an extractor from the registry."""
    execute("DELETE FROM extractors_registry WHERE id = %s", (extractor_id,))

