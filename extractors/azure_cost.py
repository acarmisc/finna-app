"""Azure Cost Management extractor for FinOps multi-cloud monitoring.

Extracts cost data from Azure Cost Management REST API via the
azure-mgmt-costmanagement SDK, normalizes rows into NormalizedCostRecord
instances, and batch-inserts them into PostgreSQL.

Configuration via environment variables:
  AZURE_SUBSCRIPTION_ID  – Target subscription ID (single-sub mode)
  AZURE_TENANT_ID        – Azure AD tenant (single-sub mode)
  AZURE_CLIENT_ID        – Service principal app ID (single-sub mode)
  AZURE_CLIENT_SECRET    – Service principal secret (single-sub mode)
  PG_DSN                 – PostgreSQL connection string
  DATE_FROM              – Start date (YYYY-MM-DD), defaults to 30 days ago
  DATE_TO                – End date (YYYY-MM-DD), defaults to today
  AZURE_SCOPE            – "subscription" (default) or "managementgroup"
  AZURE_MGMT_GROUP_ID    – Required when AZURE_SCOPE=managementgroup
  BATCH_SIZE             – DB insert batch size (default 500)
  EXCHANGE_RATE_TABLE    – Table for currency conversion (default exchange_rates)

Multi-subscription configuration (takes priority over single-sub vars):
  AZURE_{PREFIX}_SUBSCRIPTION_ID – Per-subscription ID
  AZURE_{PREFIX}_TENANT_ID      – Per-subscription tenant
  AZURE_{PREFIX}_CLIENT_ID      – Per-subscription client
  AZURE_{PREFIX}_CLIENT_SECRET  – Per-subscription secret
  AZURE_{PREFIX}_SCOPE          – Per-subscription scope
  AZURE_{PREFIX}_MGMT_GROUP_ID  – Per-subscription management group
  where PREFIX is the subscription ID uppercased with dashes→underscores
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg
from azure.core.exceptions import ServiceRequestError
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import (
    QueryAggregation,
    QueryDataset,
    QueryDefinition,
    QueryGrouping,
    QueryTimePeriod,
    TimeframeType,
)
from pydantic import ValidationError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from extractors.common import convert_to_usd
from extractors.common import load_exchange_rates as _load_exchange_rates
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
    "ResourceType",
    "ResourceLocation",
    "MeterCategory",
    "MeterSubCategory",
    "Product",
    "UnitOfMeasure",
    "ChargeType",
    "CostInBillingCurrency",
    "Currency",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(key: str, default: str | None = None) -> str:
    """Read an env var, raising if missing and no default."""
    val = os.environ.get(key, default)
    if val is None:
        raise OSError(f"Required env var {key} is not set")
    return val


def _env_optional(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


_AZURE_PREFIX_RE = re.compile(r"^AZURE_(.+)_SUBSCRIPTION_ID$")


def discover_azure_subscriptions_from_env() -> dict[str, dict[str, str]]:
    """Scan env vars for AZURE_{PREFIX}_SUBSCRIPTION_ID patterns.

    Returns a dict mapping prefix → {subscription_id, tenant_id, client_id,
    client_secret, scope, mgmt_group_id} for each discovered subscription.
    """
    subs: dict[str, dict[str, str]] = {}
    for key, value in os.environ.items():
        m = _AZURE_PREFIX_RE.match(key)
        if not m or not value:
            continue
        prefix = m.group(1)
        sub_id = value
        subs[prefix] = {
            "subscription_id": sub_id,
            "tenant_id": os.environ.get(f"AZURE_{prefix}_TENANT_ID", ""),
            "client_id": os.environ.get(f"AZURE_{prefix}_CLIENT_ID", ""),
            "client_secret": os.environ.get(f"AZURE_{prefix}_CLIENT_SECRET", ""),
            "scope": os.environ.get(f"AZURE_{prefix}_SCOPE", "resourcegroup"),
            "resource_group": os.environ.get(f"AZURE_{prefix}_RESOURCE_GROUP", ""),
            "mgmt_group_id": os.environ.get(f"AZURE_{prefix}_MGMT_GROUP_ID", ""),
        }
    return subs


def _parse_date(val: str) -> datetime:
    return datetime.strptime(val, "%Y-%m-%d").replace(tzinfo=UTC)


def _default_date_range() -> tuple[datetime, datetime]:
    """Return (from, to) defaulting to last LOOKBACK_DAYS days (env var, default 30)."""
    days = int(_env_optional("LOOKBACK_DAYS", "30") or "30")
    to_dt = datetime.now(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    from_dt = to_dt - timedelta(days=days)
    return from_dt, to_dt


def generate_record_id(
    subscription_id: str,
    usage_date: str,
    meter_category: str,
    meter_sub_category: str,
    product: str,
) -> str:
    """Deterministic record_id from provider+subscription+date+meter hash."""
    raw = f"azure:{subscription_id}:{usage_date}:{meter_category}:{meter_sub_category}:{product}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def map_service_category(
    meter_category: str, mapping: dict[str, ServiceCategory] | None = None
) -> ServiceCategory:
    """Map an Azure MeterCategory to a ServiceCategory enum value.

    Falls back to OTHER if no mapping found.
    """
    table = mapping or DEFAULT_METER_CATEGORY_MAP
    return table.get(meter_category, ServiceCategory.OTHER)


def _azure_date_to_datetime(usage_date_val: Any) -> datetime:
    """Convert Azure UsageDate (int like 20240115 or ISO string) to datetime."""
    if isinstance(usage_date_val, int):
        return datetime.strptime(str(usage_date_val), "%Y%m%d").replace(
            tzinfo=UTC
        )
    if isinstance(usage_date_val, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y%m%d"):
            try:
                return datetime.strptime(usage_date_val, fmt).replace(
                    tzinfo=UTC
                )
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
        try:
            parsed = json.loads(tags_value)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


# ---------------------------------------------------------------------------
# Exchange-rate lookup (extractors.common.load_exchange_rates / convert_to_usd)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Azure API interaction
# ---------------------------------------------------------------------------


def _build_scope(
    subscription_id: str,
    scope: str,
    mgmt_group_id: str | None = None,
    resource_group: str | None = None,
) -> str:
    """Build the Azure resource scope string."""
    _scope = scope.lower().rstrip("s").replace("_", "")  # normalize variants
    if _scope == "resourcegroup":
        if not resource_group:
            raise ValueError(
                "resource_group name required when AZURE_SCOPE=resourcegroup"
            )
        return f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
    if _scope == "managementgroup":
        if not mgmt_group_id:
            raise ValueError(
                "AZURE_MGMT_GROUP_ID is required when AZURE_SCOPE=managementgroup"
            )
        return f"/providers/Microsoft.Management/managementGroups/{mgmt_group_id}"
    return f"/subscriptions/{subscription_id}"


def _build_query_definition(date_from: datetime, date_to: datetime) -> QueryDefinition:
    """Build the QueryDefinition for the Azure Cost Management API."""
    dataset = QueryDataset(
        granularity="Daily",
        aggregation={
            "totalCost": QueryAggregation(name="Cost", function="Sum"),
            "totalQuantity": QueryAggregation(name="UsageQuantity", function="Sum"),
        },
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


def _is_rate_limited(exc: BaseException) -> bool:
    """Return True if the exception is an Azure 429 rate-limit error."""
    from azure.core.exceptions import HttpResponseError
    return isinstance(exc, HttpResponseError) and exc.status_code == 429


def _retry_after_wait(retry_state: Any) -> float:
    """Use Azure Retry-After header if present, else fall back to env-configured waits."""
    exc = retry_state.outcome.exception()
    # Try to read Retry-After from Azure response headers
    retry_after: float | None = None
    try:
        headers = exc.response.headers if exc and exc.response else {}
        ra = headers.get("Retry-After") or headers.get("x-ms-ratelimit-microsoft.costmanagement-clienttype-retry-after")
        if ra:
            retry_after = float(ra)
    except (ValueError, KeyError):
        logger.debug("Could not parse Retry-After header", exc_info=True)

    if retry_after:
        logger.warning("Azure Retry-After: %.0fs", retry_after)
        return retry_after

    # Fallback: env-configurable waits (shorter for multi-RG runs)
    attempt = retry_state.attempt_number  # 1 = first retry
    waits = [
        int(_env_optional("RATE_LIMIT_WAIT_1", "30") or "30"),
        int(_env_optional("RATE_LIMIT_WAIT_2", "60") or "60"),
        int(_env_optional("RATE_LIMIT_WAIT_3", "120") or "120"),
    ]
    wait = waits[min(attempt - 1, len(waits) - 1)]
    return float(wait)


@retry(
    retry=retry_if_exception(_is_rate_limited),
    wait=_retry_after_wait,
    stop=stop_after_attempt(4),  # 1 initial + 3 retries
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def fetch_cost_rows(
    client: CostManagementClient,
    scope: str,
    date_from: datetime,
    date_to: datetime,
) -> list[dict[str, Any]]:
    """Fetch all cost rows from Azure Cost Management, handling pagination.

    Retries on 429 with waits of 60s, 120s, 300s before giving up.
    Returns a list of dicts keyed by the AZURE_QUERY_COLUMNS.
    """
    query_def = _build_query_definition(date_from, date_to)

    all_rows: list[dict[str, Any]] = []
    continuation_token: str | None = None

    while True:
        if continuation_token:
            result = client.query.usage_by_scope(  # type: ignore[attr-defined]
                scope=scope,
                parameters=query_def,
                skip_token=continuation_token,
            )
        else:
            result = client.query.usage(
                scope=scope,
                parameters=query_def,
            )

        columns = (
            [c.name for c in result.columns] if result.columns else AZURE_QUERY_COLUMNS
        )

        for row in result.rows:
            row_dict = dict(zip(columns, row, strict=False))
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

        logger.info(
            "Pagination: fetching next page with token %s…",
            str(continuation_token)[:40],
        )

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
    resource_type = str(row.get("ResourceType", "") or "")
    resource_location = str(row.get("ResourceLocation", "") or "")
    unit_of_measure = str(row.get("UnitOfMeasure", "") or "")
    usage_quantity = row.get("UsageQuantity") or row.get("totalQuantity") or None
    cost_billing = row.get("CostInBillingCurrency") or row.get("Cost", 0) or 0
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
    project_id = tags.get(
        "project", tags.get("Project", resource_group or subscription_id)
    )

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
        project_name=resource_group or None,
        service_category=service_category,
        service_name=service_name,
        resource_id=resource_group or None,
        resource_type=resource_type or None,
        region=resource_location or None,
        charge_type=str(row.get("ChargeType", "") or "") or None,
        cost_usd=cost_usd,
        currency_original=currency,
        cost_original=cost_original,
        discount_usd=Decimal("0"),
        net_cost_usd=cost_usd,
        usage_quantity=Decimal(str(usage_quantity)) if usage_quantity is not None else None,
        usage_unit=unit_of_measure or None,
        tags=tags,
    )


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

# Single source of truth for both the SQL column list and the row-tuple order,
# so the two can never drift out of sync (see SECURITY_AUDIT.md / audit doc P0-1).
# Safe from injection: this is a fixed module-level constant, never derived from
# request or record data.
_INSERT_COLUMNS = (
    "record_id", "provider", "usage_start", "usage_end", "ingestion_ts",
    "account_id", "account_name", "project_id", "project_name", "environment", "team",
    "service_category", "service_name", "resource_id", "resource_type", "region", "charge_type",
    "cost_usd", "currency_original", "cost_original", "discount_usd", "net_cost_usd",
    "usage_quantity", "usage_unit",
    "model_name", "input_tokens", "output_tokens", "total_tokens", "latency_ms", "trace_id",
    "tags",
)

_INSERT_SQL_BATCH = (
    f"INSERT INTO cost_records ({', '.join(_INSERT_COLUMNS)}) "  # noqa: S608
    f"VALUES ({', '.join(['%s'] * len(_INSERT_COLUMNS))}) "
    "ON CONFLICT (record_id) DO NOTHING"
)


@retry(
    retry=retry_if_exception_type(psycopg.OperationalError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _insert_batch(conn: psycopg.Connection, records: list[NormalizedCostRecord]) -> int:
    if not records:
        return 0
    rows = []
    for rec in records:
        row = rec.model_dump()
        row["provider"] = rec.provider.value
        row["service_category"] = rec.service_category.value
        row["tags"] = json.dumps(row.get("tags", {}))
        rows.append(tuple(row.get(col) for col in _INSERT_COLUMNS))
    with conn.cursor() as cur:
        cur.executemany(_INSERT_SQL_BATCH, rows)
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
    now = datetime.now(UTC)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO extractor_health (extractor_name, last_run_start, status, records_extracted, updated_at)
            VALUES (%s, %s, 'success', %s, %s)
            ON CONFLICT (extractor_name) DO UPDATE
            SET last_run_start = EXCLUDED.last_run_start,
                status = EXCLUDED.status,
                records_extracted = EXCLUDED.records_extracted,
                updated_at = EXCLUDED.updated_at
            """,
            (provider, now, rows_extracted, now),
        )
    conn.commit()


def mark_extractor_unhealthy(
    conn: psycopg.Connection,
    provider: str = "azure",
    error_message: str = "",
) -> None:
    """Mark a failed extractor run in the extractor_health table."""
    now = datetime.now(UTC)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO extractor_health (extractor_name, last_run_start, status, error_message, updated_at)
                VALUES (%s, %s, 'failed', %s, %s)
                ON CONFLICT (extractor_name) DO UPDATE
                SET last_run_start = EXCLUDED.last_run_start,
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message,
                    updated_at = EXCLUDED.updated_at
                """,
                (provider, now, error_message, now),
            )
        conn.commit()
    except psycopg.Error:
        logger.exception("Failed to mark extractor as unhealthy")


# ---------------------------------------------------------------------------
# Main extractor orchestrator
# ---------------------------------------------------------------------------


@retry(
    retry=retry_if_exception_type(ServiceRequestError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _create_azure_client(
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    subscription_id: str | None = None,
) -> CostManagementClient:
    """Authenticate and return a CostManagementClient.

    Credential resolution order:
    1. Explicit client_secret params (service principal)
    2. config.auth.get_azure_credential (keyring/azcli/DefaultAzureCredential)
    3. Fallback to AZURE_TENANT_ID/AZURE_CLIENT_ID/AZURE_CLIENT_SECRET env vars
    """
    sid = subscription_id or _env("AZURE_SUBSCRIPTION_ID")

    from config.auth import get_azure_credential

    if tenant_id and client_id and client_secret:
        from azure.identity import ClientSecretCredential

        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
    else:
        credential = get_azure_credential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    return CostManagementClient(credential=credential, subscription_id=sid)


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
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    health_provider: str | None = None,
    resource_groups: list[str] | None = None,
    resource_group: str | None = None,
) -> int:
    """Run the Azure cost extractor end-to-end.

    Returns the total number of records inserted.
    """
    sub_id = subscription_id or _env("AZURE_SUBSCRIPTION_ID")
    scope_type = scope_type or _env_optional("AZURE_SCOPE", "resourcegroup")
    mgmt_group_id = mgmt_group_id or _env_optional("AZURE_MGMT_GROUP_ID")
    resource_group = resource_group or _env_optional("AZURE_RESOURCE_GROUP")
    batch_size = batch_size or int(_env_optional("BATCH_SIZE", "500") or "500")
    exchange_rate_table = exchange_rate_table or _env_optional(
        "EXCHANGE_RATE_TABLE", "exchange_rates"
    )
    pg_dsn = pg_dsn or _env("PG_DSN")

    if date_from is None or date_to is None:
        default_from, default_to = _default_date_range()
        date_from = date_from or _parse_date(
            _env_optional("DATE_FROM", default_from.strftime("%Y-%m-%d")) or ""
        )
        date_to = date_to or _parse_date(
            _env_optional("DATE_TO", default_to.strftime("%Y-%m-%d")) or ""
        )

    provider_label = health_provider or "azure"

    logger.info(
        "Starting Azure cost extractor: scope=%s, subscription=%s, from=%s, to=%s",
        scope_type,
        sub_id,
        date_from.isoformat(),
        date_to.isoformat(),
    )

    client = _create_azure_client(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        subscription_id=sub_id,
    )
    scope = _build_scope(sub_id, scope_type, mgmt_group_id, resource_group)  # type: ignore[arg-type]

    raw_rows = fetch_cost_rows(client, scope, date_from, date_to)

    if resource_groups:
        rg_set = {rg.lower() for rg in resource_groups}
        raw_rows = [
            r for r in raw_rows if str(r.get("ResourceGroup", "")).lower() in rg_set
        ]
        logger.info(
            "Filtered to %d resource groups: %d rows remaining",
            len(resource_groups),
            len(raw_rows),
        )

    if not raw_rows:
        logger.info("No cost rows returned from Azure API — nothing to insert.")
        with psycopg.connect(pg_dsn) as conn:
            mark_extractor_healthy(conn, provider_label, date_from, date_to, 0)
        return 0

    with psycopg.connect(pg_dsn) as conn:
        exchange_rates = _load_exchange_rates(conn, exchange_rate_table)  # type: ignore[arg-type]

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
            mark_extractor_healthy(conn, provider_label, date_from, date_to, 0)
            return 0

        total_inserted = insert_records(conn, records, batch_size)
        logger.info(
            "Inserted %d of %d records into PostgreSQL", total_inserted, len(records)
        )

        mark_extractor_healthy(conn, provider_label, date_from, date_to, total_inserted)

    return total_inserted


def main() -> None:
    """Entrypoint for Cloud Run Job execution.

    Supports multi-subscription mode: when AZURE_{PREFIX}_SUBSCRIPTION_ID env vars
    are present, iterates over all discovered subscriptions. Falls back to
    single-subscription mode (AZURE_SUBSCRIPTION_ID) when no prefixed vars exist.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info("Azure Cost Extractor starting…")

    multi_subs = discover_azure_subscriptions_from_env()

    if not multi_subs:
        from config.auth import get_azure_subscription_selections

        saved_subs = get_azure_subscription_selections()
        if saved_subs:
            multi_subs = {}
            for sub in saved_subs:
                sid = sub.get("subscription_id", "")
                prefix = sid.replace("-", "_").upper()[:20]
                multi_subs[prefix] = {
                    "subscription_id": sid,
                    "tenant_id": sub.get("tenant_id", ""),
                    "client_id": sub.get("client_id", ""),
                    "client_secret": sub.get("client_secret", ""),
                    "scope": "subscription",
                    "resource_groups": sub.get("resource_groups", []),
                }

    if multi_subs:
        logger.info(
            "Multi-subscription mode: %d subscription(s) discovered", len(multi_subs)
        )
        grand_total = 0
        for prefix, cfg in multi_subs.items():
            rgs: list[str | None] = cfg.get("resource_groups", [])  # type: ignore[assignment]
            health_name = f"azure_{prefix.lower()}"
            logger.info(
                "Processing Azure subscription prefix=%s id=%s rgs=%d",
                prefix, cfg["subscription_id"], len(rgs) if rgs else 0,
            )

            # Iterate over every RG; fall back to subscription scope if no RGs
            rg_targets: list[str | None] = [rg for rg in rgs] if rgs else [None]
            sub_total = 0
            rg_delay = int(_env_optional("RG_API_DELAY_SECS", "5") or "5")
            for rg_idx, rg in enumerate(rg_targets):
                if rg_idx > 0 and rg_delay > 0:
                    import time
                    time.sleep(rg_delay)
                try:
                    scope = "resourcegroup" if rg else cfg.get("scope", "subscription")
                    total = run_extractor(
                        subscription_id=cfg["subscription_id"],
                        tenant_id=cfg["tenant_id"],
                        client_id=cfg["client_id"],
                        client_secret=cfg["client_secret"],
                        scope_type=scope,
                        mgmt_group_id=cfg.get("mgmt_group_id") or None,
                        health_provider=f"{health_name}_{rg.lower().replace('-','_')[:20]}" if rg else health_name,
                        resource_group=rg,
                    )
                    sub_total += total
                    logger.info("  RG %s: %d records inserted", rg or "(subscription)", total)
                except Exception:
                    logger.exception("  RG %s failed — skipping", rg or "(subscription)")
                    try:
                        pg_dsn = _env("PG_DSN")
                        with psycopg.connect(pg_dsn) as conn:
                            mark_extractor_unhealthy(
                                conn,
                                health_name,
                                f"Failed for RG {rg} in subscription {cfg['subscription_id']}",
                            )
                    except Exception:
                        logger.exception("Also failed to mark extractor unhealthy for %s / %s", health_name, rg)

            grand_total += sub_total
            logger.info("Subscription %s total: %d records", prefix, sub_total)

        logger.info(
            "Azure Cost Extractor completed: %d total records inserted", grand_total
        )
    else:
        # Single-subscription mode — support AZURE_RESOURCE_GROUPS CSV
        rgs_env = _env_optional("AZURE_RESOURCE_GROUPS", "")
        rg_list = [rg.strip() for rg in rgs_env.split(",") if rg.strip()] if rgs_env else []
        if not rg_list:
            rg_list = [_env_optional("AZURE_RESOURCE_GROUP")]  # type: ignore[list-item]

        rg_targets = [rg for rg in rg_list if rg] or [None]
        grand_total = 0
        rg_delay = int(_env_optional("RG_API_DELAY_SECS", "5") or "5")
        for idx, rg in enumerate(rg_targets):
            if idx > 0 and rg_delay > 0:
                import time
                time.sleep(rg_delay)
            try:
                scope = "resourcegroup" if rg else _env_optional("AZURE_SCOPE", "subscription") or "subscription"
                total = run_extractor(scope_type=scope, resource_group=rg)
                grand_total += total
                logger.info("RG %s: %d records inserted", rg or "(subscription)", total)
            except Exception:
                logger.exception("Azure Cost Extractor failed for RG %s — skipping", rg)
                try:
                    pg_dsn = _env("PG_DSN")
                    with psycopg.connect(pg_dsn) as conn:
                        mark_extractor_unhealthy(conn, "azure", f"Extractor failed for RG {rg} — see logs")
                except Exception:
                    logger.exception("Also failed to mark extractor as unhealthy")
        logger.info("Azure Cost Extractor completed: %d total records inserted", grand_total)


if __name__ == "__main__":
    main()
