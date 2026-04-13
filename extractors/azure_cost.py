"""Azure Cost Management extractor for FinOps multi-cloud monitoring.

Extracts cost data from Azure Cost Management REST API via the
azure-mgmt-costmanagement SDK, normalizes rows into NormalizedCostRecord
instances, and batch-inserts them into PostgreSQL.

Configuration via environment variables:
  AZURE_SUBSCRIPTION_ID  – Target subscription ID
  AZURE_TENANT_ID        – Azure AD tenant
  AZURE_CLIENT_ID        – Service principal app ID
  AZURE_CLIENT_SECRET    – Service principal secret
  PG_DSN                 – PostgreSQL connection string
  DATE_FROM              – Start date (YYYY-MM-DD), defaults to 30 days ago
  DATE_TO                – End date (YYYY-MM-DD), defaults to today
  AZURE_SCOPE            – "subscription" (default) or "managementgroup"
  AZURE_MGMT_GROUP_ID    – Required when AZURE_SCOPE=managementgroup
  BATCH_SIZE             – DB insert batch size (default 500)
  EXCHANGE_RATE_TABLE    – Table for currency conversion (default exchange_rates)
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import psycopg
from azure.identity import ClientSecretCredential
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import (
    QueryDefinition,
    QueryDataset,
    QueryFilter,
    QueryGrouping,
    QueryTimePeriod,
    TimeframeType,
)
from pydantic import ValidationError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from models import NormalizedCostRecord, Provider, ServiceCategory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Azure meter-category → ServiceCategory mapping
# ---------------------------------------------------------------------------

DEFAULT_METER_CATEGORY_MAP: dict[str, ServiceCategory] = {
    "Virtual Machines": ServiceCategory.COMPUTE,
    "Virtual Machines Licenses": ServiceCategory.COMPUTE,
    "Container Registry": ServiceCategory.COMPUTE,
    "Kubernetes Service": ServiceCategory.COMPUTE,
    "Container Instances": ServiceCategory.COMPUTE,
    "Container Service": ServiceCategory.COMPUTE,
    "Functions": ServiceCategory.COMPUTE,
    "App Service": ServiceCategory.COMPUTE,
    "Batch": ServiceCategory.COMPUTE,
    "Storage": ServiceCategory.STORAGE,
    "Storage Accounts": ServiceCategory.STORAGE,
    "Blob Storage": ServiceCategory.STORAGE,
    "Data Lake Storage": ServiceCategory.STORAGE,
    "Files": ServiceCategory.STORAGE,
    "Queue Storage": ServiceCategory.STORAGE,
    "Table Storage": ServiceCategory.STORAGE,
    "Disk Storage": ServiceCategory.STORAGE,
    "Network": ServiceCategory.NETWORK,
    "Virtual Network": ServiceCategory.NETWORK,
    "VPN Gateway": ServiceCategory.NETWORK,
    "Application Gateway": ServiceCategory.NETWORK,
    "Load Balancer": ServiceCategory.NETWORK,
    "Front Door": ServiceCategory.NETWORK,
    "CDN": ServiceCategory.NETWORK,
    "DNS": ServiceCategory.NETWORK,
    "Public IP": ServiceCategory.NETWORK,
    "Bandwidth": ServiceCategory.NETWORK,
    "SQL Database": ServiceCategory.DATABASE,
    "Database": ServiceCategory.DATABASE,
    "Cosmos DB": ServiceCategory.DATABASE,
    "PostgreSQL": ServiceCategory.DATABASE,
    "MySQL": ServiceCategory.DATABASE,
    "Cache": ServiceCategory.DATABASE,
    "Redis Cache": ServiceCategory.DATABASE,
    "SQL Data Warehouse": ServiceCategory.DATABASE,
    "Synapse Analytics": ServiceCategory.DATABASE,
    "Machine Learning": ServiceCategory.ML,
    "Cognitive Services": ServiceCategory.ML,
    "Azure OpenAI": ServiceCategory.LLM,
    "AI Search": ServiceCategory.ML,
    "Bot Service": ServiceCategory.ML,
    "Azure Databricks": ServiceCategory.ML,
    "HDInsight": ServiceCategory.ML,
}

# Column order we request from the Azure Cost Management API.
AZURE_QUERY_COLUMNS = [
    "UsageDate",
    "SubscriptionId",
    "ResourceGroup",
    "MeterCategory",
    "MeterSubCategory",
    "Product",
    "CostInBillingCurrency",
    "Currency",
    "Tags",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(key: str, default: str | None = None) -> str:
    """Read an env var, raising if missing and no default."""
    val = os.environ.get(key, default)
    if val is None:
        raise EnvironmentError(f"Required env var {key} is not set")
    return val


def _env_optional(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def _parse_date(val: str) -> datetime:
    return datetime.strptime(val, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _default_date_range() -> tuple[datetime, datetime]:
    """Return (from, to) defaulting to last 30 days."""
    to_dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    from_dt = to_dt - timedelta(days=30)
    return from_dt, to_dt


def generate_record_id(subscription_id: str, usage_date: str, meter_category: str, meter_sub_category: str, product: str) -> str:
    """Deterministic record_id from provider+subscription+date+meter hash."""
    raw = f"azure:{subscription_id}:{usage_date}:{meter_category}:{meter_sub_category}:{product}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def map_service_category(meter_category: str, mapping: dict[str, ServiceCategory] | None = None) -> ServiceCategory:
    """Map an Azure MeterCategory to a ServiceCategory enum value.

    Falls back to OTHER if no mapping found.
    """
    table = mapping or DEFAULT_METER_CATEGORY_MAP
    return table.get(meter_category, ServiceCategory.OTHER)


def _azure_date_to_datetime(usage_date_val: Any) -> datetime:
    """Convert Azure UsageDate (int like 20240115 or ISO string) to datetime."""
    if isinstance(usage_date_val, int):
        return datetime.strptime(str(usage_date_val), "%Y%m%d").replace(tzinfo=timezone.utc)
    if isinstance(usage_date_val, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y%m%d"):
            try:
                return datetime.strptime(usage_date_val, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        raise ValueError(f"Cannot parse Azure date: {usage_date_val!r}")
    raise TypeError(f"Unexpected UsageDate type: {type(usage_date_val)}")


def _parse_tags(tags_value: Any) -> dict[str, str]:
    """Parse Azure Tags field — may be a dict, JSON string, or None."""
    if tags_value is None:
        return {}
    if isinstance(tags_value, dict):
        return {str(k): str(v) for k, v in tags_value.items()}
    if isinstance(tags_value, str):
        import json

        try:
            parsed = json.loads(tags_value)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


# ---------------------------------------------------------------------------
# Exchange-rate lookup
# ---------------------------------------------------------------------------


def _load_exchange_rates(conn: psycopg.Connection, table: str = "exchange_rates") -> dict[str, Decimal]:
    """Load exchange rates from the database. Returns {currency_code: rate_to_usd}."""
    rates: dict[str, Decimal] = {"USD": Decimal("1")}
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT currency_code, rate_to_usd FROM {table}")  # noqa: S608 — table name is config, not user input
            for row in cur.fetchall():
                rates[row[0]] = Decimal(str(row[1]))
    except psycopg.Error:
        logger.exception("Failed to load exchange rates from %s; assuming USD=1 only", table)
    return rates


def convert_to_usd(cost: Decimal, currency: str, rates: dict[str, Decimal]) -> Decimal:
    """Convert a cost in *currency* to USD using the provided rates dict."""
    if currency == "USD":
        return cost
    rate = rates.get(currency)
    if rate is None:
        logger.warning("No exchange rate for currency %s — treating as USD=1", currency)
        return cost
    return (cost * rate).quantize(Decimal("0.000001"))


# ---------------------------------------------------------------------------
# Azure API interaction
# ---------------------------------------------------------------------------


def _build_scope(subscription_id: str, scope: str, mgmt_group_id: str | None = None) -> str:
    """Build the Azure resource scope string."""
    if scope == "managementgroup":
        if not mgmt_group_id:
            raise ValueError("AZURE_MGMT_GROUP_ID is required when AZURE_SCOPE=managementgroup")
        return f"/providers/Microsoft.Management/managementGroups/{mgmt_group_id}"
    return f"/subscriptions/{subscription_id}"


def _build_query_definition(date_from: datetime, date_to: datetime) -> QueryDefinition:
    """Build the QueryDefinition for the Azure Cost Management API."""
    dataset = QueryDataset(
        granularity="Daily",
        aggregation={},
        grouping=[
            QueryGrouping(name=col, type="Dimension")
            for col in AZURE_QUERY_COLUMNS
            if col not in ("UsageDate", "CostInBillingCurrency", "Currency")
        ],
    )

    time_period = QueryTimePeriod(
        from_property=date_from,
        to=date_to,
    )

    return QueryDefinition(
        type="ActualCost",
        timeframe=TimeframeType.CUSTOM,
        time_period=time_period,
        dataset=dataset,
    )


def fetch_cost_rows(
    client: CostManagementClient,
    scope: str,
    date_from: datetime,
    date_to: datetime,
) -> list[dict[str, Any]]:
    """Fetch all cost rows from Azure Cost Management, handling pagination.

    Returns a list of dicts keyed by the AZURE_QUERY_COLUMNS.
    """
    query_def = _build_query_definition(date_from, date_to)

    all_rows: list[dict[str, Any]] = []
    continuation_token: str | None = None

    while True:
        if continuation_token:
            result = client.query.usage_by_scope(
                scope=scope,
                parameters=query_def,
                skip_token=continuation_token,
            )
        else:
            result = client.query.usage_by_scope(
                scope=scope,
                parameters=query_def,
            )

        columns = [c.name for c in result.columns] if result.columns else AZURE_QUERY_COLUMNS

        for row in result.rows:
            row_dict = dict(zip(columns, row))
            all_rows.append(row_dict)

        # Pagination
        continuation_token = getattr(result, "properties", None)
        if continuation_token is None:
            continuation_token = getattr(result, "next_link", None)
        if continuation_token is None:
            # Also check for a skip_token on the result object
            continuation_token = getattr(result, "skip_token", None)
        if not continuation_token:
            break

        logger.info("Pagination: fetching next page with token %s…", str(continuation_token)[:40])

    logger.info("Fetched %d cost rows from Azure API", len(all_rows))
    return all_rows


# ---------------------------------------------------------------------------
# Row → NormalizedCostRecord transformation
# ---------------------------------------------------------------------------


def transform_row(
    row: dict[str, Any],
    exchange_rates: dict[str, Decimal],
    meter_category_map: dict[str, ServiceCategory] | None = None,
) -> NormalizedCostRecord:
    """Transform a single Azure cost row into a NormalizedCostRecord."""
    subscription_id = str(row.get("SubscriptionId", "") or "")
    usage_date = row.get("UsageDate", "")
    meter_category = str(row.get("MeterCategory", "") or "")
    meter_sub_category = str(row.get("MeterSubCategory", "") or "")
    product = str(row.get("Product", "") or "")
    resource_group = str(row.get("ResourceGroup", "") or "")
    cost_billing = row.get("CostInBillingCurrency", 0) or 0
    currency = str(row.get("Currency", "USD") or "USD").upper()
    tags_raw = row.get("Tags", {})

    tags = _parse_tags(tags_raw)

    # Parse the usage date
    usage_dt = _azure_date_to_datetime(usage_date)

    # Cost conversion
    cost_original = Decimal(str(cost_billing))
    cost_usd = convert_to_usd(cost_original, currency, exchange_rates)

    # Service category mapping
    service_category = map_service_category(meter_category, meter_category_map)

    # Project ID from tag, fallback to resource group
    project_id = tags.get("project", tags.get("Project", resource_group or subscription_id))

    # Deterministic record_id
    record_id = generate_record_id(
        subscription_id=subscription_id,
        usage_date=str(usage_date),
        meter_category=meter_category,
        meter_sub_category=meter_sub_category,
        product=product,
    )

    # Build the service_name from MeterSubCategory + Product for richer detail
    service_name = meter_sub_category or meter_category or "unknown"

    return NormalizedCostRecord(
        record_id=record_id,
        provider=Provider.AZURE,
        usage_start=usage_dt,
        usage_end=usage_dt + timedelta(days=1),
        account_id=subscription_id,
        project_id=project_id,
        service_category=service_category,
        service_name=service_name,
        resource_id=resource_group or None,
        cost_usd=cost_usd,
        currency_original=currency,
        cost_original=cost_original,
        tags=tags,
    )


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

INSERT_SQL = """
INSERT INTO normalized_costs (
    record_id, provider, usage_start, usage_end, ingestion_ts,
    account_id, account_name, project_id, project_name, environment, team,
    service_category, service_name, resource_id,
    cost_usd, currency_original, cost_original, discount_usd, net_cost_usd,
    usage_quantity, usage_unit,
    model_name, input_tokens, output_tokens, total_tokens, latency_ms, trace_id,
    tags
) VALUES (
    %(record_id)s, %(provider)s, %(usage_start)s, %(usage_end)s, %(ingestion_ts)s,
    %(account_id)s, %(account_name)s, %(project_id)s, %(project_name)s, %(environment)s, %(team)s,
    %(service_category)s, %(service_name)s, %(resource_id)s,
    %(cost_usd)s, %(currency_original)s, %(cost_original)s, %(discount_usd)s, %(net_cost_usd)s,
    %(usage_quantity)s, %(usage_unit)s,
    %(model_name)s, %(input_tokens)s, %(output_tokens)s, %(total_tokens)s, %(latency_ms)s, %(trace_id)s,
    %(tags)s
) ON CONFLICT (record_id) DO NOTHING
"""


@retry(
    retry=retry_if_exception_type(psycopg.OperationalError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _insert_batch(conn: psycopg.Connection, records: list[NormalizedCostRecord]) -> int:
    """Insert a batch of records, returning the count actually inserted."""
    if not records:
        return 0

    rows = [r.model_dump() for r in records]
    with conn.cursor() as cur:
        cur.executemany(INSERT_SQL, rows)
    conn.commit()
    return len(records)


def insert_records(
    conn: psycopg.Connection,
    records: list[NormalizedCostRecord],
    batch_size: int = 500,
) -> int:
    """Insert records in batches, returning total count inserted."""
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        inserted = _insert_batch(conn, batch)
        total += inserted
        logger.info("Inserted batch %d-%d (%d records)", i, i + len(batch), inserted)
    return total


# ---------------------------------------------------------------------------
# Extractor health tracking
# ---------------------------------------------------------------------------


def mark_extractor_healthy(
    conn: psycopg.Connection,
    provider: str = "azure",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    rows_extracted: int = 0,
) -> None:
    """Mark a successful extractor run in the extractor_health table."""
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO extractor_health (provider, last_run_ts, date_from, date_to, rows_extracted, status)
            VALUES (%s, %s, %s, %s, %s, 'ok')
            ON CONFLICT (provider) DO UPDATE
            SET last_run_ts = EXCLUDED.last_run_ts,
                date_from = EXCLUDED.date_from,
                date_to = EXCLUDED.date_to,
                rows_extracted = EXCLUDED.rows_extracted,
                status = EXCLUDED.status
            """,
            (provider, now, date_from, date_to, rows_extracted),
        )
    conn.commit()


def mark_extractor_unhealthy(
    conn: psycopg.Connection,
    provider: str = "azure",
    error_message: str = "",
) -> None:
    """Mark a failed extractor run in the extractor_health table."""
    now = datetime.now(timezone.utc)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO extractor_health (provider, last_run_ts, status, error_message)
                VALUES (%s, %s, 'error', %s)
                ON CONFLICT (provider) DO UPDATE
                SET last_run_ts = EXCLUDED.last_run_ts,
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message
                """,
                (provider, now, error_message),
            )
        conn.commit()
    except psycopg.Error:
        logger.exception("Failed to mark extractor as unhealthy")


# ---------------------------------------------------------------------------
# Main extractor orchestrator
# ---------------------------------------------------------------------------


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _create_azure_client() -> CostManagementClient:
    """Authenticate and return a CostManagementClient."""
    credential = ClientSecretCredential(
        tenant_id=_env("AZURE_TENANT_ID"),
        client_id=_env("AZURE_CLIENT_ID"),
        client_secret=_env("AZURE_CLIENT_SECRET"),
    )
    subscription_id = _env("AZURE_SUBSCRIPTION_ID")
    return CostManagementClient(credential=credential, subscription_id=subscription_id)


def run_extractor(
    pg_dsn: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    subscription_id: str | None = None,
    scope_type: str | None = None,
    mgmt_group_id: str | None = None,
    batch_size: int | None = None,
    exchange_rate_table: str | None = None,
    meter_category_map: dict[str, ServiceCategory] | None = None,
) -> int:
    """Run the Azure cost extractor end-to-end.

    Returns the total number of records inserted.
    """
    # ---- Resolve config from env / params ----
    sub_id = subscription_id or _env("AZURE_SUBSCRIPTION_ID")
    scope_type = scope_type or _env_optional("AZURE_SCOPE", "subscription")
    mgmt_group_id = mgmt_group_id or _env_optional("AZURE_MGMT_GROUP_ID")
    batch_size = batch_size or int(_env_optional("BATCH_SIZE", "500"))
    exchange_rate_table = exchange_rate_table or _env_optional("EXCHANGE_RATE_TABLE", "exchange_rates")
    pg_dsn = pg_dsn or _env("PG_DSN")

    if date_from is None or date_to is None:
        default_from, default_to = _default_date_range()
        date_from = date_from or _parse_date(_env_optional("DATE_FROM", default_from.strftime("%Y-%m-%d")))
        date_to = date_to or _parse_date(_env_optional("DATE_TO", default_to.strftime("%Y-%m-%d")))

    logger.info(
        "Starting Azure cost extractor: scope=%s, subscription=%s, from=%s, to=%s",
        scope_type, sub_id, date_from.isoformat(), date_to.isoformat(),
    )

    # ---- Azure client ----
    client = _create_azure_client()
    scope = _build_scope(sub_id, scope_type, mgmt_group_id)

    # ---- Fetch cost rows ----
    raw_rows = fetch_cost_rows(client, scope, date_from, date_to)

    if not raw_rows:
        logger.info("No cost rows returned from Azure API — nothing to insert.")
        # Still mark healthy: a successful empty run is fine.
        with psycopg.connect(pg_dsn) as conn:
            mark_extractor_healthy(conn, "azure", date_from, date_to, 0)
        return 0

    # ---- PostgreSQL connection ----
    with psycopg.connect(pg_dsn) as conn:
        exchange_rates = _load_exchange_rates(conn, exchange_rate_table)

        # ---- Transform rows ----
        records: list[NormalizedCostRecord] = []
        errors: list[str] = []
        for i, row in enumerate(raw_rows):
            try:
                rec = transform_row(row, exchange_rates, meter_category_map)
                records.append(rec)
            except (ValidationError, ValueError, InvalidOperation) as exc:
                msg = f"Row {i}: {exc} — raw: {row!r}"
                logger.warning(msg)
                errors.append(msg)

        if errors:
            logger.warning("Skipped %d rows due to transformation errors", len(errors))

        if not records:
            logger.info("All rows failed transformation — nothing to insert.")
            mark_extractor_healthy(conn, "azure", date_from, date_to, 0)
            return 0

        # ---- Batch insert ----
        total_inserted = insert_records(conn, records, batch_size)
        logger.info("Inserted %d of %d records into PostgreSQL", total_inserted, len(records))

        # ---- Health marker ----
        mark_extractor_healthy(conn, "azure", date_from, date_to, total_inserted)

    return total_inserted


def main() -> None:
    """Entrypoint for Cloud Run Job execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info("Azure Cost Extractor starting…")

    try:
        total = run_extractor()
        logger.info("Azure Cost Extractor completed: %d records inserted", total)
    except Exception:
        logger.exception("Azure Cost Extractor failed")
        # Attempt to mark unhealthy — best effort
        try:
            pg_dsn = _env("PG_DSN")
            with psycopg.connect(pg_dsn) as conn:
                mark_extractor_unhealthy(conn, "azure", "Extractor failed — see logs")
        except Exception:
            logger.exception("Also failed to mark extractor as unhealthy")
        raise


if __name__ == "__main__":
    main()