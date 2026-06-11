import json

DS_UID = "efothkw3y68sgb"
PREFIX = "cost_records"
LLM_FILTER = "WHERE provider = 'llm'"
LLM_FILTER_AND = "WHERE provider = 'llm'"
VAR_FILTERS = "AND (model_name IN ($model) OR model_name IS NULL)"
# All LLM records have NULL project, so project filter doesn't narrow
# but include for consistency
PROJECT_FILTER = "AND (COALESCE(project_name, '(no project)') IN ($project))"

d = {
    "dashboard": {
        "uid": "finops-llm-cost",
        "title": "FinOps - LLM Cost",
        "tags": ["finops", "llm", "cost-management"],
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 0,
        "refresh": "30m",
        "templating": {
            "list": [
                {
                    "name": "model",
                    "type": "query",
                    "label": "Model",
                    "query": f"SELECT DISTINCT model_name FROM {PREFIX} {LLM_FILTER} AND model_name IS NOT NULL ORDER BY 1",
                    "datasource": {"type": "postgres", "uid": DS_UID},
                    "refresh": 2,
                    "includeAll": True,
                    "multi": True,
                    "hide": 0,
                    "sort": 1,
                    "current": {},
                    "options": []
                },
                {
                    "name": "project",
                    "type": "query",
                    "label": "Project",
                    "query": f"SELECT DISTINCT COALESCE(project_name, '(no project)') FROM {PREFIX} {LLM_FILTER} ORDER BY 1",
                    "datasource": {"type": "postgres", "uid": DS_UID},
                    "refresh": 2,
                    "includeAll": True,
                    "multi": True,
                    "hide": 0,
                    "sort": 1,
                    "current": {},
                    "options": []
                }
            ]
        },
        "time": {"from": "now-30d", "to": "now"},
        "timepicker": {"refresh_intervals": ["5m", "15m", "30m", "1h", "2h", "1d"]},
        "panels": [],
        "schemaVersion": 39
    },
    "overwrite": True,
    "message": "Imported from finna-app Grafana dashboards"
}

panels = d["dashboard"]["panels"]
pid = [0]

def next_id():
    pid[0] += 1
    return pid[0]

DS = {"type": "postgres", "uid": DS_UID}

def stat_panel(title, sql, grid, unit="USD", decimals=2, color_mode="thresholds", thresh_steps=None):
    if thresh_steps is None:
        thresh_steps = [{"color": "green", "value": None}]
    return {
        "id": next_id(),
        "title": title,
        "type": "stat",
        "gridPos": {"h": 4, "w": grid["w"], "x": grid["x"], "y": grid["y"]},
        "datasource": DS,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": color_mode},
                "mappings": [],
                "thresholds": {"mode": "absolute", "steps": thresh_steps},
                "unit": unit,
                "decimals": decimals
            },
            "overrides": []
        },
        "options": {
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["last"], "fields": "", "values": False},
            "textMode": "auto"
        },
        "targets": [{
            "datasource": DS,
            "format": "table",
            "rawQuery": True,
            "rawSql": sql,
            "refId": "A"
        }]
    }

def time_series_panel(title, sql, grid, unit="USD", fill=80):
    return {
        "id": next_id(),
        "title": title,
        "type": "timeseries",
        "gridPos": {"h": 8, "w": grid["w"], "x": grid["x"], "y": grid["y"]},
        "datasource": DS,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "axisBorderShow": False, "axisCenteredZero": False,
                    "axisColorMode": "text", "axisLabel": "", "axisPlacement": "auto",
                    "fillOpacity": fill, "gradientMode": "none",
                    "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                    "lineWidth": 1, "pointSize": 5,
                    "scaleDistribution": {"type": "linear"},
                    "showPoints": "auto", "spanNulls": True,
                    "stacking": {"group": "A", "mode": "none"},
                    "thresholdsStyle": {"mode": "off"}
                },
                "mappings": [],
                "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
                "unit": unit
            },
            "overrides": []
        },
        "options": {
            "legend": {"calcs": [], "displayMode": "table", "placement": "bottom", "showLegend": True},
            "tooltip": {"mode": "multi", "sort": "desc"}
        },
        "targets": [{
            "datasource": DS,
            "format": "time_series",
            "rawQuery": True,
            "rawSql": sql,
            "refId": "A"
        }]
    }

def bar_panel(title, sql, grid, unit="USD", stacking="none", orient="horizontal"):
    return {
        "id": next_id(),
        "title": title,
        "type": "barchart",
        "gridPos": {"h": 8, "w": grid["w"], "x": grid["x"], "y": grid["y"]},
        "datasource": DS,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "axisBorderShow": False, "axisCenteredZero": False,
                    "axisColorMode": "text", "axisLabel": "", "axisPlacement": "auto",
                    "fillOpacity": 80, "gradientMode": "none",
                    "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                    "lineWidth": 1, "pointSize": 5,
                    "scaleDistribution": {"type": "linear"},
                    "showPoints": "auto", "spanNulls": False,
                    "stacking": {"group": "A", "mode": stacking},
                    "thresholdsStyle": {"mode": "off"}
                },
                "mappings": [],
                "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
                "unit": unit
            },
            "overrides": []
        },
        "options": {
            "groupWidth": 0.7,
            "legend": {"calcs": [], "displayMode": "list", "placement": "bottom", "showLegend": False},
            "orientation": orient,
            "showValue": "auto",
            "tooltip": {"mode": "single", "sort": "none"},
            "xTickLabelRotation": 0
        },
        "targets": [{
            "datasource": DS,
            "format": "table",
            "rawQuery": True,
            "rawSql": sql,
            "refId": "A"
        }]
    }

def table_panel(title, sql, grid, unit="USD", overrides=None):
    if overrides is None:
        overrides = []
    return {
        "id": next_id(),
        "title": title,
        "type": "table",
        "gridPos": {"h": 8, "w": grid["w"], "x": grid["x"], "y": grid["y"]},
        "datasource": DS,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "custom": {"align": "auto", "cellOptions": {"type": "auto"}, "inspect": False},
                "mappings": [],
                "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
                "unit": unit
            },
            "overrides": overrides
        },
        "options": {
            "footer": {"countRows": False, "fields": "", "reducer": ["sum"], "show": False},
            "frameIndex": 0, "showHeader": True,
            "sortBy": [{"desc": True, "displayName": "total_cost"}]
        },
        "targets": [{
            "datasource": DS,
            "format": "table",
            "rawQuery": True,
            "rawSql": sql,
            "refId": "A"
        }]
    }

def pie_panel(title, sql, grid, unit="USD"):
    return {
        "id": next_id(),
        "title": title,
        "type": "piechart",
        "gridPos": {"h": 8, "w": grid["w"], "x": grid["x"], "y": grid["y"]},
        "datasource": DS,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {"hideFrom": {"legend": False, "tooltip": False, "viz": False}},
                "mappings": [],
                "unit": unit
            },
            "overrides": []
        },
        "options": {
            "displayLabels": ["name", "value", "percent"],
            "legend": {"displayMode": "table", "placement": "right", "showLegend": True, "values": ["value", "percent"]},
            "pieType": "pie",
            "reduceOptions": {"calcs": ["sum"], "fields": "", "values": False},
            "tooltip": {"mode": "single", "sort": "none"}
        },
        "targets": [{
            "datasource": DS,
            "format": "table",
            "rawQuery": True,
            "rawSql": sql,
            "refId": "A"
        }]
    }

V = VAR_FILTERS + "\n  " + PROJECT_FILTER

# Row 1: Key Stats (6 stats, 24col / 6 = 4col each)
y = 0
panels.append(stat_panel(
    "MTD Cost",
    f"SELECT ROUND(SUM(COALESCE(NULLIF(net_cost_usd, 0), cost_usd))::numeric, 2) as mtd\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND usage_start >= date_trunc('month', current_date)\n  {V}",
    {"w": 4, "x": 0, "y": y},
    unit="USD", thresh_steps=[{"color": "green", "value": None}, {"color": "orange", "value": 500}, {"color": "red", "value": 1000}]
))
panels.append(stat_panel(
    "Previous Month",
    f"SELECT ROUND(SUM(COALESCE(NULLIF(net_cost_usd, 0), cost_usd))::numeric, 2) as prev\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND usage_start >= date_trunc('month', current_date - INTERVAL '1 month')\n  AND usage_start < date_trunc('month', current_date)\n  {V}",
    {"w": 4, "x": 4, "y": y},
    unit="USD", thresh_steps=[{"color": "green", "value": None}, {"color": "orange", "value": 500}, {"color": "red", "value": 1000}]
))
panels.append(stat_panel(
    "MoM Growth",
    f"WITH days_elapsed AS (\n  SELECT EXTRACT(DAY FROM current_date)::int AS n\n),\nmtd AS (\n  SELECT SUM(COALESCE(NULLIF(net_cost_usd, 0), cost_usd)) as val\n  FROM {PREFIX}, days_elapsed\n  {LLM_FILTER_AND}\n    AND usage_start >= date_trunc('month', current_date)\n    AND usage_start < date_trunc('month', current_date) + (n || ' days')::interval\n    {V}\n),\nprev AS (\n  SELECT SUM(COALESCE(NULLIF(net_cost_usd, 0), cost_usd)) as val\n  FROM {PREFIX}, days_elapsed\n  {LLM_FILTER_AND}\n    AND usage_start >= date_trunc('month', current_date - INTERVAL '1 month')\n    AND usage_start < date_trunc('month', current_date - INTERVAL '1 month') + (n || ' days')::interval\n    {V}\n)\nSELECT ROUND(((mtd.val - prev.val) / NULLIF(prev.val, 0)) * 100, 2) as growth\nFROM mtd, prev",
    {"w": 4, "x": 8, "y": y},
    unit="percent", decimals=2, thresh_steps=[{"color": "green", "value": None}, {"color": "orange", "value": 10}, {"color": "red", "value": 20}]
))
panels.append(stat_panel(
    "Total Tokens MTD",
    f"SELECT SUM(total_tokens) as tokens\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND usage_start >= date_trunc('month', current_date)\n  {V}",
    {"w": 4, "x": 12, "y": y},
    unit="short", decimals=1, thresh_steps=[{"color": "green", "value": None}]
))
panels.append(stat_panel(
    "Cost / 1M Tokens",
    f"WITH totals AS (\n  SELECT SUM(COALESCE(NULLIF(net_cost_usd, 0), cost_usd)) as total_cost,\n         SUM(total_tokens) as total_tokens\n  FROM {PREFIX}\n  {LLM_FILTER_AND}\n    AND usage_start >= date_trunc('month', current_date)\n    {V}\n)\nSELECT ROUND((total_cost / NULLIF(total_tokens, 0) * 1000000)::numeric, 2) as cost_per_1m\nFROM totals",
    {"w": 4, "x": 16, "y": y},
    unit="USD", decimals=2, thresh_steps=[{"color": "green", "value": None}, {"color": "orange", "value": 5}, {"color": "red", "value": 15}]
))
panels.append(stat_panel(
    "Avg Latency",
    f"SELECT ROUND(AVG(latency_ms)::numeric, 0) as avg_latency\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND usage_start >= date_trunc('month', current_date)\n  AND latency_ms IS NOT NULL\n  {V}",
    {"w": 4, "x": 20, "y": y},
    unit="ms", decimals=0, thresh_steps=[{"color": "green", "value": None}, {"color": "orange", "value": 2000}, {"color": "red", "value": 5000}]
))

# Row 2: Time series (2 panels, 12col each)
y = 4
panels.append(time_series_panel(
    "Daily Cost by Model",
    f"SELECT\n  DATE(usage_start) as time,\n  model_name as metric,\n  ROUND(SUM(COALESCE(NULLIF(net_cost_usd, 0), cost_usd))::numeric, 2) as value\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND $__timeFilter(usage_start)\n  {V}\nGROUP BY 1, 2\nORDER BY 1, 2",
    {"w": 12, "x": 0, "y": y},
    unit="USD"
))
panels.append(time_series_panel(
    "Daily Token Volume by Model",
    f"SELECT\n  DATE(usage_start) as time,\n  model_name as metric,\n  SUM(total_tokens) as value\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND $__timeFilter(usage_start)\n  {V}\nGROUP BY 1, 2\nORDER BY 1, 2",
    {"w": 12, "x": 12, "y": y},
    unit="short"
))

# Row 3: Breakdowns (3 panels, 8col each)
y = 12
panels.append(bar_panel(
    "Cost by Model",
    f"SELECT\n  model_name,\n  ROUND(SUM(COALESCE(NULLIF(net_cost_usd, 0), cost_usd))::numeric, 2) as total_cost\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND $__timeFilter(usage_start)\n  {V}\nGROUP BY 1\nORDER BY 2 DESC",
    {"w": 8, "x": 0, "y": y},
    unit="USD", orient="horizontal"
))
panels.append(bar_panel(
    "Token Ratio by Model (Input vs Output)",
    f"SELECT\n  model_name,\n  SUM(input_tokens) as input_tokens,\n  SUM(output_tokens) as output_tokens\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND $__timeFilter(usage_start)\n  {V}\nGROUP BY 1\nORDER BY 2 DESC",
    {"w": 8, "x": 8, "y": y},
    unit="short", stacking="normal", orient="auto"
))
panels.append(pie_panel(
    "Cost Share by Model",
    f"SELECT\n  model_name,\n  ROUND(SUM(COALESCE(NULLIF(net_cost_usd, 0), cost_usd))::numeric, 2) as total_cost\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND $__timeFilter(usage_start)\n  {V}\nGROUP BY 1\nORDER BY 2 DESC",
    {"w": 8, "x": 16, "y": y},
    unit="USD"
))

# Row 4: Model Performance Table (full width)
y = 20
panels.append(table_panel(
    "Model Performance Detail",
    f"SELECT\n  model_name,\n  ROUND(SUM(COALESCE(NULLIF(net_cost_usd, 0), cost_usd))::numeric, 2) as total_cost,\n  SUM(total_tokens) as total_tokens,\n  SUM(input_tokens) as input_tokens,\n  SUM(output_tokens) as output_tokens,\n  ROUND(AVG(latency_ms)::numeric, 0) as avg_latency_ms,\n  ROUND((SUM(COALESCE(NULLIF(net_cost_usd, 0), cost_usd)) / NULLIF(SUM(total_tokens), 0) * 1000000)::numeric, 4) as cost_per_1m_tokens,\n  COUNT(*) as total_requests\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND $__timeFilter(usage_start)\n  {V}\nGROUP BY 1\nORDER BY total_cost DESC",
    {"w": 24, "x": 0, "y": y},
    unit="USD",
    overrides=[
        {"matcher": {"id": "byName", "options": "total_tokens"}, "properties": [{"id": "unit", "value": "short"}]},
        {"matcher": {"id": "byName", "options": "input_tokens"}, "properties": [{"id": "unit", "value": "short"}]},
        {"matcher": {"id": "byName", "options": "output_tokens"}, "properties": [{"id": "unit", "value": "short"}]},
        {"matcher": {"id": "byName", "options": "avg_latency_ms"}, "properties": [{"id": "unit", "value": "ms"}]},
        {"matcher": {"id": "byName", "options": "cost_per_1m_tokens"}, "properties": [{"id": "unit", "value": "USD"}, {"id": "custom.cellOptions", "value": {"mode": "basic", "type": "color-background"}}]},
        {"matcher": {"id": "byName", "options": "total_requests"}, "properties": [{"id": "unit", "value": "short"}]}
    ]
))

# Row 5: Latency + Cost Efficiency Trends
y = 28
panels.append(time_series_panel(
    "Latency Trend by Model",
    f"SELECT\n  DATE(usage_start) as time,\n  model_name as metric,\n  ROUND(AVG(latency_ms)::numeric, 0) as value\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND $__timeFilter(usage_start)\n  AND latency_ms IS NOT NULL\n  {V}\nGROUP BY 1, 2\nORDER BY 1, 2",
    {"w": 12, "x": 0, "y": y},
    unit="ms", fill=40
))
panels.append(time_series_panel(
    "Daily Cost per 1M Tokens",
    f"SELECT\n  DATE(usage_start) as time,\n  model_name as metric,\n  ROUND((SUM(cost_usd) / NULLIF(SUM(total_tokens), 0) * 1000000)::numeric, 4) as value\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND $__timeFilter(usage_start)\n  AND total_tokens > 0\n  {V}\nGROUP BY 1, 2\nORDER BY 1, 2",
    {"w": 12, "x": 12, "y": y},
    unit="USD", fill=40
))

y = 36
panels.append(time_series_panel(
    "Daily Cost Anomaly Detection",
    f"SELECT\n  DATE(usage_start) as time,\n  ROUND(SUM(cost_usd)::numeric, 2) as value\nFROM {PREFIX}\n{LLM_FILTER_AND}\n  AND $__timeFilter(usage_start)\n  {V}\nGROUP BY 1\nORDER BY 1",
    {"w": 24, "x": 0, "y": y},
    unit="USD",
    fill=60
))
# Add threshold as second query
anomaly_panel = panels[-1]
anomaly_panel["targets"].append({
    "datasource": DS,
    "format": "time_series",
    "rawQuery": True,
    "rawSql": f"SELECT\n  null as time,\n  ROUND((AVG(daily_cost) + 2 * STDDEV(daily_cost))::numeric, 2) as value\nFROM (\n  SELECT SUM(cost_usd) as daily_cost\n  FROM {PREFIX}\n  {LLM_FILTER_AND}\n    AND usage_start >= now() - INTERVAL '60 days'\n    {V}\n  GROUP BY DATE(usage_start)\n) sub",
    "refId": "threshold"
})

# Fix schemaVersion dedup
d["dashboard"]["schemaVersion"] = 39

with open("grafana/llm-cost-v2.json", "w") as f:
    json.dump(d, f, indent=2)

print(f"Generated grafana/llm-cost-v2.json with {len(panels)} panels")
