#!/usr/bin/env python3
"""Idempotent client onboarding script for FinOps multi-cloud monitoring.

Creates client directory, generates extractor/aggregation configs,
a connectivity test script, and registers the client in the shared registry.

Usage:
    python -m onboarding.setup_client <client_id> [--providers gcp azure] [--projects proj1 proj2]
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

logger = logging.getLogger("onboarding.setup_client")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
CLIENTS_DIR = BASE_DIR / "clients"
REGISTRY_PATH = CLIENTS_DIR / "registry.yaml"

DEFAULT_PROVIDERS = ["gcp", "azure"]
SUPPORTED_PROVIDERS = {"gcp", "azure"}

# Default aggregation settings (mirrors aggregation/config.py defaults)
DEFAULT_AGGREGATION = {
    "infra_metrics": {
        "window_size_minutes": 15,
        "retention_days": 365,
    },
    "llm_requests": {
        "window_size_minutes": 5,
        "retention_days": 180,
    },
    "billing": {
        "window_size_minutes": 60,
        "retention_days": 730,
    },
}

# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict:
    """Load a YAML file, returning an empty dict if it does not exist."""
    if not path.exists():
        return {}
    with path.open() as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _write_yaml(path: Path, data: dict) -> None:
    """Write data to a YAML file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    logger.info("Wrote %s", path)


# ---------------------------------------------------------------------------
# Config generators
# ---------------------------------------------------------------------------


def _generate_extractor_config(
    client_id: str,
    providers: list[str],
    projects: list[str],
) -> dict:
    """Build the extractor env-var config for a client.

    Each provider section contains the environment variables that the
    corresponding extractor reads at runtime.
    """
    config: dict = {"client_id": client_id}

    if "gcp" in providers:
        config["gcp_billing"] = {
            "GCP_PROJECT": projects[0] if projects else f"{client_id}-gcp-project",
            "BQ_DATASET": "billing_export",
            "BQ_TABLE": "gcp_billing_export_v1",
            "PG_DSN": "${PG_DSN}",
            "EXTRACTOR_TYPE": "gcp_billing",
        }

    if "azure" in providers:
        config["azure_cost"] = {
            "AZURE_SUBSCRIPTION_ID": f"{client_id}-subscription-id",
            "AZURE_TENANT_ID": f"{client_id}-tenant-id",
            "AZURE_CLIENT_ID": f"{client_id}-client-id",
            "AZURE_CLIENT_SECRET": "${AZURE_CLIENT_SECRET}",
            "PG_DSN": "${PG_DSN}",
            "EXTRACTOR_TYPE": "azure_cost",
        }

    return config


def _generate_aggregation_config(client_id: str) -> dict:
    """Build per-client aggregation config inheriting system defaults."""
    return {
        "client_id": client_id,
        "client_name": client_id.replace("-", " ").title(),
        "aggregation": DEFAULT_AGGREGATION,
    }


def _generate_connectivity_test(client_id: str) -> str:
    """Generate a standalone connectivity test script for the client."""
    return f'''#!/usr/bin/env python3
"""Connectivity test for client: {client_id}.

Verifies PG_DSN connectivity and runs a basic query against the
FinOps cost_records table.
"""

from __future__ import annotations

import os
import sys


def test_connectivity() -> None:
    dsn = os.getenv("PG_DSN", "")
    if not dsn:
        print("ERROR: PG_DSN environment variable is not set", file=sys.stderr)
        sys.exit(1)

    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg is not installed. Run: pip install psycopg[binary]", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to PostgreSQL...")
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                print(f"  PostgreSQL version: {{version}}")

                cur.execute(
                    "SELECT count(*) FROM cost_records WHERE project_id LIKE %s",
                    ("{client_id}%",),
                )
                count = cur.fetchone()[0]
                print(f"  cost_records for {client_id}: {{count}} rows")

                cur.execute(
                    "SELECT extractor_name, status, updated_at FROM extractor_health ORDER BY updated_at DESC LIMIT 5"
                )
                rows = cur.fetchall()
                if rows:
                    print("  Recent extractor health:")
                    for row in rows:
                        print(f"    {{row[0]}}: {{row[1]}} (updated {{row[2]}})")
                else:
                    print("  No extractor health records found")

        print("Connectivity test PASSED")
    except psycopg.OperationalError as exc:
        print(f"ERROR: Could not connect to PostgreSQL: {{exc}}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Unexpected error: {{exc}}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    test_connectivity()
'''


# ---------------------------------------------------------------------------
# Registry management
# ---------------------------------------------------------------------------


def _register_client(
    client_id: str,
    providers: list[str],
    projects: list[str],
) -> None:
    """Add or update a client entry in the shared registry YAML.

    The registry is idempotent: re-running with the same client_id updates
    the existing entry without error.
    """
    registry = _load_yaml(REGISTRY_PATH)
    clients = registry.get("clients", {})

    clients[client_id] = {
        "providers": providers,
        "projects": projects,
        "onboarded_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    registry["clients"] = clients
    _write_yaml(REGISTRY_PATH, registry)


# ---------------------------------------------------------------------------
# Main onboarding logic
# ---------------------------------------------------------------------------


def onboard(
    client_id: str,
    providers: list[str],
    projects: list[str],
) -> None:
    """Run the full idempotent onboarding for a client."""
    client_dir = CLIENTS_DIR / client_id
    client_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Client directory: %s", client_dir)

    effective_providers = list(providers)

    # 1. Extractor config
    extractor_config = _generate_extractor_config(
        client_id, effective_providers, projects
    )
    _write_yaml(client_dir / "extractor_config.yaml", extractor_config)

    # 2. Aggregation config
    agg_config = _generate_aggregation_config(client_id)
    _write_yaml(client_dir / "aggregation_config.yaml", agg_config)

    # 3. Connectivity test script
    test_script = client_dir / "test_connectivity.py"
    test_script.write_text(_generate_connectivity_test(client_id))
    test_script.chmod(0o755)
    logger.info("Wrote %s", test_script)

    # 4. Registry
    _register_client(client_id, effective_providers, projects)

    logger.info("Onboarding complete for client: %s", client_id)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Idempotent client onboarding for FinOps multi-cloud monitoring.",
    )
    parser.add_argument(
        "client_id",
        help="Unique identifier for the new client (lowercase, hyphens allowed).",
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        default=DEFAULT_PROVIDERS,
        choices=sorted(SUPPORTED_PROVIDERS),
        help=f"Cloud providers to enable (default: {' '.join(DEFAULT_PROVIDERS)}).",
    )
    parser.add_argument(
        "--projects",
        nargs="+",
        default=[],
        help="Cloud project IDs associated with this client.",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        stream=sys.stdout,
    )

    parser = _build_parser()
    args = parser.parse_args()

    client_id: str = args.client_id.lower().strip()
    if not client_id:
        parser.error("client_id must not be empty")

    # Validate client_id format: lowercase alphanumeric + hyphens
    if not all(c.isalnum() or c == "-" for c in client_id):
        parser.error(
            "client_id must contain only lowercase letters, digits, and hyphens"
        )

    onboard(
        client_id=client_id,
        providers=args.providers,
        projects=args.projects,
    )


if __name__ == "__main__":
    main()
