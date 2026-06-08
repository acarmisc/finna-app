"""Shared normalization utilities for GCP billing extractors.

Used by both BigQuery and CSV extractors to avoid code duplication.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from models import NormalizedCostRecord, Provider, ServiceCategory

# ---------------------------------------------------------------------------
# Service-category mapping
# ---------------------------------------------------------------------------

DEFAULT_SERVICE_CATEGORY_MAP: dict[str, ServiceCategory] = {
    "Compute Engine": ServiceCategory.COMPUTE,
    "Kubernetes Engine": ServiceCategory.COMPUTE,
    "Cloud Functions": ServiceCategory.COMPUTE,
    "Cloud Run": ServiceCategory.COMPUTE,
    "App Engine": ServiceCategory.COMPUTE,
    "Cloud Storage": ServiceCategory.STORAGE,
    "Persistent Disk": ServiceCategory.STORAGE,
    "Filestore": ServiceCategory.STORAGE,
    "Cloud SQL": ServiceCategory.DATABASE,
    "Cloud Spanner": ServiceCategory.DATABASE,
    "Cloud Bigtable": ServiceCategory.DATABASE,
    "Firestore": ServiceCategory.DATABASE,
    "Cloud Memorystore": ServiceCategory.DATABASE,
    "Cloud VPN": ServiceCategory.NETWORK,
    "Cloud Interconnect": ServiceCategory.NETWORK,
    "Cloud Load Balancing": ServiceCategory.NETWORK,
    "Cloud CDN": ServiceCategory.NETWORK,
    "Cloud DNS": ServiceCategory.NETWORK,
    "Cloud Networking": ServiceCategory.NETWORK,
    "Vertex AI": ServiceCategory.ML,
    "AI Platform": ServiceCategory.ML,
    "Cloud Machine Learning": ServiceCategory.ML,
    "Dialogflow": ServiceCategory.ML,
    "Cloud Vision": ServiceCategory.ML,
    "Cloud Natural Language": ServiceCategory.ML,
    "Speech-to-Text": ServiceCategory.ML,
}


def resolve_service_category(
    service_description: str,
    mapping: dict[str, ServiceCategory] | None = None,
) -> ServiceCategory:
    """Look up a GCP service description in the mapping table.

    Falls back to substring matching and ultimately ``ServiceCategory.OTHER``.
    """
    lookup = mapping if mapping is not None else DEFAULT_SERVICE_CATEGORY_MAP

    # Exact match first
    if service_description in lookup:
        return lookup[service_description]

    # Substring match — e.g. "Compute Engine API" → Compute Engine
    for key, category in lookup.items():
        if key.lower() in service_description.lower():
            return category

    return ServiceCategory.OTHER


# ---------------------------------------------------------------------------
# Deterministic record ID
# ---------------------------------------------------------------------------


def generate_record_id(
    provider: str,
    project_id: str,
    usage_start: str,
    service_name: str,
) -> str:
    """Generate a deterministic record_id from key fields.

    Uses SHA-256 over a concatenation of provider + project + usage_start +
    service_name so the same billing row always produces the same ID,
    enabling idempotent re-runs.
    """
    raw = f"{provider}|{project_id}|{usage_start}|{service_name}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Datetime parsing
# ---------------------------------------------------------------------------


def parse_datetime(value: Any) -> datetime:
    """Coerce a datetime / str / None into an aware UTC datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed
    # Fallback
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Labels / tags parsing
# ---------------------------------------------------------------------------


def extract_project_label(row: dict[str, Any]) -> str:
    """Pull the ``project`` label from the GCP labels array.

    GCP billing exports encode labels as ``REPEATED<STRUCT<key STRING, value STRING>>``.
    The BigQuery SDK returns these as a list of dicts with ``key``/``value`` keys.
    CSV exports may have labels as a semicolon-separated string like ``key1:value1;key2:value2``.
    """
    labels = row.get("labels") or []

    # BigQuery format: list of dicts
    if isinstance(labels, list):
        for entry in labels:
            if isinstance(entry, dict) and entry.get("key") == "project":
                return entry.get("value", "")  # type: ignore[no-any-return]

    # CSV format: semicolon-separated "key:value" pairs
    if isinstance(labels, str) and labels.strip():
        for pair in labels.split(";"):
            pair = pair.strip()
            if ":" in pair:
                k, v = pair.split(":", 1)
                if k.strip() == "project":
                    return v.strip()

    return ""


def labels_to_tags(row: dict[str, Any]) -> dict[str, str]:
    """Convert GCP billing labels to a plain ``{key: value}`` dict.

    Handles three formats:
    - BigQuery: list of dicts with ``key``/``value`` keys
    - CSV: semicolon-separated ``key:value`` pairs
    - Dict: already a flat mapping
    """
    labels = row.get("labels") or []

    if isinstance(labels, list):
        return {
            entry["key"]: entry.get("value", "")
            for entry in labels
            if isinstance(entry, dict) and "key" in entry
        }

    if isinstance(labels, str) and labels.strip():
        tags: dict[str, str] = {}
        for pair in labels.split(";"):
            pair = pair.strip()
            if ":" in pair:
                k, v = pair.split(":", 1)
                tags[k.strip()] = v.strip()
        return tags

    if isinstance(labels, dict):
        return {k: str(v) for k, v in labels.items() if v is not None}

    return {}


# ---------------------------------------------------------------------------
# CSV column name mapping
# ---------------------------------------------------------------------------

# Maps GCP Standard billing export CSV column names to our internal field names.
# The BigQuery export uses dots in nested field names (e.g. "project.id");
# CSV headers may use either dots or underscores depending on the export version.
CSV_COLUMN_MAP: dict[str, str] = {
    "billing_account_id": "billing_account_id",
    "project.id": "project_id",
    "project_id": "project_id",
    "project.number": "project_number",
    "project_number": "project_number",
    "project.name": "project_name",
    "project_name": "project_name",
    "service.description": "service_description",
    "service_description": "service_description",
    "sku.description": "sku_description",
    "sku_description": "sku_description",
    "usage_start_time": "usage_start_time",
    "usage_end_time": "usage_end_time",
    "cost": "cost",
    "currency": "currency",
    "currency_conversion_rate": "currency_conversion_rate",
    "usage.amount": "usage_amount",
    "usage_amount": "usage_amount",
    "usage.unit": "usage_unit",
    "usage_unit": "usage_unit",
    "labels": "labels",
    "system_labels": "system_labels",
}


def normalize_csv_row(
    row: dict[str, str],
    service_category_map: dict[str, ServiceCategory] | None = None,
) -> NormalizedCostRecord:
    """Map a single CSV billing row to a :class:`NormalizedCostRecord`.

    CSV rows are all strings; this function handles type coercion.
    """
    # Map CSV column names to internal names
    mapped: dict[str, Any] = {}
    for csv_col, val in row.items():
        internal = CSV_COLUMN_MAP.get(csv_col.strip(), csv_col.strip())
        mapped[internal] = val

    project_id = (mapped.get("project_id") or "").strip()
    project_name = (mapped.get("project_name") or "").strip()
    label_project = extract_project_label(row)
    service_description = (mapped.get("service_description") or "").strip()
    sku_description = (mapped.get("sku_description") or "").strip()
    usage_start = parse_datetime(mapped.get("usage_start_time", ""))
    usage_end = parse_datetime(mapped.get("usage_end_time", ""))

    # Cost
    try:
        cost_decimal = Decimal(mapped.get("cost", "0") or "0")
    except Exception:
        cost_decimal = Decimal("0")

    # Currency
    currency = (mapped.get("currency") or "USD").strip()

    # Usage
    try:
        usage_decimal = Decimal(mapped.get("usage_amount", "0") or "0") if mapped.get("usage_amount") else None
    except Exception:
        usage_decimal = None

    usage_unit = (mapped.get("usage_unit") or "").strip() or None

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
        account_id=mapped.get("billing_account_id", "") or "",
        project_id=label_project or project_id,
        project_name=project_name or None,
        service_category=resolve_service_category(service_description, service_category_map),
        service_name=sku_description,
        cost_usd=cost_decimal,
        currency_original=currency,
        cost_original=cost_decimal,
        net_cost_usd=cost_decimal,
        usage_quantity=usage_decimal,
        usage_unit=usage_unit,
        tags=labels_to_tags(row),
    )
