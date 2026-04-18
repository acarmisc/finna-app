"""Plugin registration for built-in extractors.

This module registers Finna's four built-in extractors as ExtractorPlugin
subclasses WITHOUT modifying the original extractor files. Each built-in
extractor keeps its standalone `main()` entry point for backward compatibility,
while also being available as a plugin through the registry.

External contributors can add new extractors by:
  1. Creating a new Python module in extractors/
  2. Subclassing ExtractorPlugin from extractors.base
  3. Using the @extractor_plugin decorator
  4. Adding the module to DISCOVERY_MODULES below
"""

from __future__ import annotations

import importlib
import logging
import os

from extractors.base import ExtractorPlugin, ConfigField, extractor_plugin, _REGISTRY

logger = logging.getLogger(__name__)

# Modules to auto-discover and register. Add new extractors here.
DISCOVERY_MODULES = [
    "extractors.gcp_billing",
    "extractors.gcp_csv",
    "extractors.azure_cost",
    "extractors.exchange_rates",
]


@extractor_plugin(
    "gcp_billing",
    display_name="GCP Billing (BigQuery)",
    description="Extracts cost data from GCP BigQuery billing export.",
)
class GCPBillingPlugin(ExtractorPlugin):
    def extract(self) -> int:
        from extractors.gcp_billing import extract

        return extract(
            project_id=self.config.get("project_id", os.getenv("GCP_PROJECT", "")),
            dataset=self.config.get("bigquery_dataset", os.getenv("BQ_DATASET", "")),
            table=self.config.get("bigquery_table", os.getenv("BQ_TABLE", "")),
            pg_dsn=self.pg_dsn,
        )

    def health_name(self) -> str:
        return "gcp_billing"

    @classmethod
    def config_fields(cls) -> list[ConfigField]:
        return [
            ConfigField(name="project_id", label="GCP Project ID", placeholder="my-project-id"),
            ConfigField(
                name="bigquery_dataset", label="BigQuery Dataset", placeholder="billing_export", required=False
            ),
            ConfigField(
                name="bigquery_table", label="BigQuery Table", placeholder="gcp_billing_export_v1", required=False
            ),
        ]

    @classmethod
    def auth_methods(cls) -> list[dict[str, str]]:
        return [
            {"id": "adc", "label": "Application Default Credentials", "sub": "Uses `gcloud auth login`"},
            {
                "id": "sakey",
                "label": "Service account JSON key",
                "sub": "Least-privilege IAM · roles/bigquery.dataViewer",
            },
        ]


@extractor_plugin(
    "gcp_csv",
    display_name="GCP Billing (CSV)",
    description="Extracts cost data from a GCP billing CSV export file.",
)
class GCPCSVPlugin(ExtractorPlugin):
    def extract(self) -> int:
        from extractors.gcp_csv import extract

        return extract(
            csv_path=self.config.get("csv_path", os.getenv("GCP_CSV_PATH", "")),
            project_id=self.config.get("project_id", os.getenv("GCP_PROJECT", "")),
            pg_dsn=self.pg_dsn,
        )

    def health_name(self) -> str:
        return "gcp_csv"

    @classmethod
    def config_fields(cls) -> list[ConfigField]:
        return [
            ConfigField(name="csv_path", label="CSV File Path", placeholder="/path/to/billing.csv"),
            ConfigField(name="project_id", label="GCP Project ID", placeholder="my-project-id"),
        ]


@extractor_plugin(
    "azure_cost",
    display_name="Azure Cost Management",
    description="Extracts cost data from Azure Cost Management REST API.",
)
class AzureCostPlugin(ExtractorPlugin):
    def extract(self) -> int:
        from extractors.azure_cost import run_extractor

        return run_extractor(pg_dsn=self.pg_dsn)

    def health_name(self) -> str:
        return "azure_cost"

    @classmethod
    def config_fields(cls) -> list[ConfigField]:
        return [
            ConfigField(name="subscription_id", label="Azure Subscription ID", placeholder="xxxxxxxx-xxxx-xxxx-xxxx"),
            ConfigField(
                name="tenant_id", label="Azure AD Tenant ID", placeholder="xxxxxxxx-xxxx-xxxx-xxxx", required=False
            ),
            ConfigField(
                name="client_id",
                label="Client ID",
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx",
                field_type="password",
                required=False,
            ),
            ConfigField(
                name="client_secret", label="Client Secret", placeholder="", field_type="password", required=False
            ),
            ConfigField(name="resource_groups", label="Resource Groups (comma-sep)", placeholder="", required=False),
            ConfigField(
                name="scope",
                label="Query Scope",
                placeholder="subscription",
                required=False,
                options=[
                    {"value": "subscription", "label": "Full subscription"},
                    {"value": "resourcegroup", "label": "Resource group(s)"},
                ],
            ),
        ]

    @classmethod
    def auth_methods(cls) -> list[dict[str, str]]:
        return [
            {
                "id": "device",
                "label": "Device code (browser)",
                "sub": "Recommended for local dev · cached in OS keyring",
            },
            {"id": "sp", "label": "Service principal", "sub": "Client ID + secret · for production"},
            {"id": "cli", "label": "Azure CLI", "sub": "Uses current `az login` session"},
        ]


@extractor_plugin(
    "exchange_rates",
    display_name="Exchange Rates (ECB)",
    description="Fetches daily ECB exchange rates and upserts to PostgreSQL.",
)
class ExchangeRatesPlugin(ExtractorPlugin):
    def extract(self) -> int:
        from extractors.exchange_rates import extract

        return extract(pg_dsn=self.pg_dsn)

    def health_name(self) -> str:
        return "exchange_rates"

    @classmethod
    def config_fields(cls) -> list[ConfigField]:
        return []  # No config needed — reads from public ECB feed

    @classmethod
    def auth_methods(cls) -> list[dict[str, str]]:
        return [{"id": "none", "label": "No authentication", "sub": "ECB feeds are public"}]


def discover_plugins() -> None:
    """Import all discovery modules to trigger @extractor_plugin registration.

    Also scans for third-party modules in the EXTRACTOR_PLUGINS env var
    (comma-separated Python module paths).
    """
    for module_name in DISCOVERY_MODULES:
        try:
            importlib.import_module(module_name)
            logger.info(f"Discovered built-in extractor: {module_name}")
        except ImportError as e:
            logger.warning(f"Failed to import {module_name}: {e}")

    # Discover third-party plugins from env var
    extra_plugins = os.getenv("EXTRACTOR_PLUGINS", "")
    if extra_plugins:
        for module_name in extra_plugins.split(","):
            module_name = module_name.strip()
            if module_name:
                try:
                    importlib.import_module(module_name)
                    logger.info(f"Discovered third-party plugin: {module_name}")
                except ImportError as e:
                    logger.warning(f"Failed to import third-party plugin {module_name}: {e}")


# Auto-discover on import
discover_plugins()
