"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Provider(str, Enum):
    AZURE = "azure"
    GCP = "gcp"
    LLM = "llm"


class CredentialType(str, Enum):
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
    environment: Optional[str] = Field(None, description="prod / staging / dev")
    team: Optional[str] = Field(None, description="Owning team")


class GCPConfigInput(BaseModel):
    """GCP configuration input."""

    project_id: str = Field(..., description="GCP project ID")
    billing_account_id: Optional[str] = Field(None, description="GCP billing account ID")
    bigquery_dataset: Optional[str] = Field(None, description="BigQuery dataset")
    bigquery_table: Optional[str] = Field(None, description="BigQuery table name")
    environment: Optional[str] = Field(None, description="prod / staging / dev")
    team: Optional[str] = Field(None, description="Owning team")


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

    name: Optional[str] = None
    credential_type: Optional[CredentialType] = None
    config: Optional[dict[str, Any]] = None


class CloudConfigResponse(BaseModel):
    """Response schema for cloud configuration."""

    id: str
    provider: str
    name: str
    credential_type: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_test: Optional[str] = None
    last_test_at: Optional[datetime] = None
    tenant_id: Optional[str] = None
    subscription_id: Optional[str] = None
    project_id: Optional[str] = None
    err: Optional[str] = None


# ============================================================================
# Extractor Run schemas
# ============================================================================


class ExtractorRunRequest(BaseModel):
    """Request schema for starting an extractor run."""

    provider: Provider = Field(..., description="Cloud provider")
    config_id: Optional[str] = Field(
        None,
        description="Specific config ID to use (defaults to first config for provider)",
    )
    extractor_type: Optional[str] = Field(
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
    config_id: Optional[str] = None
    provider: str
    extractor_type: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    records_extracted: int = 0
    error_message: Optional[str] = None


# ============================================================================
# Auth schemas
# ============================================================================


class DeviceCodeStartRequest(BaseModel):
    """Request schema for starting device code flow."""

    tenant_id: str = Field(default="organizations", description="Azure AD tenant ID")
    client_id: Optional[str] = Field(None, description="Client ID (defaults to known public client)")


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
    config_id: Optional[str] = None  # Only when completed


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
    token_type: str = "bearer"


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
    schedule: Optional[str] = Field(None, description="Cron expression for scheduled runs")
    config_id: Optional[str] = Field(None, description="Cloud config ID to use")


class ExtractorUpdate(BaseModel):
    """Request schema for updating an extractor."""

    name: Optional[str] = None
    enabled: Optional[bool] = None
    schedule: Optional[str] = None
    config_id: Optional[str] = None


class ExtractorResponse(BaseModel):
    """Response schema for extractor."""

    id: str
    name: str
    provider: str
    extractor_type: str
    enabled: bool
    schedule: Optional[str]
    config_id: Optional[str]
    status: str
    last_run_id: Optional[str]
    last_run_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ExtractorListResponse(BaseModel):
    """Response schema for extractor list."""

    extractors: list[ExtractorResponse]
    count: int


class ExtractorRunTriggerRequest(BaseModel):
    """Request schema for triggering an extractor run."""

    config_id: Optional[str] = Field(
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


class AlertStatus(str, Enum):
    FIRING = "firing"
    ACKNOWLEDGED = "ack"
    RESOLVED = "resolved"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertRecord(BaseModel):
    """Response schema for a single alert."""

    id: str
    status: AlertStatus
    severity: AlertSeverity
    description: str
    rule: Optional[str] = None
    project: Optional[str] = None
    triggered_at: Optional[str] = None
    cost_impact: float = 0.0
    resource: str = ""
    service: str = ""
    provider: str = ""
    is_acknowledged: bool = False
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None


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
    budget_cap: Optional[float] = None
    mtd: float = 0.0
    tags: dict[str, Any] = {}
    note: str = ""
    provider: Optional[str] = None
    created: Optional[str] = None


class ProjectCreate(BaseModel):
    """Request schema for creating a project."""

    name: str
    slug: Optional[str] = None
    owner: Optional[str] = None
    cost_center: Optional[str] = None
    budget_cap: Optional[float] = None
    tags: dict[str, Any] = {}
    note: str = ""
    provider: Optional[str] = None
