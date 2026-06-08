"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Provider(StrEnum):
    AZURE = "azure"
    GCP = "gcp"
    LLM = "llm"


class CredentialType(StrEnum):
    SERVICE_PRINCIPAL = "service_principal"
    MANAGED_IDENTITY = "managed_identity"
    CLI = "cli"
    DEVICE_CODE = "device_code"


# ============================================================================
# Cloud Config schemas
# ============================================================================


class AzureConfigInput(BaseModel):
    """Azure configuration input."""

    tenant_id: str = Field(..., description="Azure AD tenant ID")
    client_id: str = Field(..., description="Service principal application ID")
    client_secret: str = Field(..., description="Service principal secret")
    subscription_id: str = Field(..., description="Azure subscription ID")
    resource_groups: list[str] = Field(
        default_factory=list,
        description="Resource groups to track (empty = all)",
    )
    scope: str = Field(
        default="resourcegroup",
        description="Query scope: subscription or resourcegroup",
    )
    environment: str | None = Field(None, description="prod / staging / dev")
    team: str | None = Field(None, description="Owning team")


class GCPConfigInput(BaseModel):
    """GCP configuration input."""

    project_id: str = Field(..., description="GCP project ID")
    billing_account_id: str | None = Field(None, description="GCP billing account ID")
    bigquery_dataset: str | None = Field(None, description="BigQuery dataset")
    bigquery_table: str | None = Field(None, description="BigQuery table name")
    environment: str | None = Field(None, description="prod / staging / dev")
    team: str | None = Field(None, description="Owning team")


class CloudConfigCreate(BaseModel):
    """Request schema for creating a cloud configuration."""

    provider: Provider
    name: str = Field(..., description="Human-readable name")
    credential_type: CredentialType = Field(
        default=CredentialType.SERVICE_PRINCIPAL,
        description="Authentication method",
    )
    config: dict[str, Any] = Field(..., description="Provider-specific config")


class CloudConfigUpdate(BaseModel):
    """Request schema for updating a cloud configuration."""

    name: str | None = None
    credential_type: CredentialType | None = None
    config: dict[str, Any] | None = None


class CloudConfigResponse(BaseModel):
    """Response schema for cloud configuration."""

    id: str
    provider: str
    name: str
    credential_type: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_test: str | None = None
    last_test_at: datetime | None = None
    tenant_id: str | None = None
    subscription_id: str | None = None
    project_id: str | None = None
    err: str | None = None


# ============================================================================
# Extractor Run schemas
# ============================================================================


class ExtractorRunRequest(BaseModel):
    """Request schema for starting an extractor run."""

    provider: Provider = Field(..., description="Cloud provider")
    config_id: str | None = Field(
        None,
        description="Specific config ID to use (defaults to first config for provider)",
    )
    extractor_type: str | None = Field(
        None,
        description="Extractor type (defaults to provider-specific)",
    )


class ExtractorRunResponse(BaseModel):
    """Response schema for extractor run."""

    id: str
    config_id: str
    provider: str
    extractor_type: str
    status: str
    started_at: datetime


class ExtractorStatusResponse(BaseModel):
    """Response schema for extractor status."""

    id: str
    config_id: str | None = None
    provider: str
    extractor_type: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    records_extracted: int = 0
    error_message: str | None = None


# ============================================================================
# Auth schemas
# ============================================================================


class DeviceCodeStartRequest(BaseModel):
    """Request schema for starting device code flow."""

    tenant_id: str = Field(default="organizations", description="Azure AD tenant ID")
    client_id: str | None = Field(None, description="Client ID (defaults to known public client)")


class DeviceCodeStartResponse(BaseModel):
    """Response schema for device code start."""

    verification_uri: str
    user_code: str
    device_code: str
    expires_in: int
    interval: int
    message: str


class DeviceCodePollRequest(BaseModel):
    """Request schema for polling device code flow."""

    device_code: str
    tenant_id: str = Field(default="organizations")


class DeviceCodePollResponse(BaseModel):
    """Response schema for device code poll."""

    status: str  # "pending" | "completed" | "expired" | "failed"
    config_id: str | None = None  # Only when completed


# ============================================================================
# Token schemas
# ============================================================================


class TokenRequest(BaseModel):
    """Request schema for token endpoint."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Response schema for token endpoint."""

    access_token: str
    token_type: str = "bearer"  # noqa: S105


# ============================================================================
# Health schemas
# ============================================================================


class ExtractorHealthResponse(BaseModel):
    """Response schema for extractor health."""

    name: str
    status: str
    last_run: datetime
    records_count: int = 0


# ============================================================================#
# Extractor Registry schemas                                                  #
# ============================================================================#


class ExtractorCreate(BaseModel):
    """Request schema for creating an extractor."""

    name: str = Field(..., description="Human-readable name")
    provider: str = Field(..., description="Cloud provider")
    extractor_type: str = Field(..., description="Extractor type (e.g., azure_cost, gcp_billing)")
    enabled: bool = Field(default=True, description="Whether the extractor is enabled")
    schedule: str | None = Field(None, description="Cron expression for scheduled runs")
    config_id: str | None = Field(None, description="Cloud config ID to use")


class ExtractorUpdate(BaseModel):
    """Request schema for updating an extractor."""

    name: str | None = None
    enabled: bool | None = None
    schedule: str | None = None
    config_id: str | None = None


class ExtractorResponse(BaseModel):
    """Response schema for extractor."""

    id: str
    name: str
    provider: str
    extractor_type: str
    enabled: bool
    schedule: str | None
    config_id: str | None
    status: str
    last_run_id: str | None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ExtractorListResponse(BaseModel):
    """Response schema for extractor list."""

    extractors: list[ExtractorResponse]
    count: int


class ExtractorRunTriggerRequest(BaseModel):
    """Request schema for triggering an extractor run."""

    config_id: str | None = Field(
        None,
        description="Specific config ID to use (defaults to the extractor's config_id)"
    )


class ExtractorRunTriggerResponse(BaseModel):
    """Response schema for extractor run trigger."""

    run_id: str
    status: str
    extractor_id: str


# ============================================================================
# Alert schemas
# ============================================================================


class AlertStatus(StrEnum):
    FIRING = "firing"
    ACKNOWLEDGED = "ack"
    RESOLVED = "resolved"


class AlertSeverity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertRecord(BaseModel):
    """Response schema for a single alert."""

    id: str
    status: AlertStatus
    severity: AlertSeverity
    description: str
    rule: str | None = None
    project: str | None = None
    triggered_at: str | None = None
    cost_impact: float = 0.0
    resource: str = ""
    service: str = ""
    provider: str = ""
    is_acknowledged: bool = False
    first_seen: str | None = None
    last_seen: str | None = None


class AlertStatsResponse(BaseModel):
    """Response schema for alert statistics."""

    by_status: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    total: int = 0


# ============================================================================
# Project schemas
# ============================================================================


class ProjectResponse(BaseModel):
    """Response schema for a project."""

    id: str
    name: str
    slug: str
    owner: str
    cost_center: str
    budget_cap: float | None = None
    mtd: float = 0.0
    tags: dict[str, Any] = {}
    note: str = ""
    provider: str | None = None
    created: str | None = None


class ProjectCreate(BaseModel):
    """Request schema for creating a project."""

    name: str
    slug: str | None = None
    owner: str | None = None
    cost_center: str | None = None
    budget_cap: float | None = None
    tags: dict[str, Any] = {}
    note: str = ""
    provider: str | None = None


# ============================================================================
# Wastage schemas
# ============================================================================


class WastageStatus(StrEnum):
    OPEN = "open"
    ACKED = "acked"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class WastageSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class WastageFindingResponse(BaseModel):
    """Response schema for a single wastage finding."""

    finding_id: str
    provider: str
    account_id: str
    resource_group: str | None = None
    region: str | None = None
    resource_id: str
    resource_type: str
    rule_id: str
    severity: str
    category: str
    estimated_monthly_usd: float = 0.0
    currency: str = "USD"
    evidence: dict[str, Any] = {}
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    status: str = "open"
    tags: dict[str, str] = {}


class WastageRuleResponse(BaseModel):
    """Response schema for a rule catalog entry."""

    id: str
    severity: str
    category: str
    description: str


class WastageSummaryCategory(BaseModel):
    """Per-category summary entry."""

    category: str
    finding_count: int
    total_monthly_usd: float


class WastageSummaryResponse(BaseModel):
    """Response schema for the wastage summary endpoint."""

    categories: list[WastageSummaryCategory] = []
    total_monthly_usd: float = 0.0
    total_finding_count: int = 0


class WastageScanRunResponse(BaseModel):
    """Response schema for a scan run record."""

    id: str
    provider: str
    started_at: str | None = None
    finished_at: str | None = None
    status: str
    findings_count: int | None = None
    error: str | None = None


class IgnoreRequest(BaseModel):
    """Request body for POST /wastage/{finding_id}/ignore."""

    reason: str = ""


class ScanRequest(BaseModel):
    """Request body for POST /wastage/scan."""

    provider: str
