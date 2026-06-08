"""Wastage scan runner (Phase 5).

Orchestrates a full scan cycle:

1. Open a ``wastage_scan_runs`` record with ``status='running'``.
2. Iterate every inventory row through every rule in the REGISTRY.
3. Upsert each Finding into ``resource_wastage``:
   - New finding → ``first_seen_at = now()``, ``status = 'open'``
   - Existing finding → bump ``last_seen_at``, refresh ``evidence`` and
     ``estimated_monthly_usd``; preserve ``status`` (acked/ignored unchanged).
4. Auto-resolve findings absent for N consecutive runs (default N=3):
   compare ``last_seen_at`` against the ``started_at`` of the run that is N
   runs before the current one (oldest of the last N runs).
5. Close the scan-run record with ``status='done'`` and the findings count.

Usage (programmatic)::

    from backend.app.wastage.runner import run_scan

    run_id = run_scan(
        conn=psycopg_conn,
        provider="azure",
        inventory_rows=my_rows,   # iterable[dict] from azure_inventory
    )

Usage (CLI)::

    python -m backend.app.wastage.runner --provider azure \\
        --subscription-id <id> [--tenant-id ...] [--client-id ...] [--client-secret ...]

Public surface for Agent C (API/UI):
  - ``run_scan(conn, provider, inventory_rows, *, consecutive_miss_threshold=3) -> str``
    Returns the UUID of the completed ``wastage_scan_runs`` row.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import psycopg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQL statements
# ---------------------------------------------------------------------------

_INSERT_SCAN_RUN = """
INSERT INTO wastage_scan_runs (id, provider, started_at, status)
VALUES (%s, %s, %s, 'running')
"""

_CLOSE_SCAN_RUN = """
UPDATE wastage_scan_runs
SET finished_at = %s,
    status = %s,
    findings_count = %s,
    error = %s
WHERE id = %s
"""

# ON CONFLICT upsert on the unique key (provider, resource_id, rule_id).
# - New rows get first_seen_at = now(), status = 'open'.
# - Existing rows: only bump last_seen_at, evidence, estimated_monthly_usd.
#   status, first_seen_at are preserved (DO NOT overwrite with EXCLUDED.*).
_UPSERT_FINDING = """
INSERT INTO resource_wastage (
    finding_id,
    provider, account_id, resource_group, region,
    resource_id, resource_type, rule_id,
    severity, category,
    estimated_monthly_usd, currency,
    evidence, tags,
    first_seen_at, last_seen_at, status
)
VALUES (
    %(finding_id)s,
    %(provider)s, %(account_id)s, %(resource_group)s, %(region)s,
    %(resource_id)s, %(resource_type)s, %(rule_id)s,
    %(severity)s, %(category)s,
    %(estimated_monthly_usd)s, 'USD',
    %(evidence)s, %(tags)s,
    %(now)s, %(now)s, 'open'
)
ON CONFLICT (provider, resource_id, rule_id)
DO UPDATE SET
    last_seen_at          = EXCLUDED.last_seen_at,
    evidence              = EXCLUDED.evidence,
    estimated_monthly_usd = EXCLUDED.estimated_monthly_usd,
    tags                  = EXCLUDED.tags
"""

# Resolve findings whose last_seen_at is older than the cutoff run's started_at.
# Only 'open' findings are auto-resolved (acked/ignored are left alone).
_AUTO_RESOLVE = """
UPDATE resource_wastage
SET status = 'resolved'
WHERE provider = %s
  AND status = 'open'
  AND last_seen_at < %s
"""

_GET_CUTOFF_RUN = """
SELECT started_at
FROM wastage_scan_runs
WHERE provider = %s
  AND status = 'done'
ORDER BY started_at DESC
LIMIT 1
OFFSET %s
"""


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------


def run_scan(
    conn: psycopg.Connection,
    provider: str,
    inventory_rows: Iterable[dict[str, Any]],
    *,
    consecutive_miss_threshold: int = 3,
) -> str:
    """Run a full wastage scan and persist results.

    Args:
        conn: Open psycopg v3 connection (sync). The caller retains ownership
              and must close it.
        provider: Cloud provider label, e.g. ``"azure"``.
        inventory_rows: Iterable of normalised inventory dicts (one per
                        resource) as produced by
                        ``extractors.inventory.azure_inventory.stream_inventory``.
        consecutive_miss_threshold: Number of consecutive missed runs before a
                                    finding is auto-resolved (default 3).

    Returns:
        UUID string of the completed ``wastage_scan_runs`` row.

    Raises:
        Exception: On unrecoverable DB errors. The scan-run record is marked
                   ``status='error'`` before propagating.
    """
    # Import the rule registry and pricing lazily to avoid circular imports
    # when this module is imported from tests.
    from backend.app.wastage import pricing as pricing_module
    from backend.app.wastage.rules import REGISTRY

    # Import all provider-specific rule modules so they register themselves.
    _ensure_azure_rules_loaded()

    run_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    try:
        with conn.cursor() as cur:
            cur.execute(_INSERT_SCAN_RUN, (run_id, provider, now))
        conn.commit()
    except psycopg.Error:
        logger.exception("Failed to create scan run record")
        raise

    findings_count = 0
    error_msg: str | None = None

    try:
        provider_rules = {
            rule_id: rule_obj
            for rule_id, rule_obj in REGISTRY.items()
            if rule_id.startswith(f"{provider}.")
        }

        if not provider_rules:
            logger.warning(
                "No rules registered for provider %r — scan will produce no findings",
                provider,
            )

        with conn.cursor() as cur:
            for row in inventory_rows:
                for rule_id, rule_obj in provider_rules.items():
                    try:
                        finding = rule_obj.fn(row, pricing_module)
                    except Exception:
                        logger.exception(
                            "Rule %r raised an exception on row %r — skipping",
                            rule_id,
                            row.get("resource_id"),
                        )
                        continue

                    if finding is None:
                        continue

                    params = _finding_to_params(finding, now)
                    cur.execute(_UPSERT_FINDING, params)
                    findings_count += 1

        conn.commit()
        logger.info(
            "Scan run %s: %d finding(s) upserted for provider=%s",
            run_id,
            findings_count,
            provider,
        )

        # Auto-resolve stale findings
        _auto_resolve_stale(conn, provider, run_id, consecutive_miss_threshold, now)

    except Exception as exc:
        error_msg = str(exc)
        logger.exception("Scan run %s failed: %s", run_id, error_msg)
        try:
            conn.rollback()
        except Exception:
            pass
        _close_scan_run(conn, run_id, "error", 0, error_msg)
        raise
    else:
        _close_scan_run(conn, run_id, "done", findings_count, None)

    return run_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finding_to_params(finding: Any, now: datetime) -> dict[str, Any]:
    """Convert a Finding dataclass into a dict for the upsert SQL."""
    cost = finding.estimated_monthly_usd
    if not isinstance(cost, Decimal):
        cost = Decimal(str(cost))

    return {
        "finding_id": finding.finding_id,
        "provider": finding.provider,
        "account_id": finding.account_id,
        "resource_group": finding.resource_group,
        "region": finding.region,
        "resource_id": finding.resource_id,
        "resource_type": finding.resource_type,
        "rule_id": finding.rule_id,
        "severity": finding.severity,
        "category": finding.category,
        "estimated_monthly_usd": float(cost),
        "evidence": json.dumps(finding.evidence),
        "tags": json.dumps(finding.tags),
        "now": now,
    }


def _close_scan_run(
    conn: psycopg.Connection,
    run_id: str,
    status: str,
    findings_count: int,
    error: str | None,
) -> None:
    """Update the scan-run record to finished state."""
    finished_at = datetime.now(UTC)
    try:
        with conn.cursor() as cur:
            cur.execute(
                _CLOSE_SCAN_RUN,
                (finished_at, status, findings_count, error, run_id),
            )
        conn.commit()
    except psycopg.Error:
        logger.exception("Failed to close scan run record %s", run_id)


def _auto_resolve_stale(
    conn: psycopg.Connection,
    provider: str,
    current_run_id: str,
    threshold: int,
    _now: datetime,
) -> None:
    """Mark open findings as 'resolved' if absent for *threshold* consecutive runs.

    Strategy: look up the ``started_at`` of the run that is ``threshold``
    positions back in the done-runs history for this provider.  Any finding
    whose ``last_seen_at < that cutoff`` has been missed in at least
    *threshold* consecutive runs and should be resolved.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                _GET_CUTOFF_RUN,
                (provider, threshold - 1),  # OFFSET 0 = most recent; N-1 = Nth
            )
            row = cur.fetchone()

        if row is None:
            # Fewer than *threshold* completed runs exist — not enough history yet
            logger.debug(
                "Not enough completed runs (need %d) to auto-resolve findings for %s",
                threshold,
                provider,
            )
            return

        # row may be a dict (dict_row) or a plain tuple depending on cursor config
        if isinstance(row, dict):
            cutoff_dt: datetime = row["started_at"]
        else:
            cutoff_dt = row[0]

        with conn.cursor() as cur:
            cur.execute(_AUTO_RESOLVE, (provider, cutoff_dt))
            resolved = cur.rowcount

        conn.commit()

        if resolved:
            logger.info(
                "Auto-resolved %d stale finding(s) for provider=%s "
                "(last_seen_at < %s)",
                resolved,
                provider,
                cutoff_dt.isoformat(),
            )
    except psycopg.Error:
        logger.exception("Failed to auto-resolve stale findings for %s", provider)
        try:
            conn.rollback()
        except Exception:
            pass


def _ensure_azure_rules_loaded() -> None:
    """Import Azure rule module to trigger REGISTRY population."""
    try:
        import backend.app.wastage.rules.azure  # noqa: F401
    except ImportError:
        logger.warning("Could not import backend.app.wastage.rules.azure")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def _cli_main() -> None:
    import argparse
    import os
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Run a wastage inventory scan and persist findings to PostgreSQL."
    )
    parser.add_argument("--provider", default="azure", choices=["azure"])
    parser.add_argument(
        "--subscription-id",
        default=os.getenv("AZURE_SUBSCRIPTION_ID"),
        help="Azure subscription ID (or set AZURE_SUBSCRIPTION_ID)",
    )
    parser.add_argument("--tenant-id", default=os.getenv("AZURE_TENANT_ID"))
    parser.add_argument("--client-id", default=os.getenv("AZURE_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.getenv("AZURE_CLIENT_SECRET"))
    parser.add_argument(
        "--pg-dsn",
        default=os.getenv("PG_DSN"),
        help="PostgreSQL DSN (or set PG_DSN)",
    )
    parser.add_argument(
        "--miss-threshold",
        type=int,
        default=3,
        help="Consecutive missed runs before a finding is auto-resolved (default 3)",
    )
    args = parser.parse_args()

    if not args.pg_dsn:
        print("ERROR: PG_DSN is required (env or --pg-dsn)", file=sys.stderr)
        sys.exit(1)

    if args.provider == "azure":
        if not args.subscription_id:
            print(
                "ERROR: --subscription-id or AZURE_SUBSCRIPTION_ID is required",
                file=sys.stderr,
            )
            sys.exit(1)

        from extractors.inventory.azure_inventory import stream_inventory

        rows = stream_inventory(
            subscription_ids=[args.subscription_id],
            tenant_id=args.tenant_id,
            client_id=args.client_id,
            client_secret=args.client_secret,
        )
    else:
        print(f"ERROR: unsupported provider {args.provider!r}", file=sys.stderr)
        sys.exit(1)

    with psycopg.connect(args.pg_dsn) as conn:
        run_id = run_scan(
            conn=conn,
            provider=args.provider,
            inventory_rows=rows,
            consecutive_miss_threshold=args.miss_threshold,
        )

    print(f"Scan complete. Run ID: {run_id}")


if __name__ == "__main__":
    _cli_main()
