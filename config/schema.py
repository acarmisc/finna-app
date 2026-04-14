"""Pydantic models for multi-subscription, multi-project FinOps configuration.

Supports:
  GCP  → billing account → multiple projects (ingestion via BigQuery or CSV)
  Azure → multiple subscriptions → multiple resource groups per subscription
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# GCP ingestion mode
# ---------------------------------------------------------------------------


class GCPIngestionMode(str, Enum):
    """How GCP billing data is ingested."""

    bigquery = "bigquery"
    csv = "csv"


# ---------------------------------------------------------------------------
# GCP configuration
# ---------------------------------------------------------------------------


class GCPProjectConfig(BaseModel):
    """A single GCP project with its billing configuration."""

    project_id: str = Field(..., description="GCP project ID (e.g. my-project-prod)")
    project_name: Optional[str] = Field(None, description="Human-readable name")
    ingestion_mode: GCPIngestionMode = Field(
        GCPIngestionMode.bigquery,
        description="Ingestion mode: bigquery or csv",
    )
    bigquery_dataset: Optional[str] = Field(
        None,
        description="BigQuery dataset for billing export (required when ingestion_mode=bigquery)",
    )
    bigquery_table: Optional[str] = Field(
        None, description="BigQuery table name (required when ingestion_mode=bigquery)"
    )
    csv_path: Optional[str] = Field(
        None,
        description="Path to CSV billing export file (required when ingestion_mode=csv)",
    )
    environment: Optional[str] = Field(None, description="prod / staging / dev")
    team: Optional[str] = Field(None, description="Owning team")


class GCPConfig(BaseModel):
    """GCP provider configuration — one billing account, multiple projects."""

    enabled: bool = True
    auth_method: str = Field(
        "adc",
        description="Authentication method: 'adc', 'service_account', or 'skipped'",
    )
    billing_account_id: Optional[str] = Field(
        None, description="GCP billing account ID"
    )
    service_account_key_path: Optional[str] = Field(
        None, description="Path to service account JSON key file"
    )
    projects: list[GCPProjectConfig] = Field(default_factory=list)

    @field_validator("projects")
    @classmethod
    def validate_projects(cls, v: list[GCPProjectConfig]) -> list[GCPProjectConfig]:
        if not v:
            raise ValueError("At least one GCP project is required when GCP is enabled")
        for project in v:
            if project.ingestion_mode == GCPIngestionMode.bigquery:
                if not project.bigquery_dataset:
                    raise ValueError(
                        f"bigquery_dataset is required for project '{project.project_id}' "
                        f"when ingestion_mode is 'bigquery'"
                    )
            if project.ingestion_mode == GCPIngestionMode.csv:
                if not project.csv_path:
                    raise ValueError(
                        f"csv_path is required for project '{project.project_id}' "
                        f"when ingestion_mode is 'csv'"
                    )
        return v


# ---------------------------------------------------------------------------
# Azure configuration
# ---------------------------------------------------------------------------


class AzureSubscriptionConfig(BaseModel):
    """A single Azure subscription with its credentials and resource groups."""

    subscription_id: str = Field(..., description="Azure subscription ID (UUID)")
    subscription_name: Optional[str] = Field(None, description="Human-readable name")
    tenant_id: str = Field(..., description="Azure AD tenant ID")
    client_id: str = Field("", description="Service principal application ID")
    client_secret: str = Field(
        "",
        description="Service principal secret (or ${ENV_VAR} reference). Empty when auth_method=device_code.",
    )
    auth_method: str = Field(
        "client_secret",
        description="Authentication method: 'client_secret' or 'device_code'",
    )
    resource_groups: list[str] = Field(
        default_factory=list, description="Resource groups to track (empty = all)"
    )
    environment: Optional[str] = Field(None, description="prod / staging / dev")
    team: Optional[str] = Field(None, description="Owning team")
    scope: str = Field(
        "subscription", description="Query scope: subscription or managementgroup"
    )
    management_group_id: Optional[str] = Field(
        None, description="Required when scope=managementgroup"
    )


class AzureConfig(BaseModel):
    """Azure provider configuration — multiple subscriptions, each with resource groups."""

    enabled: bool = True
    subscriptions: list[AzureSubscriptionConfig] = Field(default_factory=list)

    @field_validator("subscriptions")
    @classmethod
    def at_least_one_subscription(
        cls, v: list[AzureSubscriptionConfig]
    ) -> list[AzureSubscriptionConfig]:
        if not v:
            raise ValueError(
                "At least one Azure subscription is required when Azure is enabled"
            )
        return v


# ---------------------------------------------------------------------------
# Aggregation settings
# ---------------------------------------------------------------------------


class AggregationSettings(BaseModel):
    """Per-metric-type aggregation window and retention."""

    window_size_minutes: int = Field(15, description="Aggregation window in minutes")
    retention_days: int = Field(365, description="Data retention in days")


class AggregationConfig(BaseModel):
    """Full aggregation configuration for a client."""

    infra_metrics: AggregationSettings = Field(
        default_factory=lambda: AggregationSettings(
            window_size_minutes=15, retention_days=365
        )
    )
    llm_requests: AggregationSettings = Field(
        default_factory=lambda: AggregationSettings(
            window_size_minutes=5, retention_days=180
        )
    )
    billing: AggregationSettings = Field(
        default_factory=lambda: AggregationSettings(
            window_size_minutes=60, retention_days=730
        )
    )


# ---------------------------------------------------------------------------
# PostgreSQL target
# ---------------------------------------------------------------------------


class PostgreSQLConfig(BaseModel):
    """Connection to the FinOps PostgreSQL database (Cloud SQL or local)."""

    host: str = Field("localhost", description="Hostname or IP")
    port: int = Field(5432, description="Port")
    database: str = Field("finops", description="Database name")
    user: str = Field("finops", description="Database user")
    password: str = Field("", description="Password (or ${ENV_VAR} reference)")
    ssl_mode: str = Field("prefer", description="SSL mode: disable, prefer, require")

    @property
    def dsn(self) -> str:
        pw = self.password
        return f"postgresql://{self.user}:{pw}@{self.host}:{self.port}/{self.database}?sslmode={self.ssl_mode}"


# ---------------------------------------------------------------------------
# Superset configuration
# ---------------------------------------------------------------------------


class SupersetConfig(BaseModel):
    """Apache Superset visualization layer."""

    enabled: bool = True
    host: str = Field("localhost", description="Superset host")
    port: int = Field(8088, description="Superset port")
    admin_username: str = Field("admin", description="Initial admin username")
    admin_password: str = Field("admin", description="Initial admin password")
    admin_email: str = Field("admin@finops.local", description="Initial admin email")
    secret_key: str = Field(
        "CHANGE_ME_TO_A_LONG_RANDOM_STRING", description="Flask secret key"
    )


# ---------------------------------------------------------------------------
# Root configuration
# ---------------------------------------------------------------------------


class ClientConfig(BaseModel):
    """Complete FinOps client configuration — multiple subscriptions per provider."""

    client_id: str = Field(
        ..., description="Unique client identifier (lowercase, hyphens)"
    )
    client_name: str = Field(..., description="Human-readable client name")
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    postgresql: PostgreSQLConfig = Field(default_factory=PostgreSQLConfig)
    superset: SupersetConfig = Field(default_factory=SupersetConfig)

    gcp: Optional[GCPConfig] = Field(
        None, description="GCP provider config (set when enabled)"
    )
    azure: Optional[AzureConfig] = Field(
        None, description="Azure provider config (set when enabled)"
    )

    aggregation: AggregationConfig = Field(default_factory=AggregationConfig)

    @property
    def enabled_providers(self) -> list[str]:
        """Return list of enabled provider names."""
        providers = []
        if self.gcp and self.gcp.enabled:
            providers.append("gcp")
        if self.azure and self.azure.enabled:
            providers.append("azure")
        return providers

    def to_env_dict(self) -> dict[str, str]:
        """Export the configuration as environment variables for extractors."""
        env: dict[str, str] = {"PG_DSN": self.postgresql.dsn}

        if self.gcp and self.gcp.enabled:
            for project in self.gcp.projects:
                prefix = f"GCP_{project.project_id.upper().replace('-', '_')}"
                env[f"{prefix}_PROJECT"] = project.project_id
                env[f"{prefix}_INGESTION_MODE"] = project.ingestion_mode.value
                if project.bigquery_dataset:
                    env[f"{prefix}_BQ_DATASET"] = project.bigquery_dataset
                if project.bigquery_table:
                    env[f"{prefix}_BQ_TABLE"] = project.bigquery_table
                if project.csv_path:
                    env[f"{prefix}_CSV_PATH"] = project.csv_path

        if self.azure and self.azure.enabled:
            for sub in self.azure.subscriptions:
                prefix = f"AZURE_{sub.subscription_id.upper().replace('-', '_')}"
                env[f"{prefix}_SUBSCRIPTION_ID"] = sub.subscription_id
                env[f"{prefix}_TENANT_ID"] = sub.tenant_id
                env[f"{prefix}_CLIENT_ID"] = sub.client_id
                env[f"{prefix}_CLIENT_SECRET"] = sub.client_secret
                if sub.resource_groups:
                    env[f"{prefix}_RESOURCE_GROUPS"] = ",".join(sub.resource_groups)

        return env
