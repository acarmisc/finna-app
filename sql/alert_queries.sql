-- =============================================================================
-- FinOps Multi-Cloud Monitoring — Alerting Queries
-- =============================================================================
-- These queries power alert rules for cost monitoring.
--
-- All queries target the PostgreSQL datasource "finops-pg" and are designed to
-- be used as SQL expressions (PostgreSQL datasource type).
--
-- PARAMETERIZATION
-- ----------------
-- Thresholds are expressed as SQL variables via a CTE at the top of each query
-- called `params`.  To adjust a threshold at provisioning time, change the
-- value in the `params` CTE.
--
-- SCHEMA DEPENDENCIES
-- -------------------
--   daily_costs       — materialized view (day, provider, project_id,
--                        service_category, service_name, model_name,
--                        total_cost, total_input_tokens, total_output_tokens,
--                        record_count)
--   cost_records      — partitioned table (see init.sql)
--   extractor_health  — (extractor_name, last_run_start, last_run_end,
--                        status, records_extracted, error_message, updated_at)
-- =============================================================================


-- =============================================================================
-- 1. DAILY COST SPIKE
-- =============================================================================
-- Compares today's aggregate net cost against the 7-day rolling average.
-- Flags when today's cost exceeds the average by more than SPIKE_PCT percent.
--
-- Parameters (in `params` CTE):
--   SPIKE_PCT         – percentage threshold for spike detection (default 30)
--   LOOKBACK_DAYS     – number of days in the baseline window (default 7)
--   MIN_BASELINE_COST – minimum baseline cost to avoid false positives on
--                        low-spend projects (default 10.00 USD)
--
-- Returns one row per provider+project when a spike is detected:
--   provider | project_id | today_cost | baseline_avg | spike_pct | threshold_pct
--
-- A statistical (mean + 2 std-dev) alternative lives in
-- docs/queries.md under "Anomaly Detection" — better for volatile
-- projects where a fixed percentage over/under-triggers; this fixed-
-- percentage version is the one wired into the live alert rule.
-- =============================================================================

WITH params AS (
    SELECT
        30   AS spike_pct,         -- flag if today > baseline * (1 + spike_pct/100)
        7    AS lookback_days,     -- days in baseline window (excludes today)
        10.0 AS min_baseline_cost  -- ignore projects with tiny baseline spend
),
today AS (
    SELECT
        dc.provider,
        dc.project_id,
        SUM(dc.total_cost) AS today_cost
    FROM daily_costs dc
    WHERE dc.day = CURRENT_DATE
    GROUP BY dc.provider, dc.project_id
),
baseline AS (
    SELECT
        dc.provider,
        dc.project_id,
        AVG(dc.daily_total) AS baseline_avg
    FROM (
        SELECT
            provider,
            project_id,
            day,
            SUM(total_cost) AS daily_total
        FROM daily_costs
        WHERE day >= CURRENT_DATE - (SELECT lookback_days FROM params)
          AND day <  CURRENT_DATE
        GROUP BY provider, project_id, day
    ) dc
    GROUP BY dc.provider, dc.project_id
    HAVING AVG(dc.daily_total) >= (SELECT min_baseline_cost FROM params)
)
SELECT
    t.provider,
    t.project_id,
    ROUND(t.today_cost, 2)                      AS today_cost,
    ROUND(b.baseline_avg, 2)                    AS baseline_avg,
    ROUND(
        ((t.today_cost - b.baseline_avg) / b.baseline_avg) * 100,
        1
    )                                           AS spike_pct,
    p.spike_pct                                 AS threshold_pct
FROM today t
JOIN baseline b
    ON t.provider  = b.provider
   AND t.project_id = b.project_id
CROSS JOIN params p
WHERE t.today_cost > b.baseline_avg * (1 + p.spike_pct / 100.0);


-- =============================================================================
-- 2. MONTHLY BUDGET THRESHOLD
-- =============================================================================
-- Calculates month-to-date (MTD) spend and compares it against a monthly
-- budget.  Returns a row for every project that has crossed at least one
-- threshold tier (80 %, 90 %, 100 %).
--
-- Parameters (in `params` CTE):
--   BUDGET_OVERRIDE_USD – set to 0 to use per-project budgets from the
--                          project_budgets table (if it exists); set > 0 to
--                          apply a uniform budget across all projects.
--                          Default: 10000.00
--
-- Per-project budgets (optional):
--   If a table `project_budgets (project_id TEXT, monthly_budget NUMERIC)`
--   exists, each project's own budget is used when BUDGET_OVERRIDE_USD = 0.
--   If the table does not exist or a project has no row, BUDGET_OVERRIDE_USD
--   is used as a fallback.
--
-- Returns:
--   provider | project_id | mtd_spend | monthly_budget | pct_used | tier
-- =============================================================================

WITH params AS (
    SELECT
        10000.00 AS budget_override_usd  -- uniform fallback budget in USD
),
mtd AS (
    SELECT
        dc.provider,
        dc.project_id,
        SUM(dc.total_cost) AS mtd_spend
    FROM daily_costs dc
    WHERE dc.day >= DATE_TRUNC('month', CURRENT_DATE)::date
      AND dc.day <  CURRENT_DATE
    GROUP BY dc.provider, dc.project_id
),
budgets AS (
    SELECT
        m.provider,
        m.project_id,
        m.mtd_spend,
        COALESCE(
            pb.monthly_budget,
            (SELECT budget_override_usd FROM params)
        ) AS monthly_budget
    FROM mtd m
    LEFT JOIN project_budgets pb
        ON pb.project_id = m.project_id
)
SELECT
    b.provider,
    b.project_id,
    ROUND(b.mtd_spend, 2)       AS mtd_spend,
    ROUND(b.monthly_budget, 2)  AS monthly_budget,
    ROUND(
        (b.mtd_spend / b.monthly_budget) * 100,
        1
    )                            AS pct_used,
    CASE
        WHEN b.mtd_spend >= b.monthly_budget      THEN '100%'
        WHEN b.mtd_spend >= b.monthly_budget * 0.9 THEN '90%'
        WHEN b.mtd_spend >= b.monthly_budget * 0.8 THEN '80%'
    END                           AS tier
FROM budgets b
WHERE b.mtd_spend >= b.monthly_budget * 0.8
ORDER BY b.mtd_spend / b.monthly_budget DESC;


-- =============================================================================
-- 3. LLM COST PER PROJECT
-- =============================================================================
-- Flags any project whose LLM spend over the last 24 hours exceeds a
-- configurable daily threshold.  Useful for catching runaway model usage or
-- misconfigured retry loops.
--
-- Parameters (in `params` CTE):
--   LLM_DAILY_THRESHOLD_USD – max allowed LLM spend per project per day
--                               Default: 50.00
--   LOOKBACK_HOURS          – rolling window in hours (default 24)
--
-- Returns:
--   project_id | llm_spend_24h | threshold | over_by
-- =============================================================================

WITH params AS (
    SELECT
        50.00 AS llm_daily_threshold_usd,  -- max $/day per project
        24    AS lookback_hours             -- rolling window
),
llm_spend AS (
    SELECT
        cr.project_id,
        SUM(cr.net_cost_usd) AS llm_spend
    FROM cost_records cr
    WHERE cr.service_category = 'llm'
      AND cr.usage_start >= NOW() - (SELECT lookback_hours FROM params) * INTERVAL '1 hour'
    GROUP BY cr.project_id
)
SELECT
    ls.project_id,
    ROUND(ls.llm_spend, 2)              AS llm_spend_24h,
    p.llm_daily_threshold_usd            AS threshold,
    ROUND(ls.llm_spend - p.llm_daily_threshold_usd, 2) AS over_by
FROM llm_spend ls
CROSS JOIN params p
WHERE ls.llm_spend > p.llm_daily_threshold_usd
ORDER BY ls.llm_spend DESC;


-- =============================================================================
-- 4. EXTRACTOR HEALTH
-- =============================================================================
-- Detects extractors that have not completed a run within 2x their expected
-- run interval.  The expected interval is derived from the extractor name
-- convention:  "<cloud>_<interval>" (e.g. "gcp_daily", "azure_hourly").
--
-- Parameters (in `params` CTE):
--   DEFAULT_INTERVAL_MINUTES – fallback interval when the name does not
--                               encode one (default 60)
--   MULTIPLIER               – how many intervals before flagging
--                               (default 2, i.e. 2x the expected interval)
--
-- Returns:
--   extractor_name | last_run_end | expected_interval_min | elapsed_min | status
-- =============================================================================

WITH params AS (
    SELECT
        60 AS default_interval_minutes,  -- fallback when interval not in name
        2  AS multiplier                 -- flag at 2x expected interval
),
expected AS (
    SELECT
        eh.extractor_name,
        eh.last_run_end,
        eh.status,
        COALESCE(
            -- Parse interval from name convention: gcp_15min, azure_hourly, aws_daily
            CASE
                WHEN eh.extractor_name ~ '\d+min' THEN
                    (SUBSTRING(eh.extractor_name FROM '(\d+)min'))::int
                WHEN eh.extractor_name ~ 'hourly'  THEN 60
                WHEN eh.extractor_name ~ 'daily'   THEN 1440
                WHEN eh.extractor_name ~ 'weekly'  THEN 10080
                ELSE NULL
            END,
            (SELECT default_interval_minutes FROM params)
        ) AS expected_interval_min
    FROM extractor_health eh
),
elapsed AS (
    SELECT
        e.extractor_name,
        e.last_run_end,
        e.status,
        e.expected_interval_min,
        EXTRACT(EPOCH FROM (NOW() - e.last_run_end)) / 60.0 AS elapsed_min
    FROM expected e
    WHERE e.last_run_end IS NOT NULL
)
SELECT
    el.extractor_name,
    el.last_run_end,
    el.expected_interval_min,
    ROUND(el.elapsed_min, 1) AS elapsed_min,
    el.status,
    (SELECT multiplier FROM params) AS multiplier_threshold
FROM elapsed el
WHERE el.elapsed_min > el.expected_interval_min * (SELECT multiplier FROM params)
   -- Also flag extractors stuck in "running" state for too long
   OR (
       el.status = 'running'
       AND el.elapsed_min > el.expected_interval_min * (SELECT multiplier FROM params)
   )
ORDER BY el.elapsed_min DESC;


-- =============================================================================
-- HELPER: Create optional project_budgets table
-- =============================================================================
-- Uncomment and run this DDL if you want per-project monthly budgets
-- instead of the uniform BUDGET_OVERRIDE_USD fallback.
--
-- CREATE TABLE IF NOT EXISTS project_budgets (
--     project_id     TEXT PRIMARY KEY,
--     monthly_budget NUMERIC(18,2) NOT NULL
-- );
--
-- -- Example inserts
-- INSERT INTO project_budgets (project_id, monthly_budget) VALUES
--     ('finops-prod',    15000.00),
--     ('finops-staging',  3000.00),
--     ('analytics-prod', 12000.00),
--     ('ml-platform',    20000.00),
--     ('dev-sandbox',     2000.00);