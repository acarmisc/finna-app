"""Health-check utilities for FinOps extractor monitoring.

Provides functions to register extractor lifecycle events (started / succeeded /
failed) and to query the ``extractor_health`` table for current status and
stale-extractor detection.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("extractors.health_check")


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type((psycopg.OperationalError, psycopg.InterfaceError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _get_pg_connection(pg_dsn: str) -> psycopg.Connection:
    """Open a PostgreSQL connection with retry on transient errors."""
    return psycopg.connect(pg_dsn, row_factory=dict_row, autocommit=False)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Lifecycle markers
# ---------------------------------------------------------------------------

def mark_extractor_started(name: str, pg_dsn: str) -> None:
    """Register that an extractor has started running.

    Creates the row if it does not exist, or resets an existing row to
    ``status = 'running'``.
    """
    conn = _get_pg_connection(pg_dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO extractor_health
                    (extractor_name, last_run_start, status, records_extracted, updated_at)
                VALUES (%s, now(), 'running', 0, now())
                ON CONFLICT (extractor_name) DO UPDATE
                    SET last_run_start = now(),
                        status = 'running',
                        records_extracted = 0,
                        error_message = NULL,
                        updated_at = now()
                """,
                (name,),
            )
        conn.commit()
        logger.info("Marked extractor %s as started", name)
    except Exception:
        conn.rollback()
        logger.exception("Failed to mark extractor %s as started", name)
        raise
    finally:
        conn.close()


def mark_extractor_succeeded(name: str, records_count: int, pg_dsn: str) -> None:
    """Register that an extractor has completed successfully."""
    conn = _get_pg_connection(pg_dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE extractor_health
                SET last_run_end = now(),
                    status = 'success',
                    records_extracted = %s,
                    updated_at = now()
                WHERE extractor_name = %s
                """,
                (records_count, name),
            )
        conn.commit()
        logger.info("Marked extractor %s as succeeded (%d records)", name, records_count)
    except Exception:
        conn.rollback()
        logger.exception("Failed to mark extractor %s as succeeded", name)
        raise
    finally:
        conn.close()


def mark_extractor_failed(name: str, error_message: str, pg_dsn: str) -> None:
    """Register that an extractor has failed.

    Best-effort: if the database update itself fails, the exception is logged
    but not re-raised, so callers can still clean up after a failed extraction.
    """
    try:
        conn = _get_pg_connection(pg_dsn)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE extractor_health
                    SET last_run_end = now(),
                        status = 'failed',
                        error_message = %s,
                        updated_at = now()
                    WHERE extractor_name = %s
                    """,
                    (error_message[:2000], name),
                )
            conn.commit()
            logger.info("Marked extractor %s as failed: %s", name, error_message[:200])
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception:
        logger.exception("Failed to mark extractor %s as failed in health table", name)


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def get_extractor_status(pg_dsn: str) -> list[tuple[str, datetime, str, int]]:
    """Return a list of (name, last_run, status, records_count) for all extractors.

    ``last_run`` is ``last_run_end`` if available, otherwise ``last_run_start``.
    """
    conn = _get_pg_connection(pg_dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    extractor_name,
                    COALESCE(last_run_end, last_run_start) AS last_run,
                    status,
                    COALESCE(records_extracted, 0) AS records_count
                FROM extractor_health
                ORDER BY extractor_name
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        (row["extractor_name"], row["last_run"], row["status"], row["records_count"])  # type: ignore[call-overload]
        for row in rows
    ]


def detect_stale_extractors(
    expected_intervals: dict[str, timedelta],
    pg_dsn: str,
) -> list[tuple[str, str]]:
    """Return extractors that have not run within 2x their expected interval.

    Args:
        expected_intervals: Mapping of extractor name to expected run interval
            (e.g. ``{"gcp_billing": timedelta(hours=6), "exchange_rates": timedelta(days=1)}``).
        pg_dsn: PostgreSQL connection string.

    Returns:
        A list of ``(extractor_name, reason)`` tuples for stale extractors.
        Extractors not present in the ``extractor_health`` table at all are
        also reported as stale.
    """
    conn = _get_pg_connection(pg_dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT extractor_name, last_run_start, last_run_end, status
                FROM extractor_health
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    # Build a lookup from DB results
    db_lookup: dict[str, dict[str, Any]] = {
        row["extractor_name"]: dict(row) for row in rows  # type: ignore[call-overload]
    }

    stale: list[tuple[str, str]] = []
    now = datetime.now(timezone.utc)

    for name, interval in expected_intervals.items():
        threshold = interval * 2  # 2x the expected interval

        if name not in db_lookup:
            stale.append((name, "no health record found"))
            continue

        row = db_lookup[name]
        # Use last_run_end if it completed, otherwise last_run_start
        last_activity = row.get("last_run_end") or row.get("last_run_start")

        if last_activity is None:
            stale.append((name, "no run timestamp available"))
            continue

        # Ensure timezone-aware comparison
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)

        elapsed = now - last_activity
        if elapsed > threshold:
            stale.append(
                (
                    name,
                    f"last run {elapsed} ago (threshold {threshold})",
                )
            )

    return stale
