"""GCP BigQuery Billing Extractor for FinOps multi-cloud monitoring.

Queries GCP billing export in BigQuery, normalizes rows into NormalizedCostRecord,
and batch-inserts them into PostgreSQL.

Can run as a Cloud Run Job via ``python -m extractors.gcp_billing``.
"""

from __future__ import annotations

import logging
import os
import sys
from decimal import Decimal
from typing import Any, Sequence

from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig
from psycopg.sql import SQL
from psycopg.rows import dict_row
from psycopg.types.json import Json
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
import psycopg

from extractors.gcp_shared import (
    extract_project_label,
    generate_record_id,
    labels_to_tags,
    parse_datetime,
    resolve_service_category,
)
from models import NormalizedCostRecord, Provider, ServiceCategory

logger = logging.getLogger("extractors.gcp_billing")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GCP_PROJECT: str = os.getenv("GCP_PROJECT", "")
BQ_DATASET: str = os.getenv("BQ_DATASET", "billing_export")
BQ_TABLE: str = os.getenv("BQ_TABLE", "gcp_billing_export_v1")
PG_DSN: str = os.getenv("PG_DSN", "")
DATE_FROM: str = os.getenv("DATE_FROM", "")
DATE_TO: str = os.getenv("DATE_TO", "")

BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "500"))

EXTRACTOR_NAME = "gcp_billing"

# ---------------------------------------------------------------------------
# BigQuery query builder
# ---------------------------------------------------------------------------

def _build_query(
    project: str,
    dataset: str,
    table: str,
    date_from: str,
    date_to: str,
) -> tuple[str, dict[str, Any]]:
    """Return parameterised SQL and query params for BigQuery."""
    query = (
        f"SELECT\n"
        f"    project.id           AS project_id,\n"
        f"    project.number       AS project_number,\n"
        f"    billing_account_id,\n"
        f"    service.description  AS service_description,\n"
        f"    sku.description      AS sku_description,\n"
        f"    usage_start_time,\n"
        f"    usage_end_time,\n"
        f"    usage.amount          AS usage_amount,\n"
        f"    usage.unit           AS usage_unit,\n"
        f"    cost,\n"
        f"    currency,\n"
        f"    labels,\n"
        f"    system_labels\n"
        f"FROM `{project}.{dataset}.{table}`\n"
        f"WHERE usage_start_time >= @date_from\n"
        f"  AND usage_start_time <  @date_to\n"
        f"ORDER BY usage_start_time\n"
    )

    query_params = [
        bigquery.ScalarQueryParameter("date_from", "STRING", date_from),
        bigquery.ScalarQueryParameter("date_to", "STRING", date_to),
    ]
    return query, query_params


# ---------------------------------------------------------------------------
# Row normalisation
# ---------------------------------------------------------------------------

def normalise_row(
    row: dict[str, Any],
    service_category_map: dict[str, ServiceCategory] | None = None,
) -> NormalizedCostRecord:
    """Map a single BigQuery billing row to a :class:`NormalizedCostRecord`.

    Delegates to :mod:`extractors.gcp_shared` for shared normalisation logic.
    """
    project_id = row.get("project_id", "") or ""
    label_project = extract_project_label(row)
    service_description = row.get("service_description", "") or ""
    sku_description = row.get("sku_description", "") or ""
    usage_start = parse_datetime(row.get("usage_start_time"))
    usage_end = parse_datetime(row.get("usage_end_time"))
    cost = row.get("cost")
    usage_amount = row.get("usage_amount")
    usage_unit = row.get("usage_unit") or ""

    # Cost — GCP exports cost as a float / string; coerce safely
    try:
        cost_decimal = Decimal(str(cost)) if cost is not None else Decimal("0")
    except Exception:
        cost_decimal = Decimal("0")

    # Usage quantity
    try:
        usage_decimal = Decimal(str(usage_amount)) if usage_amount is not None else None
    except Exception:
        usage_decimal = None

    record_id = generate_record_id(
        provider=Provider.GCP.value,
        project_id=project_id,
        usage_start=usage_start.isoformat(),
        service_name=sku_description,
    )

    return NormalizedCostRecord(
        record_id=record_id,
        provider=Provider.GCP,
        usage_start=usage_start,
        usage_end=usage_end,
        account_id=project_id,
        project_id=label_project or project_id,
        service_category=resolve_service_category(service_description, service_category_map),
        service_name=sku_description,
        cost_usd=cost_decimal,
        net_cost_usd=cost_decimal,  # GCP export cost is already net for standard export
        tags=labels_to_tags(row),
        usage_quantity=usage_decimal,
        usage_unit=usage_unit if usage_unit else None,
    )


# ---------------------------------------------------------------------------
# PostgreSQL helpers
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

    Returns the number of rows actually inserted (excludes conflicts).
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

    inserted = len(records)  # ON CONFLICT DO NOTHING doesn't give rowcount via executemany
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

@retry(
    retry=retry_if_exception_type((Exception,)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _run_bq_query(
    bq_client: bigquery.Client,
    query: str,
    query_params: list[bigquery.ScalarQueryParameter],
    project: str,
) -> bigquery.RowIterator:
    """Execute a parameterised BigQuery query with retry."""
    job_config = QueryJobConfig()
    job_config.query_parameters = query_params
    job_config.use_legacy_sql = False

    logger.info("Running BigQuery query on project %s", project)
    query_job = bq_client.query(query, job_config=job_config)
    return query_job.result()


def extract(
    bq_client: bigquery.Client | None = None,
    pg_dsn: str | None = None,
    gcp_project: str | None = None,
    bq_dataset: str | None = None,
    bq_table: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    batch_size: int | None = None,
    service_category_map: dict[str, ServiceCategory] | None = None,
) -> int:
    """Run the full GCP billing extraction pipeline.

    Returns the total number of records inserted into PostgreSQL.
    """
    # Resolve configuration — explicit params > env vars > defaults
    project = gcp_project or GCP_PROJECT
    dataset = bq_dataset or BQ_DATASET
    table = bq_table or BQ_TABLE
    dsn = pg_dsn or PG_DSN
    from_date = date_from or DATE_FROM
    to_date = date_to or DATE_TO
    batch_sz = batch_size or BATCH_SIZE

    if not project:
        raise ValueError("GCP_PROJECT is required (set env var or pass gcp_project)")
    if not dsn:
        raise ValueError("PG_DSN is required (set env var or pass pg_dsn)")
    if not from_date or not to_date:
        raise ValueError("DATE_FROM and DATE_TO are required (set env vars or pass date_from/date_to)")

    # BigQuery client
    client = bq_client if bq_client is not None else bigquery.Client(project=project)

    # Build and run query
    query, query_params = _build_query(project, dataset, table, from_date, to_date)
    rows: bigquery.RowIterator = _run_bq_query(client, query, query_params, project)

    # PostgreSQL connection
    pg_conn = _get_pg_connection(dsn)
    _mark_health_start(pg_conn)

    total_inserted = 0
    batch: list[NormalizedCostRecord] = []

    try:
        for row in rows:
            record = normalise_row(dict(row.items()), service_category_map)
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
            logger.info("No billing records found for the given date range")

        _mark_health_success(pg_conn, total_inserted)
        logger.info("Extraction complete: %d records inserted", total_inserted)

    except Exception as exc:
        logger.exception("Extraction failed: %s", exc)
        _mark_health_failure(pg_conn, str(exc))
        raise
    finally:
        pg_conn.close()

    return total_inserted


# ---------------------------------------------------------------------------
# CLI entrypoint (Cloud Run Job)
# ---------------------------------------------------------------------------

def main() -> None:
    """Entrypoint for running the extractor as a Cloud Run Job."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        stream=sys.stdout,
    )

    logger.info("Starting GCP billing extractor")

    try:
        total = extract()
        logger.info("GCP billing extractor finished: %d records", total)
    except Exception:
        logger.exception("GCP billing extractor failed")
        sys.exit(1)


if __name__ == "__main__":
    main()