"""Cost data endpoints for FinOps dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional, Union

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .. import auth as auth_module
from ..db import query_all
from .openapi_extensions import ERROR_RESPONSE_404, ERROR_RESPONSE_422, PaginationHeadersSchema

require_auth = auth_module.require_auth

router = APIRouter()

# Add pagination header documentation to responses
_cost_responses = {
    200: {"description": "Cost records retrieved", "headers": PaginationHeadersSchema},
    404: ERROR_RESPONSE_404,
    422: ERROR_RESPONSE_422,
}


class CostFilter(BaseModel):
    """Filter parameters for cost queries."""
    provider: Optional[str] = None
    project: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    granularity: str = "daily"


def _resolve_window(
    window: Optional[str],
    start_date: Union[str, datetime, None],
    end_date: datetime,
) -> tuple[datetime, datetime]:
    """Resolve window shortcut + CLI aliases into concrete start/end dates."""
    if window and window not in ("mtd", "7d", "30d", "90d"):
        window = None

    if window == "mtd":
        start = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif window == "7d":
        start = end_date - timedelta(days=7)
    elif window == "30d":
        start = end_date - timedelta(days=30)
    elif window == "90d":
        start = end_date - timedelta(days=90)
    else:
        if isinstance(start_date, str):
            start = datetime.fromisoformat(start_date)
        else:
            start = start_date or (end_date - timedelta(days=30))

    return start, end_date


@router.get("/costs", dependencies=[Depends(require_auth)])
async def list_costs(
    provider: Optional[str] = Query(None, description="Filter by provider: gcp, azure, llm"),
    project: Optional[str] = Query(None, description="Filter by project name"),
    start_date: Union[str, datetime, None] = Query(None, description="Start date in ISO format"),
    end_date: Union[str, datetime, None] = Query(None, description="End date in ISO format"),
    start: Optional[str] = Query(None, alias="start", include_in_schema=False),
    end: Optional[str] = Query(None, alias="end", include_in_schema=False),
    window: Optional[str] = Query(None, description="Time window: mtd, 7d, 30d, 90d"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
) -> dict[str, Any]:
    """Get cost records with optional filtering."""

    if end and not end_date:
        end_date = end
    if start and not start_date:
        start_date = start
    end_date = end_date or datetime.now()
    start_date, end_date = _resolve_window(window, start_date, end_date)  # type: ignore[arg-type,return-assign]  # type: ignore[arg-type]

    conditions = []
    params = []

    if provider:
        conditions.append("provider = %s")
        params.append(provider)

    if project:
        conditions.append("project_name = %s")
        params.append(project)

    conditions.append("usage_start >= %s")
    conditions.append("usage_start <= %s")
    params.extend([start_date, end_date])  # type: ignore[list-item]

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT
            record_id as id,
            provider,
            project_id,
            project_name,
            service_name as sku_name,
            usage_start as cost_date,
            net_cost_usd as cost_amount,
            currency_original,
            tags
        FROM cost_records
        {where_clause}
        ORDER BY usage_start DESC, net_cost_usd DESC
        LIMIT 1000
    """

    results = query_all(sql, tuple(params))

    costs = []
    for row in results:
        costs.append({
            "id": row["id"],
            "prov": row["provider"],
            "project_id": row["project_id"],
            "name": row["project_name"],
            "sku": row["sku_name"],
            "mtd": float(row["cost_amount"]),
            "delta": 0.0,
            "prev": 0.0,
            "tags": row["tags"] or {},
            "date": row["cost_date"].isoformat() if row["cost_date"] else None,
        })

    provider_totals = {}
    for cost in costs:
        prov = cost["prov"]
        if prov not in provider_totals:
            provider_totals[prov] = 0
        provider_totals[prov] += cost["mtd"]

    total = len(costs)
    return {
        "costs": costs,
        "totals": provider_totals,
        "filtered": total > 0,
        "startDate": start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date),
        "endDate": end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date),
        "window": window or "custom",
        "data": costs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": total > page * page_size,
        "has_prev": page > 1,
    }


@router.get("/costs/export", dependencies=[Depends(require_auth)])
async def export_costs(
    provider: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    start_date: Union[str, datetime, None] = Query(None),
    end_date: Union[str, datetime, None] = Query(None),
    window: Optional[str] = Query(None, description="Time window: mtd, 7d, 30d, 90d"),
) -> StreamingResponse:
    """Export cost data as CSV."""
    end_date_val: datetime
    if end_date is None:
        end_date_val = datetime.now()
    elif isinstance(end_date, str):
        end_date_val = datetime.fromisoformat(end_date)
    else:
        end_date_val = end_date
    if isinstance(start_date, str):
        start_date_val = datetime.fromisoformat(start_date)
    else:
        start_date_val = start_date or datetime.now()
    start_dt, end_dt = _resolve_window(window, start_date_val, end_date_val)

    conditions: list[str] = []
    params: list[Any] = []
    if provider:
        conditions.append("provider = %s")
        params.append(provider)
    if project:
        conditions.append("project_name = %s")
        params.append(project)
    conditions.extend(["usage_start >= %s", "usage_start <= %s"])
    params.extend([start_dt, end_dt])

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""SELECT record_id, provider, project_name, service_name, usage_start, net_cost_usd, currency_original
        FROM cost_records {where} ORDER BY usage_start DESC LIMIT 10000"""

    results = query_all(sql, tuple(params))

    import csv
    import io
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id", "provider", "project", "sku", "date", "amount", "currency"])
    for r in results:
        usage_ts = r["usage_start"].isoformat() if r["usage_start"] else ""
        currency = r.get("currency_original", "USD")
        w.writerow([r["record_id"], r["provider"], r["project_name"], r["service_name"],
            usage_ts, r["net_cost_usd"], currency])

    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=costs.csv"})


@router.get("/costs/totals", dependencies=[Depends(require_auth)])
async def get_cost_totals(
    start_date: Union[str, datetime, None] = Query(None),
    end_date: Union[str, datetime, None] = Query(None),
    window: Optional[str] = Query(None, description="Time window: mtd, 7d, 30d, 90d"),
) -> dict[str, Any]:
    """Get aggregated cost totals per provider with mtd/prev/delta structure."""
    end_date = end_date or datetime.now()
    if not isinstance(end_date, datetime):
        end_date = datetime.fromisoformat(end_date)  # type: ignore[assignment]
    start_date = start_date or (end_date - timedelta(days=30))
    window = window or "mtd"

    if window == "mtd":
        current_start = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif window == "7d":
        current_start = end_date - timedelta(days=7)
    elif window == "30d":
        current_start = end_date - timedelta(days=30)
    elif window == "90d":
        current_start = end_date - timedelta(days=90)
    else:
        current_start = start_date  # type: ignore[assignment]

    prev_end = current_start - timedelta(seconds=1)
    prev_start = prev_end - (end_date - current_start)  # type: ignore[assignment]

    sql = """
        SELECT
            provider,
            SUM(net_cost_usd) as total,
            COUNT(*) as record_count
        FROM cost_records
        WHERE usage_start >= %s AND usage_start <= %s
        GROUP BY provider
    """

    current_rows = query_all(sql, (current_start, end_date))
    prev_rows = query_all(sql, (prev_start, prev_end))

    curr_totals: dict[str, float] = {}
    for row in current_rows:
        curr_totals[row["provider"]] = float(row["total"])

    prev_totals: dict[str, float] = {}
    for row in prev_rows:
        prev_totals[row["provider"]] = float(row["total"])

    all_providers = sorted(set(list(curr_totals.keys()) + list(prev_totals.keys())))
    totals = {}
    grand_mtd = 0.0
    grand_prev = 0.0
    for prov in all_providers:
        mtd_val = curr_totals.get(prov, 0.0)
        prev_val = prev_totals.get(prov, 0.0)
        delta_val = round((mtd_val - prev_val) / prev_val * 100, 1) if prev_val else 0.0
        totals[prov] = {"mtd": mtd_val, "prev": prev_val, "delta": delta_val}
        grand_mtd += mtd_val
        grand_prev += prev_val

    grand_delta = round((grand_mtd - grand_prev) / grand_prev * 100, 1) if grand_prev else 0.0
    totals["total"] = {"mtd": grand_mtd, "prev": grand_prev, "delta": grand_delta}

    return {
        "totals": totals,
        "window": window,
        "startDate": current_start.isoformat() if hasattr(current_start, "isoformat") else str(current_start),
        "endDate": end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date),
    }


@router.get("/costs/by-sku", dependencies=[Depends(require_auth)])
async def get_costs_by_sku(
    provider: Optional[str] = Query(None),
    project: Optional[str] = Query(None, description="Filter by project name"),
    limit: int = Query(50, le=100),
) -> dict[str, Any]:
    """Get costs aggregated by SKU."""
    conditions = []
    params = []

    if provider:
        conditions.append("provider = %s")
        params.append(provider)

    if project:
        conditions.append("project_name = %s")
        params.append(project)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT
            provider,
            project_id,
            project_name,
            service_name as sku_name,
            SUM(net_cost_usd) as mtd,
            COUNT(*) as instances
        FROM cost_records
        {where_clause}
        GROUP BY provider, project_id, project_name, service_name
        ORDER BY mtd DESC
        LIMIT %s
    """

    results = query_all(sql, tuple(params) + (limit,))

    costs = []
    for row in results:
        costs.append({
            "prov": row["provider"],
            "project_id": row["project_id"],
            "name": row["project_name"],
            "sku": row["sku_name"],
            "mtd": float(row["mtd"]),
            "delta": 0.0,
            "prev": 0.0,
            "instances": row["instances"],
        })

    return {"costs": costs, "totalRows": len(costs)}


@router.get("/costs/daily", dependencies=[Depends(require_auth)])
async def get_daily_costs(
    start_date: Union[str, datetime, None] = Query(None),
    end_date: Union[str, datetime, None] = Query(None),
    start: Optional[str] = Query(None, alias="start", include_in_schema=False),
    end: Optional[str] = Query(None, alias="end", include_in_schema=False),
    provider: Optional[str] = Query(None),
    window: Optional[str] = Query(None, description="Time window: mtd, 7d, 30d, 90d"),
) -> dict[str, Any]:
    """Get daily cost breakdown for chart visualization."""
    if end and not end_date:
        end_date = end
    if start and not start_date:
        start_date = start
    end_date = end_date or datetime.now()
    if not isinstance(end_date, datetime):
        end_date = datetime.fromisoformat(end_date)  # type: ignore[assignment]
    start_date, end_date = _resolve_window(window, start_date, end_date)  # type: ignore[arg-type,return-assign]  # type: ignore[arg-type]

    conditions = ["DATE(usage_start) >= %s", "DATE(usage_start) <= %s"]
    _sd = start_date.date() if hasattr(start_date, "date") else start_date  # type: ignore[union-attr]
    _ed = end_date.date() if hasattr(end_date, "date") else end_date  # type: ignore[union-attr]
    params = [_sd, _ed]

    if provider:
        conditions.append("provider = %s")
        params.append(provider)  # type: ignore[arg-type]

    sql = f"""
        SELECT
            DATE(usage_start) as date,
            provider,
            SUM(net_cost_usd) as amount
        FROM cost_records
        WHERE {" AND ".join(conditions)}
        GROUP BY DATE(usage_start), provider
        ORDER BY date DESC
    """

    results = query_all(sql, tuple(params))

    # Build daily series by provider
    daily_data = {}
    for row in results:
        date_str = row["date"].isoformat() if row["date"] else None
        if not date_str:
            continue

        if date_str not in daily_data:
            daily_data[date_str] = {"date": date_str}

        prov = row["provider"]
        daily_data[date_str][prov] = float(row["amount"])

    # Convert to list and sort by date descending
    days = list(daily_data.values())
    days.sort(key=lambda x: x["date"], reverse=True)

    return {
        "days": days,
        "startDate": start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date),  # type: ignore[union-attr]
        "endDate": end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date),
    }


@router.get("/costs/summary", dependencies=[Depends(require_auth)])
async def cost_summary(
    start_date: Union[str, datetime, None] = Query(None),
    end_date: Union[str, datetime, None] = Query(None),
    start: Optional[str] = Query(None, alias="start", include_in_schema=False),
    end: Optional[str] = Query(None, alias="end", include_in_schema=False),
    window: Optional[str] = Query(None, description="Time window: mtd, 7d, 30d, 90d"),
) -> dict[str, Any]:
    """CLI-compatible cost summary endpoint."""
    if end and not end_date:
        end_date = end
    if start and not start_date:
        start_date = start
    end_date = end_date or datetime.now()
    if not isinstance(end_date, datetime):
        end_date = datetime.fromisoformat(end_date)  # type: ignore[assignment]
    start_date, end_date = _resolve_window(window, start_date, end_date)  # type: ignore[arg-type,return-assign]  # type: ignore[arg-type]

    sql = (
        "SELECT provider, SUM(net_cost_usd) as total "
        "FROM cost_records "
        "WHERE usage_start >= %s AND usage_start <= %s GROUP BY provider"
    )
    rows = query_all(sql, (start_date, end_date))  # type: ignore[list-item]

    by_provider = {}
    by_service: dict[str, float] = {}
    total = 0.0
    for r in rows:
        val = float(r["total"] or 0)
        by_provider[r["provider"]] = val
        by_service.setdefault(r["provider"], 0.0)
        by_service[r["provider"]] += val
        total += val

    return {
        "total": total,
        "by_provider": by_provider,
        "by_service": by_service,
        "start_period": (
            start_date.isoformat()
            if hasattr(start_date, "isoformat") and isinstance(start_date, datetime)
            else str(start_date)
        ),
        "end_period": (
            end_date.isoformat()
            if hasattr(end_date, "isoformat") and isinstance(end_date, datetime)
            else str(end_date)
        ),
    }

@router.get("/costs/breakdown", dependencies=[Depends(require_auth)])
async def cost_breakdown(
    start_date: Union[str, datetime, None] = Query(None),
    end_date: Union[str, datetime, None] = Query(None),
    start: Optional[str] = Query(None, alias="start", include_in_schema=False),
    end: Optional[str] = Query(None, alias="end", include_in_schema=False),
    window: Optional[str] = Query(None, description="Time window: mtd, 7d, 30d, 90d"),
    limit: int = Query(50, le=100),
) -> dict[str, Any]:
    """CLI-compatible cost breakdown by SKU endpoint."""
    from ..db import query_all
    if end and not end_date:
        end_date = end
    if start and not start_date:
        start_date = start
    end_date = end_date or datetime.now()
    if not isinstance(end_date, datetime):
        end_date = datetime.fromisoformat(end_date)  # type: ignore[assignment]
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date)  # type: ignore[assignment]
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date)  # type: ignore[assignment]
    start_date, end_date = _resolve_window(window, start_date, end_date)  # type: ignore[arg-type,return-assign]  # type: ignore[arg-type]

    conditions = []
    params = []
    if start_date and end_date:
        conditions.append("usage_start >= %s")
        conditions.append("usage_start <= %s")
        params.extend([start_date, end_date])
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    sql = f"""
        SELECT service_name as sku, SUM(net_cost_usd) as cost
        FROM cost_records {where_clause}
        GROUP BY service_name
        ORDER BY cost DESC
        LIMIT %s
    """
    rows = query_all(sql, tuple(params) + (limit,))
    data = [{"sku": r["sku"], "cost": float(r["cost"])} for r in rows]
    return {"data": data, "total": len(data)}


@router.get("/costs/skus", dependencies=[Depends(require_auth)])
async def get_skus_by_provider(
    provider: str = Query(..., description="Cloud provider: azure, gcp, llm"),
) -> dict[str, Any]:
    """Get distinct SKUs (service names) for a given provider."""
    sql = """
        SELECT DISTINCT service_name as sku
        FROM cost_records
        WHERE provider = %s AND service_name IS NOT NULL
        ORDER BY service_name
    """
    rows = query_all(sql, (provider,))
    return {"skus": [r["sku"] for r in rows if r["sku"]]}


@router.get("/dashboard/stats", dependencies=[Depends(require_auth)])
async def dashboard_stats(
    range: Optional[str] = Query(None, description="Time range: mtd, 7d, 30d, 90d"),
) -> dict[str, Any]:
    """Aggregate cost totals + daily series + alert stats for the dashboard."""
    window = range or "mtd"
    end_dt = datetime.now()

    if window == "mtd":
        current_start = end_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif window == "7d":
        current_start = end_dt - timedelta(days=7)
    elif window == "30d":
        current_start = end_dt - timedelta(days=30)
    elif window == "90d":
        current_start = end_dt - timedelta(days=90)
    else:
        current_start = end_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    prev_end = current_start - timedelta(seconds=1)
    prev_start = prev_end - (end_dt - current_start)

    totals_sql = """
        SELECT provider, SUM(net_cost_usd) as total
        FROM cost_records
        WHERE usage_start >= %s AND usage_start <= %s
        GROUP BY provider
    """
    current_rows = query_all(totals_sql, (current_start, end_dt))
    prev_rows = query_all(totals_sql, (prev_start, prev_end))

    curr_totals: dict[str, float] = {}
    for row in current_rows:
        curr_totals[row["provider"]] = float(row["total"])
    prev_totals: dict[str, float] = {}
    for row in prev_rows:
        prev_totals[row["provider"]] = float(row["total"])

    azure_mtd = curr_totals.get("azure", 0.0)
    gcp_mtd = curr_totals.get("gcp", 0.0)
    llm_mtd = curr_totals.get("llm", 0.0)
    total_mtd = azure_mtd + gcp_mtd + llm_mtd

    totals = {
        "azure": azure_mtd,
        "gcp": gcp_mtd,
        "llm": llm_mtd,
        "total": total_mtd,
    }

    daily_sql = """
        SELECT DATE(usage_start) as date, provider, SUM(net_cost_usd) as amount
        FROM cost_records
        WHERE usage_start >= %s AND usage_start <= %s
        GROUP BY DATE(usage_start), provider
        ORDER BY date ASC
    """
    daily_rows = query_all(daily_sql, (current_start, end_dt))

    daily_map: dict[str, dict[str, Any]] = {}
    for row in daily_rows:
        date_str = row["date"].isoformat() if row["date"] else None
        if not date_str:
            continue
        if date_str not in daily_map:
            daily_map[date_str] = {"date": date_str}
        daily_map[date_str][row["provider"]] = float(row["amount"])

    daily = [
        {"date": d["date"], "azure": d.get("azure", 0.0), "gcp": d.get("gcp", 0.0), "llm": d.get("llm", 0.0)}
        for d in sorted(daily_map.values(), key=lambda x: x["date"])
    ]

    alert_sql = """
        SELECT status, COUNT(*) as count
        FROM alerts
        GROUP BY status
    """
    alert_rows = query_all(alert_sql)
    by_status: dict[str, int] = {"firing": 0, "ack": 0, "resolved": 0}
    for r in alert_rows:
        status_val = r["status"] or "firing"
        by_status[status_val] = by_status.get(status_val, 0) + int(r["count"] or 0)
    alert_stats = by_status

    return {
        "totals": totals,
        "daily": daily,
        "alertStats": alert_stats,
    }
