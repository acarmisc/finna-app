"""Extractor orchestration endpoints."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from api.auth import require_auth
from api.db import query_one, query_all
from api.models import (
    ExtractorRunRequest,
    ExtractorRunResponse,
    ExtractorStatusResponse,
)
from api.runner import cancel_run, get_run_status, list_runs, start_extractor

router = APIRouter()



from api.auth import require_auth
from api.db import query_one, query_all
from api.models import (
    ExtractorRunRequest,
    ExtractorRunResponse,
    ExtractorStatusResponse,
)
from api.runner import cancel_run, get_run_status, list_runs, start_extractor

router = APIRouter()


@router.post("/extractors/run", response_model=ExtractorRunResponse, dependencies=[Depends(require_auth)])
async def run_extractor(request: ExtractorRunRequest) -> dict[str, Any]:
    """Start an extractor run."""
    from api.db import get_connection
    from api.runner import _get_pg_dsn

    # Get config_id from request or find first config for provider
    config_id = request.config_id
    if not config_id:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM cloud_config WHERE provider = %s ORDER BY created_at DESC LIMIT 1",
                (request.provider.value,),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"No configuration found for provider {request.provider.value}",
            )
        config_id = row["id"]

    try:
        run_id = start_extractor(
            config_id=config_id,
            provider=request.provider.value,
            extractor_type=request.extractor_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "id": run_id,
        "config_id": config_id,
        "provider": request.provider.value,
        "extractor_type": request.extractor_type or f"{request.provider.value}_cost",
        "status": "running",
        "started_at": datetime.now(timezone.utc),
    }


@router.get("/extractors/status", response_model=list[ExtractorStatusResponse], dependencies=[Depends(require_auth)])
async def get_status(
    limit: int = 50, provider: Optional[str] = None
) -> list[dict[str, Any]]:
    """Get recent extractor runs."""
    runs = list_runs(limit=limit, provider=provider)
    return [
        {
            "id": r["id"],
            "provider": r["provider"],
            "extractor_type": r["extractor_type"],
            "status": r["status"],
            "started_at": r["started_at"],
            "finished_at": r.get("finished_at"),
            "records_extracted": r.get("records_extracted", 0),
            "error_message": r.get("error_message"),
        }
        for r in runs
    ]


@router.get("/extractors/status/{run_id}", response_model=ExtractorStatusResponse, dependencies=[Depends(require_auth)])
async def get_run_detail(run_id: str) -> dict[str, Any]:
    """Get detailed status of a run."""
    run = get_run_status(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "id": run["id"],
        "provider": run["provider"],
        "extractor_type": run["extractor_type"],
        "status": run["status"],
        "started_at": run["started_at"],
        "finished_at": run.get("finished_at"),
        "records_extracted": run.get("records_extracted", 0),
        "error_message": run.get("error_message"),
    }


@router.post("/extractors/cancel/{run_id}", dependencies=[Depends(require_auth)])
async def cancel_extractor(run_id: str) -> dict[str, str]:
    """Cancel a running extractor."""
    success = cancel_run(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found or already finished")
    return {"status": "cancelled", "run_id": run_id}


@router.get("/extractors/health", dependencies=[Depends(require_auth)])
async def get_extractor_health() -> list[dict[str, Any]]:
    """Get health status for all extractors."""
    from api.db import get_connection

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT extractor_name, status,
                   COALESCE(last_run_end, last_run_start) as last_run,
                   COALESCE(records_extracted, 0) as records_count
            FROM extractor_health
            ORDER BY extractor_name
            """
        )
        rows = cur.fetchall()

    return [
        {
            "name": r["extractor_name"],
            "status": r["status"],
            "last_run": r["last_run"],
            "records_count": r["records_count"],
        }
        for r in rows
    ]
