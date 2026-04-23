# FinOps Queries

Ready-to-run SQL queries against the `cost_records` data model. Connect with:

```bash
psql $PG_DSN
```

---

## Overview & Totals

### Month-to-date cost by provider

```sql
SELECT
    provider,
    ROUND(SUM(cost_usd)::numeric, 2)     AS cost_usd,
    ROUND(SUM(discount_usd)::numeric, 2) AS discount_usd,
    ROUND(SUM(net_cost_usd)::numeric, 2) AS net_cost_usd,
    COUNT(*)                              AS records
FROM cost_records
WHERE usage_start >= date_trunc('month', now())
GROUP BY provider
ORDER BY cost_usd DESC;
```

### Total spend last 30 days

```sql
SELECT
    ROUND(SUM(cost_usd)::numeric, 2)     AS total_usd,
    ROUND(SUM(discount_usd)::numeric, 2) AS total_discount_usd,
    COUNT(DISTINCT resource_id)          AS resource_groups,
    COUNT(DISTINCT project_id)           AS projects,
    MIN(usage_start)::date               AS from_date,
    MAX(usage_end)::date                 AS to_date
FROM cost_records
WHERE usage_start >= now() - interval '30 days';
```

---

## Daily Trends

### Daily cost per provider (last 30 days)

```sql
SELECT
    usage_start::date     AS day,
    provider,
    ROUND(SUM(cost_usd)::numeric, 2) AS cost_usd
FROM cost_records
WHERE usage_start >= now() - interval '30 days'
GROUP BY 1, 2
ORDER BY 1, 2;
```

### Daily total cost with 7-day rolling average

```sql
SELECT
    day,
    cost_usd,
    ROUND(
        AVG(cost_usd) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),
        2
    ) AS rolling_7d_avg
FROM (
    SELECT
        usage_start::date             AS day,
        ROUND(SUM(cost_usd)::numeric, 2) AS cost_usd
    FROM cost_records
    WHERE usage_start >= now() - interval '30 days'
    GROUP BY 1
) d
ORDER BY day;
```

### Week-over-week cost change by provider

```sql
SELECT
    provider,
    ROUND(SUM(CASE WHEN usage_start >= now() - interval '7 days'  THEN cost_usd ELSE 0 END)::numeric, 2) AS this_week,
    ROUND(SUM(CASE WHEN usage_start BETWEEN now() - interval '14 days' AND now() - interval '7 days' THEN cost_usd ELSE 0 END)::numeric, 2) AS last_week,
    ROUND((
        SUM(CASE WHEN usage_start >= now() - interval '7 days' THEN cost_usd ELSE 0 END) -
        SUM(CASE WHEN usage_start BETWEEN now() - interval '14 days' AND now() - interval '7 days' THEN cost_usd ELSE 0 END)
    )::numeric, 2) AS delta_usd
FROM cost_records
WHERE usage_start >= now() - interval '14 days'
GROUP BY provider
ORDER BY delta_usd DESC;
```

---

## Cost Breakdown

### Cost by service category

```sql
SELECT
    service_category,
    provider,
    ROUND(SUM(cost_usd)::numeric, 2) AS cost_usd,
    ROUND(100.0 * SUM(cost_usd) / SUM(SUM(cost_usd)) OVER (), 1) AS pct
FROM cost_records
WHERE usage_start >= now() - interval '30 days'
GROUP BY 1, 2
ORDER BY cost_usd DESC;
```

### Top 15 most expensive services (SKU-level)

```sql
SELECT
    provider,
    service_category,
    service_name,
    ROUND(SUM(cost_usd)::numeric, 2) AS cost_usd,
    COUNT(*)                          AS days
FROM cost_records
WHERE usage_start >= now() - interval '30 days'
GROUP BY 1, 2, 3
ORDER BY cost_usd DESC
LIMIT 15;
```

### Cost by resource group / resource

```sql
SELECT
    provider,
    resource_id,
    resource_type,
    ROUND(SUM(cost_usd)::numeric, 2) AS cost_usd
FROM cost_records
WHERE usage_start >= now() - interval '30 days'
  AND resource_id IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY cost_usd DESC
LIMIT 20;
```

### Cost by region

```sql
SELECT
    provider,
    COALESCE(region, 'unknown') AS region,
    ROUND(SUM(cost_usd)::numeric, 2) AS cost_usd
FROM cost_records
WHERE usage_start >= now() - interval '30 days'
GROUP BY 1, 2
ORDER BY cost_usd DESC;
```

### Charge type breakdown (Usage / Tax / Credit)

```sql
SELECT
    provider,
    COALESCE(charge_type, 'unknown') AS charge_type,
    ROUND(SUM(cost_usd)::numeric, 2) AS cost_usd,
    COUNT(*)                          AS records
FROM cost_records
WHERE usage_start >= now() - interval '30 days'
GROUP BY 1, 2
ORDER BY 1, cost_usd DESC;
```

---

## Project Tracking

### Cost vs budget per project (MTD)

```sql
SELECT
    p.name                                      AS project,
    p.cost_center,
    ROUND(p.budget_cap::numeric, 2)             AS budget_usd,
    ROUND(SUM(c.cost_usd)::numeric, 2)          AS spent_usd,
    ROUND(100.0 * SUM(c.cost_usd) / NULLIF(p.budget_cap, 0), 1) AS pct_used,
    CASE
        WHEN SUM(c.cost_usd) > p.budget_cap THEN 'OVER BUDGET'
        WHEN SUM(c.cost_usd) > p.budget_cap * 0.8 THEN 'WARNING'
        ELSE 'OK'
    END AS status
FROM fin_projects p
LEFT JOIN cost_records c
    ON c.project_id = p.id
   AND c.usage_start >= date_trunc('month', now())
GROUP BY p.id, p.name, p.cost_center, p.budget_cap
ORDER BY pct_used DESC NULLS LAST;
```

### Top cost contributors per project (last 30 days)

```sql
SELECT
    project_id,
    service_name,
    ROUND(SUM(cost_usd)::numeric, 2) AS cost_usd
FROM cost_records
WHERE usage_start >= now() - interval '30 days'
  AND project_id IS NOT NULL
GROUP BY project_id, service_name
ORDER BY project_id, cost_usd DESC;
```

---

## LLM Cost & Usage

### LLM cost and token usage by model

```sql
SELECT
    service_name                                        AS model,
    ROUND(SUM(cost_usd)::numeric, 4)                   AS cost_usd,
    SUM(COALESCE(input_tokens, 0))                     AS input_tokens,
    SUM(COALESCE(output_tokens, 0))                    AS output_tokens,
    SUM(COALESCE(total_tokens, 0))                     AS total_tokens,
    ROUND(
        1000.0 * SUM(cost_usd) / NULLIF(SUM(total_tokens), 0),
        6
    )                                                  AS cost_per_1k_tokens
FROM cost_records
WHERE provider = 'llm'
  AND usage_start >= now() - interval '30 days'
GROUP BY service_name
ORDER BY cost_usd DESC;
```

### Daily LLM token burn

```sql
SELECT
    usage_start::date                        AS day,
    service_name                             AS model,
    SUM(COALESCE(total_tokens, 0))          AS total_tokens,
    ROUND(SUM(cost_usd)::numeric, 4)        AS cost_usd
FROM cost_records
WHERE provider = 'llm'
  AND usage_start >= now() - interval '30 days'
GROUP BY 1, 2
ORDER BY 1, 3 DESC;
```

### LLM avg latency by model

```sql
SELECT
    service_name                             AS model,
    COUNT(*)                                AS calls,
    ROUND(AVG(latency_ms)::numeric, 0)     AS avg_latency_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)::numeric, 0) AS p95_latency_ms,
    MAX(latency_ms)                         AS max_latency_ms
FROM cost_records
WHERE provider = 'llm'
  AND latency_ms IS NOT NULL
  AND usage_start >= now() - interval '30 days'
GROUP BY service_name
ORDER BY avg_latency_ms DESC;
```

---

## Anomaly Detection

### Days with abnormally high cost (> mean + 2σ)

```sql
WITH daily AS (
    SELECT
        usage_start::date AS day,
        SUM(cost_usd)     AS cost_usd
    FROM cost_records
    WHERE usage_start >= now() - interval '60 days'
    GROUP BY 1
),
stats AS (
    SELECT
        AVG(cost_usd)   AS mean,
        STDDEV(cost_usd) AS stddev
    FROM daily
)
SELECT
    d.day,
    ROUND(d.cost_usd::numeric, 2)              AS cost_usd,
    ROUND(s.mean::numeric, 2)                  AS mean_usd,
    ROUND((d.cost_usd - s.mean)::numeric, 2)   AS delta_usd,
    ROUND(((d.cost_usd - s.mean) / NULLIF(s.stddev, 0))::numeric, 2) AS z_score
FROM daily d, stats s
WHERE d.cost_usd > s.mean + 2 * s.stddev
ORDER BY d.day DESC;
```

### Fastest-growing services (last 7 days vs prior 7 days)

```sql
SELECT
    service_name,
    provider,
    ROUND(SUM(CASE WHEN usage_start >= now() - interval '7 days'
                   THEN cost_usd ELSE 0 END)::numeric, 2) AS this_week,
    ROUND(SUM(CASE WHEN usage_start BETWEEN now() - interval '14 days'
                                        AND now() - interval '7 days'
                   THEN cost_usd ELSE 0 END)::numeric, 2) AS last_week,
    ROUND((
        SUM(CASE WHEN usage_start >= now() - interval '7 days' THEN cost_usd ELSE 0 END) -
        SUM(CASE WHEN usage_start BETWEEN now() - interval '14 days' AND now() - interval '7 days' THEN cost_usd ELSE 0 END)
    )::numeric, 2) AS growth_usd
FROM cost_records
WHERE usage_start >= now() - interval '14 days'
GROUP BY service_name, provider
HAVING SUM(CASE WHEN usage_start BETWEEN now() - interval '14 days'
                                     AND now() - interval '7 days'
                THEN cost_usd ELSE 0 END) > 0
ORDER BY growth_usd DESC
LIMIT 10;
```

---

## Usage Metrics

### Top resources by usage quantity

```sql
SELECT
    provider,
    service_name,
    usage_unit,
    ROUND(SUM(usage_quantity)::numeric, 2) AS total_quantity,
    ROUND(SUM(cost_usd)::numeric, 2)       AS cost_usd,
    ROUND(SUM(cost_usd) / NULLIF(SUM(usage_quantity), 0)::numeric, 6) AS cost_per_unit
FROM cost_records
WHERE usage_start >= now() - interval '30 days'
  AND usage_quantity IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY total_quantity DESC
LIMIT 20;
```

---

## Extractor Health

### Latest extractor run status

```sql
SELECT
    extractor_name,
    status,
    records_extracted,
    last_run_ts,
    error_message
FROM extractor_health
ORDER BY last_run_ts DESC;
```

### Run history with duration

```sql
SELECT
    provider,
    extractor_type,
    status,
    records_extracted,
    started_at,
    finished_at,
    ROUND(EXTRACT(EPOCH FROM (finished_at - started_at)) / 60, 1) AS duration_min,
    LEFT(error_message, 100) AS error
FROM extractor_runs
ORDER BY started_at DESC
LIMIT 20;
```

### Success rate per provider (last 30 days)

```sql
SELECT
    provider,
    COUNT(*)                                                        AS total_runs,
    COUNT(*) FILTER (WHERE status = 'success')                     AS successful,
    COUNT(*) FILTER (WHERE status = 'failed')                      AS failed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'success') / COUNT(*), 1) AS success_rate_pct,
    SUM(records_extracted)                                          AS total_records
FROM extractor_runs
WHERE started_at >= now() - interval '30 days'
GROUP BY provider
ORDER BY total_runs DESC;
```
