"""AWS Cost Explorer extractor for FinOps multi-cloud monitoring.

Extracts cost data from AWS Cost Explorer API (ce:GetCostAndUsage),
normalizes rows into NormalizedCostRecord instances, and batch-inserts
them into PostgreSQL.

Configuration via environment variables:
  AWS_ACCESS_KEY_ID      – IAM Access Key ID
  AWS_SECRET_ACCESS_KEY  – IAM Secret Access Key
  AWS_DEFAULT_REGION     – AWS region (default: us-east-1)
  PG_DSN                 – PostgreSQL connection string
  DATE_FROM              – Start date (YYYY-MM-DD), defaults to 30 days ago
  DATE_TO                – End date (YYYY-MM-DD), defaults to today
  BATCH_SIZE             – DB insert batch size (default 500)
  EXCHANGE_RATE_TABLE    – Table for currency conversion (default: exchange_rates)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_chain,
    wait_fixed,
)

from extractors.common import convert_to_usd
from extractors.common import load_exchange_rates as _load_exchange_rates
from models import NormalizedCostRecord, Provider, ServiceCategory

logger = logging.getLogger(__name__)

# AWS Cost Explorer metric names
METRICS = ["UNBLENDED_COST"]

# Time granularity for queries
GRANULARITY = "DAILY"

# ---------------------------------------------------------------------------#
# AWS Cost Explorer response → ServiceCategory mapping                      #
# ---------------------------------------------------------------------------#

SERVICE_CODE_MAP: dict[str, ServiceCategory] = {
    "AmazonEC2": ServiceCategory.COMPUTE,
    "AmazonRDS": ServiceCategory.DATABASE,
    "AmazonS3": ServiceCategory.STORAGE,
    "AmazonECR": ServiceCategory.COMPUTE,
    "AmazonECS": ServiceCategory.COMPUTE,
    "AmazonEKS": ServiceCategory.COMPUTE,
    "AmazonLambda": ServiceCategory.COMPUTE,
    "AmazonDynamoDB": ServiceCategory.DATABASE,
    "AmazonCloudFront": ServiceCategory.NETWORK,
    "AmazonVPC": ServiceCategory.NETWORK,
    "AmazonES": ServiceCategory.COMPUTE,
    "AmazonMQ": ServiceCategory.COMPUTE,
    "AWSGlue": ServiceCategory.COMPUTE,
    "AWSDataTransfer": ServiceCategory.NETWORK,
}


def get_service_category(service_code: str | None) -> ServiceCategory:
    """Map AWS service code to ServiceCategory."""
    if not service_code:
        return ServiceCategory.OTHER
    for key in SERVICE_CODE_MAP:
        if key.lower() in service_code.lower():
            return SERVICE_CODE_MAP[key]
    return ServiceCategory.OTHER


# ---------------------------------------------------------------------------#
# Cost Explorer API client                                                  #
# ---------------------------------------------------------------------------#


@retry(
    stop=stop_after_attempt(3),
    wait=wait_chain(wait_fixed(1), wait_fixed(2), wait_fixed(4)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def get_cost_and_usage(
    client: Any,
    start_date: str,
    end_date: str,
    granularity: str = GRANULARITY,
    metrics: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch cost data from AWS Cost Explorer API with pagination."""
    if metrics is None:
        metrics = METRICS

    all_results: list[dict[str, Any]] = []
    next_token: str | None = None

    while True:
        try:
            kwargs: dict[str, Any] = {
                "TimePeriod": {"Start": start_date, "End": end_date},
                "Granularity": granularity,
                "Metrics": metrics,
                "GroupBy": [
                    {"Type": "DIMENSION", "Key": "SERVICE"},
                    {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"},
                ],
            }
            if next_token:
                kwargs["NextPageToken"] = next_token

            response = client.get_cost_and_usage(**kwargs)
            all_results.extend(response.get("ResultsByTime", []))

            next_token = response.get("NextPageToken")
            if not next_token:
                break
        except ClientError as e:
            logger.error("AWS Cost Explorer API error: %s", e)
            raise

    return {"ResultsByTime": all_results}


# ---------------------------------------------------------------------------#
# Data transformation                                                       #
# ---------------------------------------------------------------------------#


def _generate_record_id(
    account_id: str,
    service_code: str,
    date_str: str,
) -> str:
    """Deterministic record id hash."""
    raw = f"aws:{account_id}:{service_code}:{date_str}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def normalize_aws_cost_records(
    response: dict[str, Any],
    date_from: datetime,
    date_to: datetime,
) -> list[NormalizedCostRecord]:
    """Transform Cost Explorer response into NormalizedCostRecord instances."""
    records: list[NormalizedCostRecord] = []
    results = response.get("ResultsByTime", [])

    for result in results:
        time_period = result.get("TimePeriod", {})
        date_str = time_period.get("Start", "")

        groups = result.get("Groups", [])
        for group in groups:
            keys = group.get("Keys", [])
            if not keys:
                continue

            # Parse identity: SERVICE~LINKED_ACCOUNT
            identity = keys[0]
            parts = identity.split("~")
            service_code = parts[0] if len(parts) > 0 else None
            account_id = parts[1] if len(parts) > 1 else "unknown"

            cost_data = group.get("Metrics", {})
            unblended = cost_data.get("UnblendedCost", {})
            amount_str = unblended.get("Amount", "0")
            currency = unblended.get("Unit", "USD")

            try:
                amount = Decimal(amount_str)
            except (InvalidOperation, ValueError):
                amount = Decimal("0")

            if amount <= 0:
                continue

            usage_start = datetime.strptime(date_str, "%Y-%m-%d").replace(
                tzinfo=UTC
            )
            usage_end = usage_start + timedelta(days=1)

            record = NormalizedCostRecord(
                record_id=_generate_record_id(account_id, service_code or "", date_str),
                provider=Provider.AWS,
                usage_start=usage_start,
                usage_end=usage_end,
                account_id=account_id,
                project_id=account_id,
                service_category=get_service_category(service_code),
                service_name=service_code or "Unknown",
                resource_id=None,
                region=None,
                charge_type=None,
                cost_usd=amount,
                currency_original=currency,
                cost_original=amount,
                discount_usd=Decimal("0"),
                net_cost_usd=amount,
                usage_quantity=None,
                usage_unit=None,
                tags={"service": service_code or ""},
            )
            records.append(record)

    return records


# ---------------------------------------------------------------------------#
# Exchange-rate lookup (extractors.common.load_exchange_rates / convert_to_usd)
# ---------------------------------------------------------------------------#


# ---------------------------------------------------------------------------#
# PostgreSQL helpers                                                        #
# ---------------------------------------------------------------------------#

_INSERT_SQL = """
INSERT INTO cost_records (
    record_id, provider, usage_start, usage_end, ingestion_ts,
    account_id, project_id, service_category, service_name,
    resource_id, region, charge_type,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit, tags
) VALUES (
    %(record_id)s, %(provider)s, %(usage_start)s, %(usage_end)s, %(ingestion_ts)s,
    %(account_id)s, %(project_id)s, %(service_category)s, %(service_name)s,
    %(resource_id)s, %(region)s, %(charge_type)s,
    %(cost_usd)s, %(currency_original)s, %(cost_original)s, %(discount_usd)s, %(net_cost_usd)s,
    %(usage_quantity)s, %(usage_unit)s, %(tags)s
) ON CONFLICT (record_id) DO NOTHING
"""

_INSERT_SQL_BATCH = """
INSERT INTO cost_records (
    record_id, provider, usage_start, usage_end, ingestion_ts,
    account_id, project_id, service_category, service_name,
    resource_id, region, charge_type,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit, tags
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (record_id) DO NOTHING
"""


def _insert_batch(conn: psycopg.Connection, records: list[NormalizedCostRecord]) -> int:
    if not records:
        return 0
    rows = []
    for rec in records:
        row = rec.model_dump()
        row["provider"] = rec.provider.value
        row["service_category"] = rec.service_category.value
        row["tags"] = json.dumps(row.get("tags", {}))
        rows.append((
            row["record_id"], row["provider"], row["usage_start"], row["usage_end"],
            row.get("ingestion_ts"), row["account_id"], row["project_id"],
            row["service_category"], row["service_name"],
            row.get("resource_id"), row.get("region"), row.get("charge_type"),
            row["cost_usd"], row["currency_original"], row["cost_original"],
            row["discount_usd"], row["net_cost_usd"],
            row.get("usage_quantity"), row.get("usage_unit"), row["tags"],
        ))
    with conn.cursor() as cur:
        cur.executemany(_INSERT_SQL_BATCH, rows)
    conn.commit()
    return len(records)


def insert_records(
    conn: psycopg.Connection, records: list[NormalizedCostRecord], batch_size: int = 500
) -> int:
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        inserted = _insert_batch(conn, batch)
        total += inserted
        logger.info("Inserted batch %d-%d (%d records)", i, i + len(batch), inserted)
    return total


# ---------------------------------------------------------------------------#
# Health tracking                                                           #
# ---------------------------------------------------------------------------#

EXTRACTOR_NAME = "aws_cost"


def _mark_health_start(conn: psycopg.Connection) -> None:
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
    try:
        conn.rollback()
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


# ---------------------------------------------------------------------------#
# Main extraction flow                                                      #
# ---------------------------------------------------------------------------#


def extract_costs(
    date_from: datetime,
    date_to: datetime,
    batch_size: int = 500,
    exchange_rate_table: str = "exchange_rates",
) -> int:
    """Extract AWS costs and return count of records inserted."""
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    if not aws_access_key_id or not aws_secret_access_key:
        logger.error("AWS credentials not configured")
        return 0

    pg_dsn = os.getenv("PG_DSN")
    if not pg_dsn:
        raise ValueError("PG_DSN is not configured")

    start_str = date_from.strftime("%Y-%m-%d")
    end_str = date_to.strftime("%Y-%m-%d")

    import boto3

    ce_client = boto3.client(
        "ce",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region,
    )

    response = get_cost_and_usage(ce_client, start_str, end_str)
    records = normalize_aws_cost_records(response, date_from, date_to)

    if not records:
        logger.info("No cost records found for %s – %s", start_str, end_str)
        return 0

    pg_conn = psycopg.connect(pg_dsn)
    _mark_health_start(pg_conn)

    try:
        exchange_rates = _load_exchange_rates(pg_conn, exchange_rate_table)

        for idx, rec in enumerate(records):
            if rec.currency_original != "USD":
                records[idx] = rec.model_copy(
                    update={
                        "cost_usd": convert_to_usd(
                            rec.cost_original, rec.currency_original, exchange_rates
                        ),
                        "net_cost_usd": convert_to_usd(
                            rec.cost_original, rec.currency_original, exchange_rates
                        ),
                    }
                )

        total_inserted = insert_records(pg_conn, records, batch_size)
        logger.info("AWS extraction complete: %d records inserted", total_inserted)
        _mark_health_success(pg_conn, total_inserted)

    except Exception as exc:
        logger.exception("AWS extraction failed: %s", exc)
        _mark_health_failure(pg_conn, str(exc))
        raise
    finally:
        pg_conn.close()

    return total_inserted


# ---------------------------------------------------------------------------#
# CLI entrypoint                                                            #
# ---------------------------------------------------------------------------#


def main() -> None:
    """Entrypoint for running the extractor as a subprocess / Cloud Run Job."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        stream=sys.stdout,
    )

    logger.info("Starting AWS Cost Explorer extractor")

    date_from_raw = os.getenv("DATE_FROM")
    date_to_raw = os.getenv("DATE_TO")

    if date_from_raw and date_to_raw:
        date_from = datetime.strptime(date_from_raw, "%Y-%m-%d").replace(
            tzinfo=UTC
        )
        date_to = datetime.strptime(date_to_raw, "%Y-%m-%d").replace(
            tzinfo=UTC
        )
    else:
        to_dt = datetime.now(UTC)
        from_dt = to_dt - timedelta(days=30)
        date_to = to_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        date_from = from_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        total = extract_costs(date_from=date_from, date_to=date_to)
        logger.info("AWS Cost Extractor finished: %d records", total)
    except Exception:
        logger.exception("AWS Cost Extractor failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
