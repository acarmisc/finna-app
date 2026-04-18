"""GCP CSV Billing Extractor for FinOps multi-cloud monitoring.

Reads a GCP billing CSV export file, normalizes rows into NormalizedCostRecord,
and batch-inserts them into PostgreSQL.

Can run via ``python -m extractors.gcp_csv`` or as a Docker container with
EXTRACTOR_TYPE=gcp_csv.

The CSV must be a Standard billing export from the GCP Console
(or BigQuery export saved as CSV). Expected columns include:
  billing_account_id, project.id, project.name, service.description,
  sku.description, usage_start_time, usage_end_time, cost, currency,
  usage.amount, usage.unit, labels
"""

from __future__ import annotations

import csv
import logging
import os
import sys
from pathlib import Path
from typing import Sequence

import psycopg
from psycopg.rows import dict_row
from psycopg.sql import SQL
from psycopg.types.json import Json
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.extractors.gcp_shared import (
    DEFAULT_SERVICE_CATEGORY_MAP,
    normalize_csv_row,
)
from backend.models import NormalizedCostRecord, ServiceCategory

logger = logging.getLogger("backend.extractors.gcp_csv")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GCP_CSV_PATH: str = os.getenv("GCP_CSV_PATH", "")
GCP_PROJECT: str = os.getenv("GCP_PROJECT", "")
PG_DSN: str = os.getenv("PG_DSN", "")

BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "500"))

EXTRACTOR_NAME = "gcp_csv"

# ---------------------------------------------------------------------------
# PostgreSQL helpers (same pattern as gcp_billing)
# ---------------------------------------------------------------------------

_INSERT_SQL = SQL(
    "INSERT INTO cost_records "
    "(record_id, provider, usage_start, usage_end, ingestion_ts, "
    "account_id, project_id, service_category, service_name, "
    "cost_usd, currency_original, cost_original, net_cost_usd, "
    "usage_quantity, usage_unit, tags) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
    "ON CONFLICT (record_id) DO NOTHING"
)


@retry(
    retry=retry_if_exception_type((psycopg.OperationalError, psycopg.InterfaceError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _get_pg_connection(dsn: str) -> psycopg.Connection:
    """Open a PostgreSQL connection with retry on transient errors."""
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=False)


def _batch_insert(
    conn: psycopg.Connection,
    records: Sequence[NormalizedCostRecord],
) -> int:
    """Insert a batch of records into ``cost_records``.

    Returns the number of rows inserted (excludes conflicts).
    """
    if not records:
        return 0

    rows = [
        (
            rec.record_id,
            rec.provider.value,
            rec.usage_start,
            rec.usage_end,
            rec.ingestion_ts,
            rec.account_id,
            rec.project_id,
            rec.service_category.value,
            rec.service_name,
            rec.cost_usd,
            rec.currency_original,
            rec.cost_original,
            rec.net_cost_usd,
            rec.usage_quantity,
            rec.usage_unit,
            Json(rec.tags) if rec.tags else Json({}),
        )
        for rec in records
    ]

    with conn.cursor() as cur:
        cur.executemany(_INSERT_SQL, rows)
    conn.commit()

    inserted = len(records)
    logger.debug("Batch inserted up to %d records", inserted)
    return inserted


# ---------------------------------------------------------------------------
# Extractor health tracking
# ---------------------------------------------------------------------------

def _mark_health_start(conn: psycopg.Connection) -> None:
    """Mark the extractor as *running* in ``extractor_health``."""
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
            (EXTRACTOR_NAME,),
        )
    conn.commit()


def _mark_health_success(conn: psycopg.Connection, record_count: int) -> None:
    """Mark the extractor as *success* in ``extractor_health``."""
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
            (record_count, EXTRACTOR_NAME),
        )
    conn.commit()


def _mark_health_failure(conn: psycopg.Connection, error_message: str) -> None:
    """Mark the extractor as *failed* in ``extractor_health``."""
    try:
        conn.rollback()  # clear any aborted transaction before writing
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
                (error_message[:2000], EXTRACTOR_NAME),
            )
        conn.commit()
    except Exception:
        logger.exception("Failed to mark extractor health as failed")


# ---------------------------------------------------------------------------
# Core extractor logic
# ---------------------------------------------------------------------------

def _detect_delimiter(file_path: Path) -> str:
    """Detect CSV delimiter by inspecting the first line."""
    with open(file_path, "r", encoding="utf-8-sig") as fh:
        first_line = fh.readline()
    if "\t" in first_line:
        return "\t"
    return ","


def extract(
    csv_path: str | None = None,
    pg_dsn: str | None = None,
    batch_size: int | None = None,
    service_category_map: dict[str, ServiceCategory] | None = None,
) -> int:
    """Run the full GCP CSV billing extraction pipeline.

    Returns the total number of records inserted into PostgreSQL.
    """
    path = csv_path or GCP_CSV_PATH
    dsn = pg_dsn or PG_DSN
    batch_sz = batch_size or BATCH_SIZE
    category_map = service_category_map or DEFAULT_SERVICE_CATEGORY_MAP

    if not path:
        raise ValueError("GCP_CSV_PATH is required (set env var or pass csv_path)")
    if not dsn:
        raise ValueError("PG_DSN is required (set env var or pass pg_dsn)")

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    logger.info("Reading CSV file: %s", file_path)

    delimiter = _detect_delimiter(file_path)
    logger.info("Detected delimiter: %s", repr(delimiter))

    # PostgreSQL connection
    pg_conn = _get_pg_connection(dsn)
    _mark_health_start(pg_conn)

    total_inserted = 0
    batch: list[NormalizedCostRecord] = []
    total_rows = 0

    try:
        with open(file_path, "r", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, delimiter=delimiter)

            for row in reader:
                total_rows += 1

                # Normalize CSV row to NormalizedCostRecord
                try:
                    record = normalize_csv_row(row, category_map)
                except Exception as exc:
                    logger.warning("Skipping row %d due to error: %s", total_rows, exc)
                    continue

                batch.append(record)

                if len(batch) >= batch_sz:
                    inserted = _batch_insert(pg_conn, batch)
                    total_inserted += inserted
                    batch = []

        # Flush remaining records
        if batch:
            inserted = _batch_insert(pg_conn, batch)
            total_inserted += inserted

        if total_inserted == 0:
            logger.info("No billing records found in CSV file")

        _mark_health_success(pg_conn, total_inserted)
        logger.info(
            "CSV extraction complete: %d/%d rows inserted", total_inserted, total_rows
        )

    except Exception as exc:
        logger.exception("CSV extraction failed: %s", exc)
        _mark_health_failure(pg_conn, str(exc))
        raise
    finally:
        pg_conn.close()

    return total_inserted


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Entrypoint for running the CSV extractor."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        stream=sys.stdout,
    )

    logger.info("Starting GCP CSV billing extractor")

    try:
        total = extract()
        logger.info("GCP CSV billing extractor finished: %d records", total)
    except Exception:
        logger.exception("GCP CSV billing extractor failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
