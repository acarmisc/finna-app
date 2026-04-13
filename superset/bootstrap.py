#!/usr/bin/env python3
# =============================================================================
# FinOps Multi-Cloud Monitoring -- Superset Dashboard Bootstrap
# =============================================================================
# Creates the FinOps database connection, datasets, and dashboards by calling
# the Superset REST API.  Run this against an existing Superset instance.
#
# Usage:
#   export SUPERSET_BASE_URL=http://your-superset:8088
#   export SUPERSET_ADMIN_USERNAME=admin
#   export ADMIN_PASSWORD=your-password
#   export FINOPS_PG_URI=postgresql://finops:finops_dev@postgres:5432/finops
#   python3 superset/bootstrap.py
#
# Idempotent: every resource is looked up by name before creation so the
# script can be re-run safely.
# =============================================================================

import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

# ---------------------------------------------------------------------------
# Configuration (override via environment variables)
# ---------------------------------------------------------------------------
SUPERSET_BASE_URL = os.getenv("SUPERSET_BASE_URL", "http://superset:8088")
ADMIN_USERNAME = os.getenv("SUPERSET_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
FINOPS_PG_URI = os.getenv(
    "FINOPS_PG_URI", "postgresql://finops:finops_dev@postgres:5432/finops"
)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _req(path, method="GET", body=None, token=None):
    url = f"{SUPERSET_BASE_URL}{path}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        detail = exc.read().decode()
        print(f"HTTP {exc.code} on {method} {url}: {detail}", file=sys.stderr)
        raise


def login():
    """Authenticate and return an access token."""
    resp = _req("/api/v1/security/login", "POST", {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
        "provider": "db",
    })
    return resp["access_token"]


def get_csrf(token):
    """Fetch CSRF token (required for POST/PUT/DELETE)."""
    resp = _req("/api/v1/security/csrf_token/", token=token)
    return resp["csrf"]


class Api:
    """Thin wrapper that injects auth headers (including CSRF)."""

    def __init__(self, token, csrf):
        self.token = token
        self.csrf = csrf

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-CSRFToken": self.csrf,
            "Referer": f"{SUPERSET_BASE_URL}/",
        }

    def get(self, path, params=None):
        qs = urllib.parse.urlencode(params) if params else ""
        url = f"{SUPERSET_BASE_URL}{path}?{qs}"
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def post(self, path, body):
        url = f"{SUPERSET_BASE_URL}{path}"
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def put(self, path, body):
        url = f"{SUPERSET_BASE_URL}{path}"
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="PUT")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# Resource helpers (idempotent)
# ---------------------------------------------------------------------------

def ensure_database(api, name, uri):
    """Create or return the FinOps PostgreSQL database connection."""
    try:
        result = api.get("/api/v1/database/", {"q": json.dumps({"filters": [{"col": "database_name", "opr": "eq", "value": name}])}})
        if result.get("result"):
            db = result["result"][0]
            print(f"  Database '{name}' already exists (id={db['id']}).")
            return db["id"]
    except Exception:
        pass

    body = {
        "database_name": name,
        "sqlalchemy_uri": uri,
        "expose_in_sqllab": True,
        "allow_ctas": True,
        "allow_cvas": True,
        "allow_dml": False,
        "extra": json.dumps({"allows_virtual_table_explore": True}),
    }
    resp = api.post("/api/v1/database/", body)
    db_id = resp.get("id") or resp.get("result", {}).get("id")
    print(f"  Database '{name}' created (id={db_id}).")
    return db_id


def ensure_dataset(api, table_name, schema, db_id):
    """Create or return a physical dataset."""
    try:
        result = api.get("/api/v1/dataset/", {
            "q": json.dumps({
                "filters": [
                    {"col": "table_name", "opr": "eq", "value": table_name},
                    {"col": "database_id", "opr": "eq", "value": db_id},
                ]
            })
        })
        if result.get("result"):
            ds = result["result"][0]
            print(f"  Dataset '{table_name}' already exists (id={ds['id']}).")
            return ds["id"]
    except Exception:
        pass

    body = {
        "database_id": db_id,
        "table_name": table_name,
        "schema": schema or None,
        "sql": None,
    }
    resp = api.post("/api/v1/dataset/", body)
    ds_id = resp.get("id") or resp.get("result", {}).get("id")
    print(f"  Dataset '{table_name}' created (id={ds_id}).")
    return ds_id


def ensure_virtual_dataset(api, dataset_name, sql, db_id):
    """Create or return a virtual (SQL) dataset."""
    try:
        result = api.get("/api/v1/dataset/", {
            "q": json.dumps({
                "filters": [
                    {"col": "table_name", "opr": "eq", "value": dataset_name},
                    {"col": "database_id", "opr": "eq", "value": db_id},
                ]
            })
        })
        if result.get("result"):
            ds = result["result"][0]
            print(f"  Virtual dataset '{dataset_name}' already exists (id={ds['id']}).")
            return ds["id"]
    except Exception:
        pass

    body = {
        "database_id": db_id,
        "table_name": dataset_name,
        "sql": sql,
    }
    resp = api.post("/api/v1/dataset/", body)
    ds_id = resp.get("id") or resp.get("result", {}).get("id")
    print(f"  Virtual dataset '{dataset_name}' created (id={ds_id}).")
    return ds_id


def ensure_dashboard(api, dashboard_title, dashboard_json):
    """Create or return a dashboard by title."""
    try:
        result = api.get("/api/v1/dashboard/", {
            "q": json.dumps({"filters": [{"col": "dashboard_title", "opr": "eq", "value": dashboard_title}]})
        })
        if result.get("result"):
            db = result["result"][0]
            print(f"  Dashboard '{dashboard_title}' already exists (id={db['id']}).")
            return db["id"]
    except Exception:
        pass

    body = {
        "dashboard_title": dashboard_title,
        "json_metadata": json.dumps({}),
        "position_json": json.dumps(dashboard_json),
        "published": True,
    }
    resp = api.post("/api/v1/dashboard/", body)
    dash_id = resp.get("id") or resp.get("result", {}).get("id")
    print(f"  Dashboard '{dashboard_title}' created (id={dash_id}).")
    return dash_id


# ---------------------------------------------------------------------------
# Dashboard definitions
# ---------------------------------------------------------------------------

FINOPS_OVERVIEW_DASHBOARD = {
    "DASHBOARD_VERSION": "v2",
    "description": "FinOps multi-cloud cost overview",
    "CHARTS": [
        {
            "id": "total-cost-30d",
            "slice_name": "Total Cost (Last 30 Days)",
            "viz_type": "big_number_total",
            "datasource": "daily_costs",
            "metrics": [{"expressionType": "SQL", "sqlExpression": "SUM(total_cost)", "label": "total_cost"}],
            "sql": "SELECT SUM(total_cost) AS total_cost FROM daily_costs WHERE day >= CURRENT_DATE - 30",
            "time_range": "Last 30 days",
        },
        {
            "id": "cost-per-provider-pie",
            "slice_name": "Cost per Provider (Last 30 Days)",
            "viz_type": "pie",
            "datasource": "daily_costs",
            "groupby": ["provider"],
            "metrics": [{"expressionType": "SQL", "sqlExpression": "SUM(total_cost)", "label": "cost"}],
            "sql": "SELECT provider, SUM(total_cost) AS cost FROM daily_costs WHERE day >= CURRENT_DATE - 30 GROUP BY provider ORDER BY cost DESC",
            "time_range": "Last 30 days",
        },
        {
            "id": "daily-cost-trend-provider",
            "slice_name": "Daily Cost Trend per Provider (90 Days)",
            "viz_type": "echarts_timeseries_line",
            "datasource": "daily_costs",
            "groupby": ["provider"],
            "x_axis": "day",
            "metrics": [{"expressionType": "SQL", "sqlExpression": "SUM(total_cost)", "label": "daily_cost"}],
            "sql": "SELECT day, provider, SUM(total_cost) AS daily_cost FROM daily_costs WHERE day >= CURRENT_DATE - 90 GROUP BY day, provider ORDER BY day",
            "time_range": "Last 90 days",
        },
        {
            "id": "top-10-projects",
            "slice_name": "Top 10 Projects by Cost (Last 30 Days)",
            "viz_type": "echarts_timeseries_bar",
            "datasource": "daily_costs",
            "groupby": ["project_id"],
            "metrics": [{"expressionType": "SQL", "sqlExpression": "SUM(total_cost)", "label": "cost"}],
            "sql": "SELECT project_id, SUM(total_cost) AS cost FROM daily_costs WHERE day >= CURRENT_DATE - 30 GROUP BY project_id ORDER BY cost DESC LIMIT 10",
            "time_range": "Last 30 days",
        },
        {
            "id": "cost-per-service-category",
            "slice_name": "Cost per Service Category (Last 30 Days)",
            "viz_type": "table",
            "datasource": "daily_costs",
            "groupby": ["service_category"],
            "metrics": [
                {"expressionType": "SQL", "sqlExpression": "SUM(total_cost)", "label": "cost"},
                {"expressionType": "SQL", "sqlExpression": "SUM(record_count)", "label": "records"},
            ],
            "sql": "SELECT service_category, SUM(total_cost) AS cost, SUM(record_count) AS records FROM daily_costs WHERE day >= CURRENT_DATE - 30 GROUP BY service_category ORDER BY cost DESC",
            "time_range": "Last 30 days",
        },
    ],
}


LLM_COSTS_DASHBOARD = {
    "DASHBOARD_VERSION": "v2",
    "description": "LLM cost tracking and efficiency metrics",
    "CHARTS": [
        {
            "id": "model-cost-table",
            "slice_name": "Model Cost & Token Efficiency",
            "viz_type": "table",
            "datasource": "daily_costs",
            "sql": (
                "SELECT model_name, "
                "  SUM(total_cost) AS cost, "
                "  SUM(total_input_tokens) AS input_tok, "
                "  SUM(total_output_tokens) AS output_tok, "
                "  SUM(total_cost) / NULLIF(SUM(total_input_tokens + total_output_tokens), 0) * 1e6 AS cost_per_mtok "
                "FROM daily_costs "
                "WHERE service_category = 'llm' AND day >= CURRENT_DATE - 30 "
                "GROUP BY model_name ORDER BY cost DESC"
            ),
            "time_range": "Last 30 days",
        },
        {
            "id": "daily-llm-cost-per-model",
            "slice_name": "Daily LLM Cost per Model (90 Days)",
            "viz_type": "echarts_timeseries_line",
            "datasource": "daily_costs",
            "groupby": ["model_name"],
            "x_axis": "day",
            "metrics": [{"expressionType": "SQL", "sqlExpression": "SUM(total_cost)", "label": "daily_cost"}],
            "sql": (
                "SELECT day, model_name, SUM(total_cost) AS daily_cost "
                "FROM daily_costs "
                "WHERE service_category = 'llm' AND day >= CURRENT_DATE - 90 "
                "GROUP BY day, model_name ORDER BY day"
            ),
            "time_range": "Last 90 days",
        },
        {
            "id": "total-llm-cost",
            "slice_name": "Total LLM Cost (Last 30 Days)",
            "viz_type": "big_number_total",
            "datasource": "daily_costs",
            "sql": (
                "SELECT SUM(total_cost) AS total_llm_cost "
                "FROM daily_costs "
                "WHERE service_category = 'llm' AND day >= CURRENT_DATE - 30"
            ),
            "time_range": "Last 30 days",
        },
        {
            "id": "llm-pct-total",
            "slice_name": "LLM as % of Total Cloud Cost",
            "viz_type": "big_number_total",
            "datasource": "daily_costs",
            "sql": (
                "SELECT COALESCE(SUM(CASE WHEN service_category = 'llm' THEN total_cost ELSE 0 END), 0) "
                "  / NULLIF(SUM(total_cost), 0) * 100 AS llm_pct "
                "FROM daily_costs WHERE day >= CURRENT_DATE - 30"
            ),
            "time_range": "Last 30 days",
        },
    ],
}


PROJECT_DRILLDOWN_DASHBOARD = {
    "DASHBOARD_VERSION": "v2",
    "description": "Per-project cost drill-down",
    "CHARTS": [
        {
            "id": "daily-cost-per-category",
            "slice_name": "Daily Cost per Service Category (90 Days)",
            "viz_type": "echarts_timeseries_line",
            "datasource": "daily_costs",
            "groupby": ["service_category"],
            "x_axis": "day",
            "metrics": [{"expressionType": "SQL", "sqlExpression": "SUM(total_cost)", "label": "daily_cost"}],
            "sql": (
                "SELECT day, service_category, SUM(total_cost) AS daily_cost "
                "FROM daily_costs WHERE day >= CURRENT_DATE - 90 "
                "GROUP BY day, service_category ORDER BY day"
            ),
            "time_range": "Last 90 days",
        },
        {
            "id": "resource-cost-detail",
            "slice_name": "Resource-Level Cost Detail (Last 30 Days)",
            "viz_type": "table",
            "datasource": "daily_costs",
            "sql": (
                "SELECT service_name, service_category, SUM(total_cost) AS cost, SUM(record_count) AS records "
                "FROM daily_costs WHERE day >= CURRENT_DATE - 30 "
                "GROUP BY service_name, service_category ORDER BY cost DESC"
            ),
            "time_range": "Last 30 days",
        },
        {
            "id": "mtd-cost",
            "slice_name": "Month-to-Date Cost",
            "viz_type": "big_number_total",
            "datasource": "daily_costs",
            "sql": (
                "SELECT SUM(total_cost) AS mtd_cost "
                "FROM daily_costs "
                "WHERE day >= DATE_TRUNC('month', CURRENT_DATE)::date"
            ),
        },
        {
            "id": "prev-month-cost",
            "slice_name": "Previous Month Cost",
            "viz_type": "big_number_total",
            "datasource": "daily_costs",
            "sql": (
                "SELECT SUM(total_cost) AS prev_month_cost "
                "FROM daily_costs "
                "WHERE day >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')::date "
                "  AND day < DATE_TRUNC('month', CURRENT_DATE)::date"
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# Chart creation helper
# ---------------------------------------------------------------------------

def create_chart(api, chart_def, dataset_id, db_id):
    """Create a single chart (slice) via the API."""
    slice_name = chart_def["slice_name"]
    viz_type = chart_def["viz_type"]
    sql = chart_def.get("sql", "")

    # Check if chart already exists
    try:
        result = api.get("/api/v1/chart/", {
            "q": json.dumps({"filters": [{"col": "slice_name", "opr": "eq", "value": slice_name}]})
        })
        if result.get("result"):
            print(f"    Chart '{slice_name}' already exists (id={result['result'][0]['id']}).")
            return result["result"][0]["id"]
    except Exception:
        pass

    params = {
        "datasource": f"{dataset_id}__table",
        "viz_type": viz_type,
        "sql": sql,
    }

    # Add chart-type-specific parameters
    if viz_type in ("echarts_timeseries_line", "echarts_timeseries_bar"):
        params["x_axis"] = chart_def.get("x_axis", "day")
        if chart_def.get("groupby"):
            params["groupby"] = chart_def["groupby"]
        if chart_def.get("metrics"):
            params["metrics"] = chart_def["metrics"]
    elif viz_type == "pie":
        if chart_def.get("groupby"):
            params["groupby"] = chart_def["groupby"]
        if chart_def.get("metrics"):
            params["metrics"] = chart_def["metrics"]
    elif viz_type == "big_number_total":
        pass  # sql-based, no extra params
    elif viz_type == "table":
        pass  # sql-based, no extra params

    body = {
        "slice_name": slice_name,
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "viz_type": viz_type,
        "params": json.dumps(params),
        "description": chart_def.get("description", ""),
    }

    resp = api.post("/api/v1/chart/", body)
    chart_id = resp.get("id") or resp.get("result", {}).get("id")
    print(f"    Chart '{slice_name}' created (id={chart_id}).")
    return chart_id


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Superset Bootstrap (API) ===")

    # Wait for Superset to be ready
    max_wait = 120
    waited = 0
    while waited < max_wait:
        try:
            _req("/health")
            print("  Superset is healthy.")
            break
        except Exception:
            print(f"  Waiting for Superset ... ({waited}s / {max_wait}s)")
            time.sleep(5)
            waited += 5
    else:
        print("ERROR: Superset did not become healthy in time.", file=sys.stderr)
        sys.exit(1)

    # Authenticate
    token = login()
    csrf = get_csrf(token)
    api = Api(token, csrf)

    # -- Database connection -------------------------------------------------
    print("\n[1/4] Creating FinOps database connection ...")
    db_id = ensure_database(api, "finops-pg", FINOPS_PG_URI)

    # -- Datasets ------------------------------------------------------------
    print("\n[2/4] Creating datasets ...")
    ds_daily_costs = ensure_dataset(api, "daily_costs", "public", db_id)
    ds_cost_records = ensure_dataset(api, "cost_records", "public", db_id)
    ds_extractor_health = ensure_dataset(api, "extractor_health", "public", db_id)

    # -- Charts & Dashboards -------------------------------------------------
    print("\n[3/4] Creating dashboards and charts ...")

    # Dashboard 1: FinOps Overview
    print("  Dashboard 1: FinOps Overview")
    for chart_def in FINOPS_OVERVIEW_DASHBOARD["CHARTS"]:
        create_chart(api, chart_def, ds_daily_costs, db_id)
    ensure_dashboard(api, "FinOps Overview", FINOPS_OVERVIEW_DASHBOARD)

    # Dashboard 2: LLM Costs
    print("  Dashboard 2: LLM Costs")
    for chart_def in LLM_COSTS_DASHBOARD["CHARTS"]:
        create_chart(api, chart_def, ds_daily_costs, db_id)
    ensure_dashboard(api, "LLM Costs", LLM_COSTS_DASHBOARD)

    # Dashboard 3: Project Drill-down
    print("  Dashboard 3: Project Drill-down")
    for chart_def in PROJECT_DRILLDOWN_DASHBOARD["CHARTS"]:
        create_chart(api, chart_def, ds_daily_costs, db_id)
    ensure_dashboard(api, "Project Drill-down", PROJECT_DRILLDOWN_DASHBOARD)

    print("\n[4/4] Bootstrap complete.")
    print("=== Done ===")


if __name__ == "__main__":
    main()