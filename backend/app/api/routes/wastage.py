"""Resource wastage endpoints."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from .. import auth as auth_module
from ..pagination import add_pagination_headers, get_pagination_params
from ..queries.wastage_queries import (
    count_wastage_findings,
    create_scan_run,
    get_wastage_finding,
    get_wastage_summary,
    list_scan_runs,
    list_wastage_findings,
    set_finding_status,
    update_scan_run,
)
from .openapi_extensions import ERROR_RESPONSE_404, ERROR_RESPONSE_422

require_auth = auth_module.require_auth

router = APIRouter()

# ---------------------------------------------------------------------------
# Guarded import of runner (Agent B lands backend/app/wastage/runner.py)
# ---------------------------------------------------------------------------

try:
    from backend.app.wastage import runner as _wastage_runner  # type: ignore[import]

    _RUNNER_AVAILABLE = True
except ImportError:  # pragma: no cover
    _wastage_runner = None  # type: ignore[assignment]
    _RUNNER_AVAILABLE = False

# ---------------------------------------------------------------------------
# Request / response helpers
# ---------------------------------------------------------------------------


class IgnoreBody(BaseModel):
    reason: str = ""


class ScanBody(BaseModel):
    provider: str


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _serialize_finding(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a DB row to a JSON-safe dict."""
    out = dict(row)
    for ts_field in ("first_seen_at", "last_seen_at"):
        if out.get(ts_field) and hasattr(out[ts_field], "isoformat"):
            out[ts_field] = out[ts_field].isoformat()
    if out.get("estimated_monthly_usd") is not None:
        out["estimated_monthly_usd"] = float(out["estimated_monthly_usd"])
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/wastage",
    dependencies=[Depends(require_auth)],
    responses={200: {"description": "Findings list"}, 422: ERROR_RESPONSE_422},
)
async def list_findings(
    request: Request,
    provider: Optional[str] = Query(None, description="Filter by cloud provider"),
    severity: Optional[str] = Query(None, description="critical | high | medium | low | info"),
    rule_id: Optional[str] = Query(None, description="Filter by rule ID"),
    status: Optional[str] = Query(None, description="open | acked | resolved | ignored"),
    account_id: Optional[str] = Query(None, description="Filter by cloud account/subscription ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """List wastage findings with optional filters and offset-based pagination."""
    rows = list_wastage_findings(
        provider=provider,
        severity=severity,
        rule_id=rule_id,
        status=status,
        account_id=account_id,
        limit=limit,
        offset=offset,
    )
    total = count_wastage_findings(
        provider=provider,
        severity=severity,
        rule_id=rule_id,
        status=status,
        account_id=account_id,
    )
    data = [_serialize_finding(r) for r in rows]
    return {
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_next": offset + limit < total,
        "has_prev": offset > 0,
    }


@router.get(
    "/wastage/summary",
    dependencies=[Depends(require_auth)],
)
async def wastage_summary() -> dict[str, Any]:
    """Return findings grouped by category with summed estimated monthly savings."""
    rows = get_wastage_summary()
    categories = []
    total_usd = 0.0
    total_count = 0
    for r in rows:
        monthly = float(r.get("total_monthly_usd") or 0)
        count = int(r.get("finding_count") or 0)
        categories.append(
            {
                "category": r["category"],
                "finding_count": count,
                "total_monthly_usd": monthly,
            }
        )
        total_usd += monthly
        total_count += count
    return {
        "categories": categories,
        "total_monthly_usd": total_usd,
        "total_finding_count": total_count,
    }


@router.get(
    "/wastage/rules",
    dependencies=[Depends(require_auth)],
)
async def list_rules() -> dict[str, Any]:
    """Return the registered rule catalog."""
    try:
        from backend.app.wastage.rules import REGISTRY  # type: ignore[import]

        rules = [
            {
                "id": r.id,
                "severity": r.severity,
                "category": r.category,
                "description": r.description,
            }
            for r in REGISTRY.values()
        ]
    except ImportError:  # pragma: no cover
        rules = []
    return {"rules": rules, "count": len(rules)}


@router.get(
    "/wastage/scans",
    dependencies=[Depends(require_auth)],
)
async def list_scans(
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """List recent wastage scan runs."""
    rows = list_scan_runs(limit=limit)
    data = []
    for r in rows:
        row = dict(r)
        for ts_field in ("started_at", "finished_at"):
            if row.get(ts_field) and hasattr(row[ts_field], "isoformat"):
                row[ts_field] = row[ts_field].isoformat()
        data.append(row)
    return {"scans": data, "count": len(data)}


@router.get(
    "/wastage/{finding_id}",
    dependencies=[Depends(require_auth)],
    responses={404: ERROR_RESPONSE_404},
)
async def get_finding(finding_id: str) -> dict[str, Any]:
    """Fetch a single wastage finding by its ID."""
    row = get_wastage_finding(finding_id)
    if not row:
        raise HTTPException(status_code=404, detail="Finding not found")
    return _serialize_finding(row)


@router.post(
    "/wastage/{finding_id}/ack",
    dependencies=[Depends(require_auth)],
    responses={404: ERROR_RESPONSE_404},
)
async def ack_finding(finding_id: str) -> dict[str, Any]:
    """Acknowledge a finding (status → acked)."""
    ok = set_finding_status(finding_id, "acked")
    if not ok:
        raise HTTPException(status_code=404, detail="Finding not found")
    return {"finding_id": finding_id, "status": "acked"}


@router.post(
    "/wastage/{finding_id}/resolve",
    dependencies=[Depends(require_auth)],
    responses={404: ERROR_RESPONSE_404},
)
async def resolve_finding(finding_id: str) -> dict[str, Any]:
    """Mark a finding as resolved (status → resolved)."""
    ok = set_finding_status(finding_id, "resolved")
    if not ok:
        raise HTTPException(status_code=404, detail="Finding not found")
    return {"finding_id": finding_id, "status": "resolved"}


@router.post(
    "/wastage/{finding_id}/ignore",
    dependencies=[Depends(require_auth)],
    responses={404: ERROR_RESPONSE_404},
)
async def ignore_finding(finding_id: str, body: IgnoreBody) -> dict[str, Any]:
    """Ignore a finding (status → ignored); reason stored in tags."""
    extra: dict[str, str] = {}
    if body.reason:
        extra["ignore_reason"] = body.reason
    ok = set_finding_status(finding_id, "ignored", extra_tags=extra or None)
    if not ok:
        raise HTTPException(status_code=404, detail="Finding not found")
    return {"finding_id": finding_id, "status": "ignored", "reason": body.reason}


@router.post(
    "/wastage/scan",
    dependencies=[Depends(require_auth)],
)
async def trigger_scan(body: ScanBody) -> dict[str, Any]:
    """Enqueue a wastage scan for the given provider.

    If Agent B's runner module is not yet on main the endpoint returns 503
    rather than crashing at import time.
    """
    if not _RUNNER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Wastage runner module not available — Phase 5 not yet merged",
        )

    run_id = str(uuid.uuid4())
    try:
        create_scan_run(body.provider, run_id)
    except Exception:
        pass

    # Scan execution runs out-of-band via the extractor entrypoint
    # (EXTRACTOR_TYPE=azure_inventory_scan). The API only records the queued
    # run; a worker picks it up, streams inventory, and calls runner.run_scan.
    return {"run_id": run_id, "status": "queued", "provider": body.provider}
