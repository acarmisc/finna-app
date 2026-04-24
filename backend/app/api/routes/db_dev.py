"""Developer-only raw query endpoints for CLI testing."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from .. import auth as auth_module

require_auth = auth_module.require_auth
from ..db import query_all

router = APIRouter()

_MAX_LIMIT = 1000


def _safely_limit(limit: int) -> int:
    return min(max(limit, 1), _MAX_LIMIT)


@router.get("/db/costs", dependencies=[Depends(require_auth)])
async def db_costs(
    limit: int = Query(50, le=_MAX_LIMIT),
) -> dict[str, Any]:
    """Raw cost_records rows (dev only)."""
    sql = """
    SELECT record_id AS id, provider, service_category, cost_usd AS cost,
           currency_original AS currency, usage_start::text AS start_date,
           usage_end::text AS end_date, region
    FROM cost_records
    ORDER BY ingestion_ts DESC
    LIMIT %s
    """
    rows = query_all(sql, (_safely_limit(limit),))
    return {"data": rows, "count": len(rows)}


@router.get("/db/alerts", dependencies=[Depends(require_auth)])
async def db_alerts(
    limit: int = Query(50, le=_MAX_LIMIT),
) -> dict[str, Any]:
    """Raw alerts rows (dev only)."""
    sql = """
    SELECT id, type, severity, title, body, status,
           created_at::text AS first_seen, acknowledged_at::text,
           acknowledged_by
    FROM alerts
    ORDER BY created_at DESC
    LIMIT %s
    """
    rows = query_all(sql, (_safely_limit(limit),))
    data = []
    for r in rows:
        row = dict(r)
        row["description"] = r.get("body", "")
        row["is_acknowledged"] = r.get("acknowledged_at") is not None
        row["cost_impact"] = 0.0
        data.append(row)
    return {"data": data, "count": len(rows)}


@router.get("/db/configs", dependencies=[Depends(require_auth)])
async def db_configs(
    limit: int = Query(50, le=_MAX_LIMIT),
) -> dict[str, Any]:
    """Raw cloud_config rows (dev only)."""
    sql = """
    SELECT id, provider, name, credential_type, config,
           created_at::text AS last_updated, updated_at::text
    FROM cloud_config
    ORDER BY updated_at DESC
    LIMIT %s
    """
    rows = query_all(sql, (_safely_limit(limit),))
    data = []
    for r in rows:
        row = dict(r)
        row["service_category"] = r.get("credential_type", "")
        row["region"] = ""
        # Config JSON blob
        cfg = r.get("config") or {}
        if isinstance(cfg, str):
            try:
                import json
                cfg = json.loads(cfg)
            except Exception:
                cfg = {}
        row["region"] = cfg.get("region", "")
        data.append(row)
    return {"data": data, "count": len(rows)}


@router.get("/db/extractors", dependencies=[Depends(require_auth)])
async def db_extractors(
    limit: int = Query(50, le=_MAX_LIMIT),
) -> dict[str, Any]:
    """Raw extractor_runs rows (dev only)."""
    sql = """
    SELECT id, config_id, provider, extractor_type, status,
           started_at::text, finished_at::text, records_extracted,
           error_message
    FROM extractor_runs
    ORDER BY started_at DESC
    LIMIT %s
    """
    rows = query_all(sql, (_safely_limit(limit),))
    return {"data": rows, "count": len(rows)}
