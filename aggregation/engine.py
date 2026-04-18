"""Aggregation engine for FinOps infrastructure metrics.

Receives raw data points, groups by configurable time window + resource,
computes statistical aggregates (avg, max, p95, sum, sample_count),
and batch-inserts results into the infra_metrics_agg PostgreSQL table.
"""

from __future__ import annotations

import logging
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import psycopg

logger = logging.getLogger("aggregation_engine")

# Supported window sizes in minutes
WINDOW_SIZES: dict[str, int] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
}


# ---------------------------------------------------------------------------
# Window alignment
# ---------------------------------------------------------------------------


def align_to_window(ts: datetime, window_minutes: int) -> datetime:
    """Round a timestamp down to the nearest window boundary.

    For example, with a 15-minute window:
        10:37:42 -> 10:30:00
        10:00:00 -> 10:00:00

    Args:
        ts: The timestamp to align.
        window_minutes: Window size in minutes.

    Returns:
        The aligned timestamp (floor of the window containing ts).
    """
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    # Total minutes since midnight
    total_minutes = ts.hour * 60 + ts.minute
    aligned_minutes = (total_minutes // window_minutes) * window_minutes

    aligned = ts.replace(
        hour=aligned_minutes // 60,
        minute=aligned_minutes % 60,
        second=0,
        microsecond=0,
    )
    return aligned


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------


def compute_percentile(sorted_values: list[float], percentile: float) -> float:
    """Compute a percentile from a sorted list of values.

    Uses the "nearest rank" / linear interpolation method.

    Args:
        sorted_values: Values sorted in ascending order.
        percentile: Percentile to compute (0-100).

    Returns:
        The percentile value.
    """
    if not sorted_values:
        return 0.0

    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]

    # Linear interpolation
    rank = (percentile / 100.0) * (n - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return sorted_values[lower]

    fraction = rank - lower
    return sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])


def compute_aggregates(values: list[float]) -> dict[str, Any]:
    """Compute statistical aggregates for a list of numeric values.

    Args:
        values: List of float values to aggregate.

    Returns:
        Dict with keys: avg, max, p95, sum, sample_count.
    """
    if not values:
        return {
            "avg": None,
            "max": None,
            "p95": None,
            "sum": None,
            "sample_count": 0,
        }

    n = len(values)
    total = sum(values)
    sorted_vals = sorted(values)

    return {
        "avg": total / n,
        "max": sorted_vals[-1],
        "p95": compute_percentile(sorted_vals, 95),
        "sum": total,
        "sample_count": n,
    }


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------


def aggregate(
    data_points: list[dict[str, Any]],
    window_minutes: int = 15,
) -> list[dict[str, Any]]:
    """Aggregate raw data points by time window and resource.

    Each data point is a dict with keys:
        - timestamp (datetime or ISO string)
        - metric_name (str): e.g. "cpu", "memory", "network_in", "network_out"
        - value (float): the measurement value
        - labels (dict): must include "provider", "project_id", "resource_id"

    For cumulative counters (metric names starting with "network_"), the
    engine reports ``sum`` as the primary aggregate. For gauges (cpu, memory),
    ``avg`` is the primary aggregate.

    Args:
        data_points: List of raw metric data points.
        window_minutes: Aggregation window size in minutes.

    Returns:
        List of aggregated records suitable for insertion into
        infra_metrics_agg.
    """
    if not data_points:
        return []

    # Group: (window_start, provider, project_id, resource_id) -> metric_name -> [values]
    groups: dict[tuple, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    # Also track window_end per group
    window_ends: dict[tuple, datetime] = {}

    for dp in data_points:
        ts = dp["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        window_start = align_to_window(ts, window_minutes)
        window_end = datetime.fromtimestamp(
            window_start.timestamp() + window_minutes * 60,
            tz=timezone.utc,
        )

        labels = dp.get("labels", {})
        provider = labels.get("provider", "unknown")
        project_id = labels.get("project_id", "unknown")
        resource_id = labels.get("resource_id", "unknown")
        metric_name = dp.get("metric_name", "unknown")
        value = float(dp.get("value", 0))

        group_key = (window_start, provider, project_id, resource_id)
        groups[group_key][metric_name].append(value)
        window_ends[group_key] = window_end

    # Build aggregated records
    results: list[dict[str, Any]] = []
    for group_key, metrics in groups.items():
        window_start, provider, project_id, resource_id = group_key
        window_end = window_ends[group_key]

        # Compute aggregates per metric
        cpu_vals = metrics.get("cpu", [])
        memory_vals = metrics.get("memory", [])
        network_in_vals = metrics.get("network_in", [])
        network_out_vals = metrics.get("network_out", [])

        cpu_agg = compute_aggregates(cpu_vals)
        mem_agg = compute_aggregates(memory_vals)
        net_in_agg = compute_aggregates(network_in_vals)
        net_out_agg = compute_aggregates(network_out_vals)

        # sample_count: use the metric with the most samples (typically cpu)
        all_counts = [
            cpu_agg["sample_count"],
            mem_agg["sample_count"],
            net_in_agg["sample_count"],
            net_out_agg["sample_count"],
        ]
        sample_count = max(all_counts) if any(c > 0 for c in all_counts) else 0

        record = {
            "window_start": window_start,
            "window_end": window_end,
            "provider": provider,
            "project_id": project_id,
            "resource_id": resource_id,
            "cpu_avg": cpu_agg["avg"],
            "cpu_p95": cpu_agg["p95"],
            "cpu_max": cpu_agg["max"],
            "memory_avg_bytes": int(mem_agg["avg"]) if mem_agg["avg"] is not None else None,
            "memory_max_bytes": int(mem_agg["max"]) if mem_agg["max"] is not None else None,
            "network_in_bytes": int(net_in_agg["sum"]) if net_in_agg["sum"] is not None else None,
            "network_out_bytes": int(net_out_agg["sum"]) if net_out_agg["sum"] is not None else None,
            "sample_count": sample_count,
        }
        results.append(record)

    logger.info(
        "Aggregated %d data points into %d records (window=%dm)",
        len(data_points),
        len(results),
        window_minutes,
    )
    return results


# ---------------------------------------------------------------------------
# Batch insert
# ---------------------------------------------------------------------------

_AGG_INSERT_SQL = """
INSERT INTO infra_metrics_agg (
    window_start, window_end, provider, project_id, resource_id,
    cpu_avg, cpu_p95, cpu_max,
    memory_avg_bytes, memory_max_bytes,
    network_in_bytes, network_out_bytes,
    sample_count
) VALUES (
    %(window_start)s, %(window_end)s, %(provider)s, %(project_id)s, %(resource_id)s,
    %(cpu_avg)s, %(cpu_p95)s, %(cpu_max)s,
    %(memory_avg_bytes)s, %(memory_max_bytes)s,
    %(network_in_bytes)s, %(network_out_bytes)s,
    %(sample_count)s
)
"""


def batch_insert(
    conn: psycopg.Connection,
    records: list[dict[str, Any]],
) -> int:
    """Insert aggregated records into infra_metrics_agg.

    Args:
        conn: Connection to the FinOps PostgreSQL database.
        records: List of aggregated record dicts from ``aggregate()``.

    Returns:
        Number of records inserted.
    """
    if not records:
        return 0

    with conn.cursor() as cur:
        cur.execute_batch(_AGG_INSERT_SQL, records)
    conn.commit()
    logger.info("Inserted %d aggregated records into infra_metrics_agg", len(records))
    return len(records)


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the aggregation engine as a standalone job.

    Reads PG_DSN from the environment. In production this would be
    triggered by a Cloud Run Job or pg_cron, and would read raw metrics
    from a staging table. For now this serves as a manual entrypoint.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    dsn = os.environ.get("PG_DSN")
    if not dsn:
        logger.error("PG_DSN environment variable is not set")
        return

    window = int(os.environ.get("AGG_WINDOW_MINUTES", "15"))

    logger.info("Aggregation engine started (window=%dm)", window)

    # In production, you would:
    # 1. Read raw data points from a staging table or message queue
    # 2. Call aggregate(data_points, window_minutes=window)
    # 3. Call batch_insert(conn, results)
    logger.info("Aggregation engine completed")


if __name__ == "__main__":
    main()
