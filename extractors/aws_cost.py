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

import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError
from pydantic import ValidationError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_chain,
    wait_fixed,
    wait_exponential,
)

from models import NormalizedCostRecord, Provider, ServiceCategory

logger = logging.getLogger(__name__)

# AWS Cost Explorer metric names
METRICS = ["UNBLENDED_COST"]

# Time granularity for queries
GRANULARITY = "DAILY"


# ---------------------------------------------------------------------------#
# AWS Cost Explorer response → ServiceCategory mapping                      #
# ---------------------------------------------------------------------------#

# Map service codes to service categories based on AWS service naming
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
    "AmazonES": ServiceCategory.COMPUTE,
    "AmazonMQ": ServiceCategory.COMPUTE,
    "AWSGlue": ServiceCategory.COMPUTE,
    "AWSDataTransfer": ServiceCategory.NETWORK,
}


def get_service_category(service_code: str | None) -> ServiceCategory:
    """Map AWS service code to ServiceCategory."""
    if not service_code:
        return ServiceCategory.OTHER
    # Normalize the service code
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
    metrics: list[str] = None,
) -> dict[str, Any]:
    """Fetch cost data from AWS Cost Explorer API."""
    if metrics is None:
        metrics = METRICS

    try:
        response = client.get_cost_and_usage(
            TimePeriod={
                "Start": start_date,
                "End": end_date,
            },
            Granularity=granularity,
            Metrics=metrics,
            GroupBy=[
                {"Type": "DIMENSION", "Key": "SERVICE"},
                {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"},
            ],
            NextPageToken=None,  # Simple page traversal - could be improved
        )
        return response
    except ClientError as e:
        logger.error(f"AWS Cost Explorer API error: {e}")
        raise


# ---------------------------------------------------------------------------#
# Data transformation                                                       #
# ---------------------------------------------------------------------------#


def normalize_aws_cost_records(
    response: dict[str, Any],
    date_from: datetime,
    date_to: datetime,
) -> list[NormalizedCostRecord]:
    """Transform Cost Explorer response into NormalizedCostRecord instances."""
    records = []

    results = response.get("ResultsByTime", [])

    for result in results:
        time_period = result.get("TimePeriod", {})
        date_str = time_period.get("Start", "")

        groups = result.get("Groups", [])
        for group in groups:
            identity = group.get("Keys", [None])[0]
            if not identity:
                continue

            # Parse the identity: SERVICE~LINKED_ACCOUNT
            parts = identity.split("~")
            service_code = parts[0] if len(parts) > 0 else None
            account_id = parts[1] if len(parts) > 1 else "unknown"

            cost_data = group.get("Metrics", {})
            amount_str = cost_data.get("UnblendedCost", {}).get("Amount", "0")

            try:
                amount = Decimal(amount_str)
            except (InvalidOperation, ValueError):
                amount = Decimal("0")

            if amount > 0:
                record = NormalizedCostRecord(
                    provider=Provider.AWS,
                    project_name=account_id,
                    sku_name=service_code or "Unknown",
                    cost_amount=float(amount),
                    currency="USD",
                    tags={"service": service_code or ""},
                    date=date_str,
                    created_at=datetime.now(timezone.utc),
                )
                records.append(record)

    return records


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
    # Get AWS credentials from environment
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    if not aws_access_key_id or not aws_secret_access_key:
        logger.error("AWS credentials not configured")
