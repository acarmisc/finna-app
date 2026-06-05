"""Wastage-specific database queries."""

from __future__ import annotations

import json
from typing import Any

from ..db import execute, insert_and_return, query_all, query_one


# ---------------------------------------------------------------------------
# Findings queries
# ---------------------------------------------------------------------------


def get_wastage_finding(finding_id: str) -> dict[str, Any] | None:
    """Fetch a single finding by its finding_id."""
    sql = """
        SELECT
            finding_id, provider, account_id, resource_group, region,
            resource_id, resource_type, rule_id, severity, category,
            estimated_monthly_usd, currency, evidence, first_seen_at,
            last_seen_at, status, tags
        FROM resource_wastage
        WHERE finding_id = %s
    """
    return query_one(sql, (finding_id,))


def list_wastage_findings(
    *,
    provider: str | None = None,
    severity: str | None = None,
    rule_id: str | None = None,
    status: str | None = None,
    account_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List findings with optional filters and pagination."""
    conditions: list[str] = []
    params: list[Any] = []

    if provider:
        conditions.append("provider = %s")
        params.append(provider)
    if severity:
        conditions.append("severity = %s")
        params.append(severity)
    if rule_id:
        conditions.append("rule_id = %s")
        params.append(rule_id)
    if status:
        conditions.append("status = %s")
        params.append(status)
    if account_id:
        conditions.append("account_id = %s")
        params.append(account_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            finding_id, provider, account_id, resource_group, region,
            resource_id, resource_type, rule_id, severity, category,
            estimated_monthly_usd, currency, evidence, first_seen_at,
            last_seen_at, status, tags
        FROM resource_wastage
        {where}
        ORDER BY estimated_monthly_usd DESC, first_seen_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    return query_all(sql, tuple(params))


def count_wastage_findings(
    *,
    provider: str | None = None,
    severity: str | None = None,
    rule_id: str | None = None,
    status: str | None = None,
    account_id: str | None = None,
) -> int:
    """Count findings matching the given filters."""
    conditions: list[str] = []
    params: list[Any] = []

    if provider:
        conditions.append("provider = %s")
        params.append(provider)
    if severity:
        conditions.append("severity = %s")
        params.append(severity)
    if rule_id:
        conditions.append("rule_id = %s")
        params.append(rule_id)
    if status:
        conditions.append("status = %s")
        params.append(status)
    if account_id:
        conditions.append("account_id = %s")
        params.append(account_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT COUNT(*) as cnt FROM resource_wastage {where}"
    row = query_one(sql, tuple(params) if params else None)
    return int(row["cnt"]) if row else 0


def get_wastage_summary() -> list[dict[str, Any]]:
    """Group findings by category and sum estimated savings."""
    sql = """
        SELECT
            category,
            COUNT(*) AS finding_count,
            SUM(estimated_monthly_usd) AS total_monthly_usd
        FROM resource_wastage
        WHERE status NOT IN ('resolved', 'ignored')
        GROUP BY category
        ORDER BY total_monthly_usd DESC
    """
    return query_all(sql)


# ---------------------------------------------------------------------------
# Status-change helpers
# ---------------------------------------------------------------------------


def set_finding_status(
    finding_id: str,
    status: str,
    extra_tags: dict[str, str] | None = None,
) -> bool:
    """Update finding status, optionally merging extra_tags.  Returns True if found."""
    if extra_tags:
        # Merge into existing tags via jsonb || operator
        sql = """
            UPDATE resource_wastage
            SET status = %s,
                tags = tags || %s::jsonb,
                last_seen_at = now()
            WHERE finding_id = %s
            RETURNING finding_id
        """
        row = query_one(sql, (status, json.dumps(extra_tags), finding_id))
    else:
        sql = """
            UPDATE resource_wastage
            SET status = %s,
                last_seen_at = now()
            WHERE finding_id = %s
            RETURNING finding_id
        """
        row = query_one(sql, (status, finding_id))
    return row is not None


# ---------------------------------------------------------------------------
# Scan run queries
# ---------------------------------------------------------------------------


def list_scan_runs(limit: int = 20) -> list[dict[str, Any]]:
    """List the most recent wastage scan runs."""
    sql = """
        SELECT id, provider, started_at, finished_at, status, findings_count, error
        FROM wastage_scan_runs
        ORDER BY started_at DESC
        LIMIT %s
    """
    return query_all(sql, (limit,))


def create_scan_run(provider: str, run_id: str) -> str:
    """Insert a new scan run record; returns the run id."""
    sql = """
        INSERT INTO wastage_scan_runs (id, provider, started_at, status)
        VALUES (%s, %s, now(), 'running')
        RETURNING id
    """
    return insert_and_return(sql, (run_id, provider))


def update_scan_run(
    run_id: str,
    status: str,
    findings_count: int | None = None,
    error: str | None = None,
) -> None:
    """Mark a scan run as done / error."""
    sql = """
        UPDATE wastage_scan_runs
        SET status = %s,
            finished_at = now(),
            findings_count = %s,
            error = %s
        WHERE id = %s
    """
    execute(sql, (status, findings_count, error, run_id))
