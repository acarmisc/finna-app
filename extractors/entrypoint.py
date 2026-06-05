"""Entrypoint for FinOps extractor Docker container.

Reads the EXTRACTOR_TYPE environment variable and dispatches to the
corresponding extractor's main() function.

Supported values:
  aws_cost               - AWS Cost Explorer extractor
  gcp_billing            - GCP BigQuery billing extractor
  gcp_csv                - GCP CSV billing file extractor
  azure_cost             - Azure Cost Management extractor
  litellm_cost           - LiteLLM proxy spend logs extractor
  exchange_rates         - ECB exchange rate extractor
  azure_inventory_scan   - Azure resource inventory + wastage scan (Phase 4/5)

For azure_inventory_scan the following env vars are used:
  AZURE_SUBSCRIPTION_ID  - Target Azure subscription (required)
  AZURE_TENANT_ID        - Service principal tenant (optional)
  AZURE_CLIENT_ID        - Service principal client ID (optional)
  AZURE_CLIENT_SECRET    - Service principal secret (optional)
  PG_DSN                 - PostgreSQL connection string (required)
  WASTAGE_MISS_THRESHOLD - Consecutive missed runs before auto-resolve (default 3)
"""

from __future__ import annotations

import os
import sys

EXTRACTOR_MAP = {
    "aws_cost": "extractors.aws_cost",
    "gcp_billing": "extractors.gcp_billing",
    "gcp_csv": "extractors.gcp_csv",
    "azure_cost": "extractors.azure_cost",
    "litellm_cost": "extractors.litellm_cost",
    "exchange_rates": "extractors.exchange_rates",
}

# Inventory scan modes delegate to the wastage runner directly
INVENTORY_SCAN_PROVIDERS = {"azure"}


def _run_inventory_scan(provider: str) -> None:
    """Run the inventory + wastage scan for the given cloud provider."""
    import psycopg

    if provider == "azure":
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID", "").strip()
        if not subscription_id:
            print(
                "ERROR: AZURE_SUBSCRIPTION_ID is required for azure_inventory_scan",
                file=sys.stderr,
            )
            sys.exit(1)

        pg_dsn = os.getenv("PG_DSN", "").strip()
        if not pg_dsn:
            print("ERROR: PG_DSN is required", file=sys.stderr)
            sys.exit(1)

        threshold = int(os.getenv("WASTAGE_MISS_THRESHOLD", "3"))

        from backend.app.wastage.runner import run_scan
        from extractors.inventory.azure_inventory import stream_inventory

        rows = stream_inventory(
            subscription_ids=[subscription_id],
            tenant_id=os.getenv("AZURE_TENANT_ID") or None,
            client_id=os.getenv("AZURE_CLIENT_ID") or None,
            client_secret=os.getenv("AZURE_CLIENT_SECRET") or None,
        )

        with psycopg.connect(pg_dsn) as conn:
            run_id = run_scan(
                conn=conn,
                provider="azure",
                inventory_rows=rows,
                consecutive_miss_threshold=threshold,
            )

        print(f"Wastage scan complete. Run ID: {run_id}")
    else:
        print(f"ERROR: unsupported provider {provider!r}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    extractor_type = os.getenv("EXTRACTOR_TYPE", "").strip()

    if not extractor_type:
        all_types = list(EXTRACTOR_MAP) + ["azure_inventory_scan"]
        print(
            "ERROR: EXTRACTOR_TYPE env var is required. "
            f"Valid values: {', '.join(all_types)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Inventory scan mode: EXTRACTOR_TYPE=azure_inventory_scan
    if extractor_type == "azure_inventory_scan":
        _run_inventory_scan("azure")
        return

    if extractor_type not in EXTRACTOR_MAP:
        all_types = list(EXTRACTOR_MAP) + ["azure_inventory_scan"]
        print(
            f"ERROR: Unknown EXTRACTOR_TYPE '{extractor_type}'. "
            f"Valid values: {', '.join(all_types)}",
            file=sys.stderr,
        )
        sys.exit(1)

    module_name = EXTRACTOR_MAP[extractor_type]

    # Import the target module and call its main()
    try:
        import importlib

        module = importlib.import_module(module_name)
    except ImportError as exc:
        print(f"ERROR: Failed to import {module_name}: {exc}", file=sys.stderr)
        sys.exit(1)

    if not hasattr(module, "main"):
        print(f"ERROR: {module_name} has no main() function", file=sys.stderr)
        sys.exit(1)

    module.main()


if __name__ == "__main__":
    main()
