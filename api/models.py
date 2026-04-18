"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Provider(str, Enum):
    AZURE = "azure"
    GCP = "gcp"
    AWS = "aws"
    LLM = "llm"
    ECB = "ecb"


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
