"""Entrypoint for FinOps extractor Docker container.

Reads the EXTRACTOR_TYPE environment variable and dispatches to the
corresponding extractor's main() function.

Supported values:
  gcp_billing    - GCP BigQuery billing extractor
  gcp_csv        - GCP CSV billing file extractor
  azure_cost     - Azure Cost Management extractor
  exchange_rates - ECB exchange rate extractor
"""

from __future__ import annotations

import os
import sys

EXTRACTOR_MAP = {
    "gcp_billing": "backend.extractors.gcp_billing",
    "gcp_csv": "backend.extractors.gcp_csv",
    "azure_cost": "backend.extractors.azure_cost",
    "exchange_rates": "backend.extractors.exchange_rates",
}


def main() -> None:
    extractor_type = os.getenv("EXTRACTOR_TYPE", "").strip()

    if not extractor_type:
        print(
            f"ERROR: EXTRACTOR_TYPE env var is required. Valid values: {', '.join(EXTRACTOR_MAP)}",
            file=sys.stderr,
        )
        sys.exit(1)

    if extractor_type not in EXTRACTOR_MAP:
        print(
            f"ERROR: Unknown EXTRACTOR_TYPE '{extractor_type}'. Valid values: {', '.join(EXTRACTOR_MAP)}",
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
