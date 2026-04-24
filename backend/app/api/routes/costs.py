"""Cost data endpoints for FinOps dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .. import auth as auth_module
require_auth = auth_module.require_auth
from ..db import query_all
from ..openapi_extensions import PaginationHeadersSchema, ERROR_RESPONSE_404, ERROR_RESPONSE_422

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


@router.get("/costs", dependencies=[Depends(require_auth)])
async def list_costs(
    provider: Optional[str] = Query(None, description="Filter by provider: gcp, azure, llm"),
    project: Optional[str] = Query(None, description="Filter by project name"),
    start_date: Optional[str] = Query(None, description="Start date in ISO format"),
    end_date: Optional[str] = Query(None, description="End date in ISO format"),
    start: Optional[str] = Query(None, alias="start", include_in_schema=False),
    end: Optional[str] = Query(None, alias="end", include_in_schema=False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
) -> dict[str, Any]:
    """Get cost records with optional filtering."""
    
    # Build query with filters
    conditions = []
    params = []
    
    if provider:
        conditions.append("provider = %s")
        params.append(provider)
    
    if project:
        conditions.append("project_name = %s")
        params.append(project)
    
    # Allow CLI aliases start=/end=
    if start and not start_date:
        start_date = start
    if end and not end_date:
        end_date = end
    # Default to last 30 days if no date range specified
    end_date = end_date or datetime.now()
    start_date = start_date or (end_date - timedelta(days=30))
    
    conditions.append("cost_date >= %s")
    conditions.append("cost_date <= %s")
    params.extend([start_date, end_date])
    
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            id,
            provider,
            project_name,
            sku_name,
            cost_date,
            cost_amount,
            currency,
            tags,
            created_at
        FROM cost_records
        {where_clause}
        ORDER BY cost_date DESC, cost_amount DESC
        LIMIT 1000
    """
    
    results = query_all(sql, tuple(params))
    
    # Transform results to match frontend expectations
    costs = []
    for row in results:
        costs.append({
            "id": row["id"],
            "prov": row["provider"],
            "name": row["project_name"],
            "sku": row["sku_name"],
            "mtd": float(row["cost_amount"]),
            "delta": 0.0,  # Would need comparison logic
            "prev": 0.0,
            "tags": row["tags"] or {},
            "date": row["cost_date"].isoformat() if row["cost_date"] else None,
        })
    
    # Calculate MTD totals by provider for frontend
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
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        # CLI-compatibility wrapper
        "data": costs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": total > page * page_size,
        "has_prev": page > 1,
    }


@router.get("/costs/totals", dependencies=[Depends(require_auth)])
async def get_cost_totals(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> dict[str, Any]:
    """Get aggregated cost totals."""
    end_date = end_date or datetime.now()
    start_date = start_date or (end_date - timedelta(days=30))
    
    sql = """
        SELECT 
            provider,
            SUM(cost_amount) as total,
            COUNT(*) as record_count
        FROM cost_records
        WHERE cost_date >= %s AND cost_date <= %s
        GROUP BY provider
    """
    
    results = query_all(sql, (start_date, end_date))
    
    totals = {}
    for row in results:
        totals[row["provider"]] = float(row["total"])
    
    return {
        "totals": totals,
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
    }


@router.get("/costs/by-sku", dependencies=[Depends(require_auth)])
async def get_costs_by_sku(
    provider: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
) -> dict[str, Any]:
    """Get costs aggregated by SKU."""
    conditions = []
    params = []
    
    if provider:
        conditions.append("provider = %s")
        params.append(provider)
    
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            provider,
            project_name,
            sku_name,
            SUM(cost_amount) as mtd,
            COUNT(*) as instances
        FROM cost_records
        {where_clause}
        GROUP BY provider, project_name, sku_name
        ORDER BY mtd DESC
        LIMIT %s
    """
    
    results = query_all(sql, tuple(params) + (limit,))
    
    costs = []
    for row in results:
        costs.append({
            "prov": row["provider"],
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
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
) -> dict[str, Any]:
    """Get daily cost breakdown for chart visualization."""
    end_date = end_date or datetime.now()
    start_date = start_date or (end_date - timedelta(days=30))
    
    conditions = ["DATE(cost_date) >= %s", "DATE(cost_date) <= %s"]
    params = [start_date.date(), end_date.date()]
    
    if provider:
        conditions.append("provider = %s")
        params.append(provider)
    
    sql = f"""
        SELECT 
            DATE(cost_date) as date,
            provider,
            SUM(cost_amount) as amount
        FROM cost_records
        WHERE {" AND ".join(conditions)}
        GROUP BY DATE(cost_date), provider
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
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
    }


@router.get("/costs/summary", dependencies=[Depends(require_auth)])
async def cost_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    start: Optional[str] = Query(None, alias="start", include_in_schema=False),
    end: Optional[str] = Query(None, alias="end", include_in_schema=False),
) -> dict[str, Any]:
    """CLI-compatible cost summary endpoint."""
    if start and not start_date:
        start_date = start
    if end and not end_date:
        end_date = end
    end_date = end_date or datetime.now()
    start_date = start_date or (end_date - timedelta(days=30))

    sql = "SELECT provider, SUM(cost_amount) as total FROM cost_records WHERE cost_date >= %s AND cost_date <= %s GROUP BY provider"
    rows = query_all(sql, (start_date, end_date))

    by_provider = {}
    by_service = {}
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
        "start_period": start_date.isoformat() if hasattr(start_date, "isoformat") and isinstance(start_date, datetime) else str(start_date),
        "end_period": end_date.isoformat() if hasattr(end_date, "isoformat") and isinstance(end_date, datetime) else str(end_date),
    }

@router.get("/costs/breakdown", dependencies=[Depends(require_auth)])
async def cost_breakdown(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    start: Optional[str] = Query(None, alias="start", include_in_schema=False),
    end: Optional[str] = Query(None, alias="end", include_in_schema=False),
    limit: int = Query(50, le=100),
) -> dict[str, Any]:
    """CLI-compatible cost breakdown by SKU endpoint."""
    from ..db import query_all
    if start and not start_date:
        start_date = start
    if end and not end_date:
        end_date = end
    conditions = []
    params = []
    if start_date and end_date:
        conditions.append("cost_date >= %s")
        conditions.append("cost_date <= %s")
        params.extend([start_date, end_date])
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    sql = f"""
        SELECT sku_name as sku, SUM(cost_amount) as cost
        FROM cost_records {where_clause}
        GROUP BY sku_name
        ORDER BY cost DESC
        LIMIT %s
    """
    rows = query_all(sql, tuple(params) + (limit,))
    data = [{"sku": r["sku"], "cost": float(r["cost"])} for r in rows]
    return {"data": data, "total": len(data)}
