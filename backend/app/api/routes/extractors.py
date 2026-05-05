"""Extractor orchestration endpoints."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

# Import auth module from parent package
from .. import auth as auth_module

require_auth = auth_module.require_auth  # noqa: E402

from ..runner import cancel_run, get_run_status, list_runs, start_extractor  # noqa: E402

router = APIRouter()


# Keep existing extractors/run endpoints for backward compatibility
@router.get("/extractors/status", dependencies=[Depends(require_auth)])
async def list_extractor_runs(
    limit: int = 50, provider: Optional[str] = None
) -> dict[str, Any]:
    """List extractor runs (legacy endpoint)."""
    runs = list_runs(limit=limit, provider=provider)
    return {"runs": runs, "count": len(runs)}


@router.get("/extractors/runs", dependencies=[Depends(require_auth)])
async def list_extractor_runs_alias(
    limit: int = 50, provider: Optional[str] = None
) -> dict[str, Any]:
    """Alias for /extractors/status (CLI compatibility)."""
    runs = list_runs(limit=limit, provider=provider)
    return {"runs": runs, "count": len(runs)}


@router.post("/extractors/run", dependencies=[Depends(require_auth)])
async def run_extractor_via_post(data: dict[str, Any]) -> dict[str, Any]:
    """Run an extractor (legacy endpoint)."""
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


@router.get("/extractors/run/{run_id}", dependencies=[Depends(require_auth)])
async def get_extractor_run(run_id: str) -> dict[str, Any]:
    """Get status of an extractor run."""
    run = get_run_status(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/extractors/run/{run_id}/cancel", dependencies=[Depends(require_auth)])
async def cancel_extractor_run(run_id: str) -> dict[str, Any]:
    """Cancel an extractor run."""
    success = cancel_run(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found or already finished")
    return {"status": "cancelled"}
