"""Extractor registry endpoints - New CRUD operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

# Import auth module from parent package
from .. import auth as auth_module

require_auth = auth_module.require_auth  # noqa: E402

from ..models import (  # noqa: E402
    ExtractorCreate,
    ExtractorListResponse,
    ExtractorResponse,
    ExtractorRunTriggerRequest,
    ExtractorRunTriggerResponse,
    ExtractorUpdate,
)

router = APIRouter()


def _extractor_to_response(extractor: dict[str, Any]) -> ExtractorResponse:
    """Convert extractor dict to response schema."""
    return ExtractorResponse(
        id=extractor["id"],
        name=extractor["name"],
        provider=extractor["provider"],
        extractor_type=extractor["extractor_type"],
        enabled=extractor["enabled"],
        schedule=extractor.get("schedule"),
        config_id=extractor.get("config_id"),
        status=extractor.get("status", "idle"),
        last_run_id=extractor.get("last_run_id"),
        last_run_at=extractor.get("last_run_at"),
        created_at=extractor["created_at"],
        updated_at=extractor["updated_at"],
    )


@router.get("/extractors", response_model=ExtractorListResponse, dependencies=[Depends(require_auth)])
async def list_extractors(
    provider: str | None = None,
    enabled: bool | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """List extractors with optional filtering."""
    from ..db import query_all

    where_clauses: list[str] = []
    params: list[str | bool | int] = []

    if provider:
        where_clauses.append("provider = %s")
        params.append(provider)
    if enabled is not None:
        where_clauses.append("enabled = %s")
        params.append(enabled)

    where_clause = ""
    if where_clauses:
        where_clause = "WHERE " + " AND ".join(where_clauses)

    sql = f"""
        SELECT id, name, provider, extractor_type, enabled, schedule,
               config_id, status, last_run_id, last_run_at, created_at, updated_at
        FROM extractors
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s
    """

    extractors = query_all(sql, tuple(params) + (limit,))  # type: ignore[arg-type]

    return {
        "extractors": [_extractor_to_response(e) for e in extractors],
        "count": len(extractors),
    }


@router.get("/extractors/{extractor_id}", response_model=ExtractorResponse, dependencies=[Depends(require_auth)])
async def get_extractor(extractor_id: str) -> dict[str, Any]:
    """Get a single extractor by ID."""
    from ..db import query_one

    sql = """
        SELECT id, name, provider, extractor_type, enabled, schedule,
               config_id, status, last_run_id, last_run_at, created_at, updated_at
        FROM extractors
        WHERE id = %s
    """
    extractor = query_one(sql, (extractor_id,))

    if not extractor:
        raise HTTPException(status_code=404, detail=f"Extractor {extractor_id} not found")

    return extractor


@router.post("/extractors", response_model=ExtractorResponse, dependencies=[Depends(require_auth)])
async def create_extractor(data: ExtractorCreate) -> dict[str, Any]:
    """Create a new extractor."""
    from ..db import insert_and_return, query_one

    extractor_id = str(uuid.uuid4())[:12]  # Short ID

    # Validate config_id exists if provided
    if data.config_id:
        config = query_one("SELECT id FROM cloud_config WHERE id = %s", (data.config_id,))
        if not config:
            raise HTTPException(status_code=400, detail=f"Config {data.config_id} not found")

    now = datetime.now(timezone.utc)

    sql = """
        INSERT INTO extractors (
            id, name, provider, extractor_type, enabled, schedule, config_id, status, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, name, provider, extractor_type, enabled, schedule, config_id,
                  status, last_run_id, last_run_at, created_at, updated_at
    """

    result = insert_and_return(
        sql,
        (
            extractor_id,
            data.name,
            data.provider,
            data.extractor_type,
            data.enabled,
            data.schedule,
            data.config_id,
            "idle",
            now,
        ),
    )

    return result  # type: ignore[return-value]


@router.put("/extractors/{extractor_id}", response_model=ExtractorResponse, dependencies=[Depends(require_auth)])
async def update_extractor(extractor_id: str, data: ExtractorUpdate) -> dict[str, Any]:
    """Update an extractor."""
    from ..db import query_one

    extractor = query_one("SELECT * FROM extractors WHERE id = %s", (extractor_id,))
    if not extractor:
        raise HTTPException(status_code=404, detail=f"Extractor {extractor_id} not found")

    # Build update query dynamically
    updates: list[str] = []
    params: list[Any] = []

    if data.name is not None:
        updates.append("name = %s")
        params.append(data.name)
    if data.enabled is not None:
        updates.append("enabled = %s")
        params.append(data.enabled)
    if data.schedule is not None:
        updates.append("schedule = %s")
        params.append(data.schedule)
    if data.config_id is not None:
        # Validate config_id if provided
        if data.config_id:
            config = query_one("SELECT id FROM cloud_config WHERE id = %s", (data.config_id,))
            if not config:
                raise HTTPException(status_code=400, detail=f"Config {data.config_id} not found")
        updates.append("config_id = %s")
        params.append(data.config_id)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = now()")
    params.append(extractor_id)

    sql = f"""
        UPDATE extractors
        SET {", ".join(updates)}
        WHERE id = %s
        RETURNING id, name, provider, extractor_type, enabled, schedule, config_id,
                  status, last_run_id, last_run_at, created_at, updated_at
    """

    result = query_one(sql, tuple(params))
    return result  # type: ignore[return-value]


@router.delete("/extractors/{extractor_id}", status_code=204, dependencies=[Depends(require_auth)])
async def delete_extractor(extractor_id: str) -> None:
    """Delete an extractor."""
    from ..db import execute, query_one

    extractor = query_one("SELECT id FROM extractors WHERE id = %s", (extractor_id,))
    if not extractor:
        raise HTTPException(status_code=404, detail=f"Extractor {extractor_id} not found")

    execute("DELETE FROM extractors WHERE id = %s", (extractor_id,))


@router.post("/extractors/{extractor_id}/trigger", response_model=ExtractorRunTriggerResponse, dependencies=[Depends(require_auth)])  # noqa: E501
async def trigger_extractor_run(extractor_id: str, data: ExtractorRunTriggerRequest | None = None) -> dict[str, Any]:
    """Trigger a run for an extractor."""
    from ..db import query_one
    from ..runner import start_extractor

    extractor = query_one("SELECT * FROM extractors WHERE id = %s", (extractor_id,))
    if not extractor:
        raise HTTPException(status_code=404, detail=f"Extractor {extractor_id} not found")

    if not extractor["enabled"]:
        raise HTTPException(status_code=400, detail=f"Extractor {extractor_id} is disabled")

    # Use provided config_id or the extractor's config_id
    config_id = data.config_id if data and data.config_id else extractor["config_id"]

    if not config_id:
        raise HTTPException(
            status_code=400,
            detail=f"No config_id provided and extractor {extractor_id} has no default config_id",
        )

    # Start the extractor run
    run_id = start_extractor(
        config_id=config_id,
        provider=extractor["provider"],
        extractor_type=extractor["extractor_type"],
    )

    # Update last_run_id and last_run_at
    from ..db import execute
    execute(
        "UPDATE extractors SET last_run_id = %s, last_run_at = now(), status = 'running' WHERE id = %s",
        (run_id, extractor_id),
    )

    return {
        "run_id": run_id,
        "status": "started",
        "extractor_id": extractor_id,
    }
