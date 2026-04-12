"""Shared Pydantic models for FinOps multi-cloud cost normalization."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Provider(str, Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    LLM = "llm"


class ServiceCategory(str, Enum):
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
    ingestion_ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Organization
    account_id: str
    account_name: Optional[str] = None
    project_id: str
    project_name: Optional[str] = None
    environment: Optional[str] = None  # "prod" | "staging" | "dev"
    team: Optional[str] = None

    # Service
    service_category: ServiceCategory
    service_name: str
    resource_id: Optional[str] = None

    # Cost
    cost_usd: Decimal = Decimal("0")
    currency_original: str = "USD"
    cost_original: Decimal = Decimal("0")
    discount_usd: Decimal = Decimal("0")
    net_cost_usd: Decimal = Decimal("0")

    # Usage
    usage_quantity: Optional[Decimal] = None
    usage_unit: Optional[str] = None

    # LLM-specific
    model_name: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[float] = None
    trace_id: Optional[str] = None

    # Tags
    tags: dict[str, str] = Field(default_factory=dict)

    model_config = {"frozen": False}