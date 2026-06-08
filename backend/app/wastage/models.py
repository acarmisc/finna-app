"""Pydantic models for resource wastage tables.

These mirror the DB schema created in alembic/versions/006_resource_wastage.py.
All fields match column names exactly so callers can do ``model.model_dump()``
straight into an INSERT/UPSERT without renaming.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WastageStatus(StrEnum):
    OPEN = "open"
    ACKED = "acked"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class ResourceWastage(BaseModel):
    """One finding: a single (provider, resource_id, rule_id) wastage signal."""

    finding_id: str = Field(description="SHA-256 hash of (provider, resource_id, rule_id)")
    provider: str
    account_id: str
    resource_group: str | None = None
    region: str | None = None
    resource_id: str
    resource_type: str
    rule_id: str
    severity: str  # critical | high | medium | low | info
    category: str  # compute | storage | network | database | other
    estimated_monthly_usd: Decimal = Decimal("0")
    currency: str = "USD"
    evidence: dict[str, Any] = Field(default_factory=dict)
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: WastageStatus = WastageStatus.OPEN
    tags: dict[str, str] = Field(default_factory=dict)

    model_config = {"frozen": False}


class WastageScanRun(BaseModel):
    """Audit record for a single scan execution."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    status: str = "running"  # running | done | error
    findings_count: int | None = None
    error: str | None = None

    model_config = {"frozen": False}
