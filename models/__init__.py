"""Shared Pydantic models for FinOps multi-cloud cost normalization."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class Provider(StrEnum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    LLM = "llm"


class ServiceCategory(StrEnum):
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    DATABASE = "database"
    ML = "ml"
    LLM = "llm"
    OTHER = "other"


class NormalizedCostRecord(BaseModel):
    """Unified cost record across all cloud providers and LLM usage."""

    # Identity
    record_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: Provider

    # Time
    usage_start: datetime
    usage_end: datetime
    ingestion_ts: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Organization
    account_id: str
    account_name: str | None = None
    project_id: str
    project_name: str | None = None
    environment: str | None = None  # "prod" | "staging" | "dev"
    team: str | None = None

    # Service
    service_category: ServiceCategory
    service_name: str
    resource_id: str | None = None
    resource_type: str | None = None   # e.g. "microsoft.compute/virtualmachines"
    region: str | None = None          # e.g. "westeurope", "us-central1"
    charge_type: str | None = None     # "Usage" | "Tax" | "Credit" | "Adjustment"

    # Cost
    cost_usd: Decimal = Decimal("0")
    currency_original: str = "USD"
    cost_original: Decimal = Decimal("0")
    discount_usd: Decimal = Decimal("0")
    net_cost_usd: Decimal = Decimal("0")

    # Usage
    usage_quantity: Decimal | None = None
    usage_unit: str | None = None

    # LLM-specific
    model_name: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: float | None = None
    trace_id: str | None = None

    # Tags
    tags: dict[str, str] = Field(default_factory=dict)

    model_config = {"frozen": False}
