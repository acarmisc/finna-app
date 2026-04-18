"""FinOps Configuration Wizard — interactive TUI for creating client configurations.

Usage:
    python -m config.wizard
    python config/wizard.py
"""

from __future__ import annotations

import secrets
import string
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import questionary
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from config.schema import (
    AggregationConfig,
    AggregationSettings,
    AzureConfig,
    ClientConfig,
    GCPConfig,
    GCPIngestionMode,
    PostgreSQLConfig,
    SupersetConfig,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLIENTS_DIR = PROJECT_ROOT / "clients"
REGISTRY_PATH = CLIENTS_DIR / "registry.yaml"

ENV_CHOICES_SSL = ["disable", "prefer", "require"]
ENV_CHOICES_ENV = ["prod", "staging", "dev"]
SCOPE_CHOICES = ["subscription", "managementgroup"]

console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_secret_key(length: int = 32) -> str:
    """Generate a random secret key suitable for Flask / Superset."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _validate_client_id(value: str) -> str | bool:
    """client_id must be lowercase alphanumeric with hyphens."""
    if not value:
        return "Client ID is required"
    if not all(c.isalnum() or c == "-" for c in value):
        return "Only lowercase alphanumeric characters and hyphens are allowed"
    if value != value.lower():
        return "Must be lowercase"
    return True


def _validate_required(value: str) -> str | bool:
    """Generic non-empty validator."""
    if not value or not value.strip():
        return "This field is required"
    return True


def _validate_port(value: str) -> str | bool:
    """Port must be a valid integer 1-65535."""
    if not value:
        return "Port is required"
    try:
        p = int(value)
        if not (1 <= p <= 65535):
            return "Port must be between 1 and 65535"
    except ValueError:
        return "Port must be a number"
    return True


def _validate_positive_int(value: str) -> str | bool:
    """Must be a positive integer."""
    if not value:
        return "This field is required"
    try:
        v = int(value)
        if v <= 0:
            return "Must be a positive integer"
    except ValueError:
        return "Must be a number"
    return True


# ---------------------------------------------------------------------------
# Section prompts
# ---------------------------------------------------------------------------


def welcome_screen() -> None:
    """Display the welcome banner."""
    banner = Text()
    banner.append("FinOps Configuration Wizard\n\n", style="bold cyan")
    banner.append(
        "This wizard will guide you through creating a complete\n"
        "FinOps multi-cloud monitoring configuration.\n\n"
        "Press Ctrl+C at any time to exit.",
        style="dim",
    )
    console.print(Panel(banner, border_style="bright_blue", padding=(1, 2)))


def ask_client_identification() -> dict[str, str]:
    """Ask for client_id and client_name."""
    console.rule("[bold green]Client Identification[/bold green]")

    client_id = questionary.text(
        "Client ID (lowercase, hyphens, alphanumeric):",
        validate=_validate_client_id,
    ).ask()

    if client_id is None:
        raise KeyboardInterrupt

    client_name = questionary.text(
        "Client name (human-readable):",
        validate=_validate_required,
    ).ask()

    if client_name is None:
        raise KeyboardInterrupt

    return {"client_id": client_id.strip(), "client_name": client_name.strip()}


def ask_postgresql() -> dict[str, Any]:
    """Ask for PostgreSQL connection settings."""
    console.rule("[bold green]PostgreSQL Configuration[/bold green]")

    host = questionary.text("Host:", default="localhost").ask()
    port_str = questionary.text("Port:", default="5432", validate=_validate_port).ask()
    database = questionary.text("Database:", default="finops").ask()
    user = questionary.text("User:", default="finops").ask()
    password = questionary.password("Password:").ask()
    ssl_mode = questionary.select(
        "SSL mode:",
        choices=ENV_CHOICES_SSL,
        default="prefer",
    ).ask()

    if any(v is None for v in [host, port_str, database, user, password, ssl_mode]):
        raise KeyboardInterrupt

    port = int(port_str)
    pw = password or ""

    # Show constructed DSN
    dsn = f"postgresql://{user}:{'***' if pw else ''}@{host}:{port}/{database}?sslmode={ssl_mode}"
    console.print(f"  Constructed DSN: [cyan]{dsn}[/cyan]")

    confirm = questionary.confirm("Does this look correct?", default=True).ask()
    if confirm is None:
        raise KeyboardInterrupt
    if not confirm:
        console.print("[yellow]Re-entering PostgreSQL configuration...[/yellow]")
        return ask_postgresql()

    return {
        "host": host,
        "port": port,
        "database": database,
        "user": user,
        "password": pw,
        "ssl_mode": ssl_mode,
    }


def ask_superset() -> dict[str, Any]:
    """Ask for Apache Superset settings."""
    console.rule("[bold green]Superset Configuration[/bold green]")

    host = questionary.text("Superset host:", default="localhost").ask()
    port_str = questionary.text(
        "Superset port:", default="8088", validate=_validate_port
    ).ask()
    admin_username = questionary.text("Admin username:", default="admin").ask()
    admin_password = questionary.password("Admin password:", default=None).ask()
    admin_email = questionary.text(
        "Admin email:",
        default="admin@finops.local",
    ).ask()

    suggested_key = _generate_secret_key()
    use_generated = questionary.confirm(
        f"Use a generated secret key? (suggested: {suggested_key[:8]}...)",
        default=True,
    ).ask()

    if use_generated is None:
        raise KeyboardInterrupt

    if use_generated:
        secret_key = suggested_key
    else:
        secret_key = questionary.text(
            "Secret key:",
            default="CHANGE_ME_TO_A_LONG_RANDOM_STRING",
        ).ask()

    if any(v is None for v in [host, port_str, admin_username, admin_email]):
        raise KeyboardInterrupt

    port = int(port_str)

    return {
        "enabled": True,
        "host": host,
        "port": port,
        "admin_username": admin_username,
        "admin_password": admin_password or "admin",
        "admin_email": admin_email,
        "secret_key": secret_key,
    }


def ask_providers() -> list[str]:
    """Ask which cloud providers to enable."""
    console.rule("[bold green]Cloud Providers[/bold green]")

    providers = questionary.checkbox(
        "Select providers to enable:",
        choices=["gcp", "azure"],
    ).ask()

    if providers is None:
        raise KeyboardInterrupt

    return providers


# ---------------------------------------------------------------------------
# GCP section
# ---------------------------------------------------------------------------


def ask_gcp_project(ingestion_mode: str = "bigquery") -> dict[str, Any]:
    """Ask for a single GCP project configuration.

    The prompts for BigQuery dataset/table are shown only when
    ingestion_mode is 'bigquery'. A CSV path prompt is shown only
    when ingestion_mode is 'csv'.
    """
    project_id = questionary.text(
        "Project ID (required):",
        validate=_validate_required,
    ).ask()
    project_name = questionary.text("Project name:").ask()

    result: dict[str, Any] = {
        "project_id": project_id.strip(),
        "project_name": project_name.strip() if project_name else None,
        "ingestion_mode": ingestion_mode,
    }

    if ingestion_mode == "bigquery":
        bigquery_dataset = questionary.text(
            "BigQuery dataset:",
            default="billing_export",
        ).ask()
        bigquery_table = questionary.text(
            "BigQuery table:",
            default="gcp_billing_export_v1",
        ).ask()
        result["bigquery_dataset"] = bigquery_dataset or "billing_export"
        result["bigquery_table"] = bigquery_table or "gcp_billing_export_v1"

    if ingestion_mode == "csv":
        csv_path = questionary.text(
            "Path to CSV billing export file:",
            validate=_validate_required,
        ).ask()
        result["csv_path"] = csv_path.strip() if csv_path else None

    environment = questionary.select(
        "Environment:",
        choices=ENV_CHOICES_ENV,
    ).ask()
    team = questionary.text("Team:").ask()

    result["environment"] = environment
    result["team"] = team.strip() if team else None

    if project_id is None:
        raise KeyboardInterrupt

    return result


def ask_gcp() -> dict[str, Any]:
    """Ask for full GCP configuration including projects and authentication."""
    console.rule("[bold green]GCP Configuration[/bold green]")

    from config.auth import gcp_auth_interactive

    auth_result = gcp_auth_interactive()
    auth_method = auth_result.get("auth_method", "skipped")

    if auth_method == "skipped":
        return {"enabled": False}

    billing_account_id = questionary.text("Billing account ID (optional):").ask()

    service_account_key_path = None
    if auth_method == "service_account":
        service_account_key_path = questionary.text(
            "Service account key path:",
        ).ask()

    ingestion_mode = questionary.select(
        "Ingestion mode:",
        choices=["bigquery", "csv"],
        default="bigquery",
    ).ask()

    if ingestion_mode is None or billing_account_id is None:
        raise KeyboardInterrupt

    mode_desc = "BigQuery export" if ingestion_mode == "bigquery" else "CSV file import"
    console.print(f"  Using ingestion mode: [cyan]{mode_desc}[/cyan]")

    projects: list[dict[str, Any]] = []
    while True:
        console.print("\n[bold]Add GCP Project[/bold]")
        project = ask_gcp_project(ingestion_mode=ingestion_mode)
        projects.append(project)

        add_another = questionary.confirm(
            "Add another project?",
            default=False,
        ).ask()
        if add_another is None or not add_another:
            break

    # Show project summary
    if projects:
        table = Table(title="GCP Projects", show_lines=True)
        table.add_column("Project ID", style="cyan")
        table.add_column("Name")
        table.add_column("Mode", style="magenta")
        if ingestion_mode == "bigquery":
            table.add_column("Dataset")
            table.add_column("Table")
        else:
            table.add_column("CSV Path")
        table.add_column("Environment")
        table.add_column("Team")
        for p in projects:
            row_data = [
                p["project_id"],
                p.get("project_name") or "-",
                p.get("ingestion_mode", "bigquery"),
            ]
            if ingestion_mode == "bigquery":
                row_data.extend(
                    [
                        p.get("bigquery_dataset", "-"),
                        p.get("bigquery_table", "-"),
                    ]
                )
            else:
                row_data.append(p.get("csv_path", "-"))
            row_data.extend(
                [
                    p.get("environment") or "-",
                    p.get("team") or "-",
                ]
            )
            table.add_row(*row_data)
        console.print(table)

    return {
        "enabled": True,
        "auth_method": auth_method,
        "billing_account_id": billing_account_id.strip()
        if billing_account_id
        else None,
        "service_account_key_path": service_account_key_path.strip()
        if service_account_key_path
        else None,
        "projects": projects,
    }


# ---------------------------------------------------------------------------
# Azure section
# ---------------------------------------------------------------------------


def ask_azure_subscription(tenant_id_hint: str | None = None) -> dict[str, Any]:
    """Ask for a single Azure subscription configuration."""
    subscription_id = questionary.text(
        "Subscription ID (required):",
        validate=_validate_required,
    ).ask()
    subscription_name = questionary.text("Subscription name:").ask()

    tenant_id = questionary.text(
        "Tenant ID (required):",
        default=tenant_id_hint or "",
        validate=_validate_required,
    ).ask()

    auth_method = questionary.select(
        "Authentication method for this subscription:",
        choices=[
            "OAuth device code (browser login — recommended)",
            "Service principal (client secret)",
        ],
    ).ask()

    client_id = ""
    client_secret = ""
    if auth_method and "Service principal" in auth_method:
        client_id = (
            questionary.text(
                "Client ID / App ID (required):",
                validate=_validate_required,
            ).ask()
            or ""
        )
        client_secret = (
            questionary.password(
                "Client secret (required):",
            ).ask()
            or ""
        )
    elif auth_method and "OAuth" in auth_method:
        from config.auth import azure_device_flow

        console.print(
            f"\n[bold]Authenticating via OAuth for subscription {subscription_id.strip()}[/bold]"
        )
        try:
            meta = azure_device_flow(tenant_id=tenant_id.strip())
            client_id = meta.get("client_id", "")
            console.print(
                "[dim]OAuth token cached — extractors will use it automatically.[/dim]"
            )
        except Exception as exc:
            console.print(f"[red]OAuth failed: {exc}[/red]")
            console.print("[yellow]Falling back to service principal.[/yellow]")
            client_id = questionary.text("Client ID / App ID:").ask() or ""
            client_secret = questionary.password("Client secret:").ask() or ""
            auth_method = "Service principal (client secret)"

    scope = questionary.select(
        "Scope:",
        choices=SCOPE_CHOICES,
        default="subscription",
    ).ask()

    management_group_id: Optional[str] = None
    if scope == "managementgroup":
        management_group_id = questionary.text(
            "Management group ID (required for management group scope):",
            validate=_validate_required,
        ).ask()

    # Resource groups loop
    resource_groups: list[str] = []
    while True:
        add_rg = questionary.confirm(
            "Add a resource group?",
            default=False,
        ).ask()
        if add_rg is None or not add_rg:
            break
        rg_name = questionary.text("Resource group name:").ask()
        if rg_name and rg_name.strip():
            resource_groups.append(rg_name.strip())

    environment = questionary.select(
        "Environment:",
        choices=ENV_CHOICES_ENV,
    ).ask()
    team = questionary.text("Team:").ask()

    if subscription_id is None:
        raise KeyboardInterrupt

    result: dict[str, Any] = {
        "subscription_id": subscription_id.strip(),
        "subscription_name": subscription_name.strip() if subscription_name else None,
        "tenant_id": tenant_id.strip(),
        "client_id": client_id.strip() if client_id else "",
        "client_secret": client_secret or "",
        "auth_method": "device_code"
        if auth_method and "OAuth" in auth_method
        else "client_secret",
        "resource_groups": resource_groups,
        "environment": environment,
        "team": team.strip() if team else None,
        "scope": scope,
        "management_group_id": management_group_id.strip()
        if management_group_id
        else None,
    }
    return result


def ask_azure() -> dict[str, Any]:
    """Ask for full Azure configuration including subscriptions."""
    console.rule("[bold green]Azure Configuration[/bold green]")

    subscriptions: list[dict[str, Any]] = []
    while True:
        console.print("\n[bold]Add Azure Subscription[/bold]")
        sub = ask_azure_subscription()
        subscriptions.append(sub)

        add_another = questionary.confirm(
            "Add another subscription?",
            default=False,
        ).ask()
        if add_another is None or not add_another:
            break

    # Show subscription summary
    if subscriptions:
        table = Table(title="Azure Subscriptions", show_lines=True)
        table.add_column("Subscription ID", style="cyan")
        table.add_column("Name")
        table.add_column("Tenant ID")
        table.add_column("Scope")
        table.add_column("Resource Groups")
        table.add_column("Environment")
        table.add_column("Team")
        for s in subscriptions:
            rg_list = (
                ", ".join(s["resource_groups"]) if s["resource_groups"] else "(all)"
            )
            table.add_row(
                s["subscription_id"][:12] + "...",
                s.get("subscription_name") or "-",
                s["tenant_id"][:12] + "...",
                s["scope"],
                rg_list,
                s.get("environment") or "-",
                s.get("team") or "-",
            )
        console.print(table)

    return {
        "enabled": True,
        "subscriptions": subscriptions,
    }


# ---------------------------------------------------------------------------
# Aggregation section
# ---------------------------------------------------------------------------


def ask_aggregation() -> dict[str, Any]:
    """Ask for aggregation settings."""
    console.rule("[bold green]Aggregation Settings[/bold green]")

    use_defaults = questionary.confirm(
        "Use default aggregation settings?",
        default=True,
    ).ask()

    if use_defaults is None:
        raise KeyboardInterrupt

    if use_defaults:
        return {
            "infra_metrics": {"window_size_minutes": 15, "retention_days": 365},
            "llm_requests": {"window_size_minutes": 5, "retention_days": 180},
            "billing": {"window_size_minutes": 60, "retention_days": 730},
        }

    console.print("[dim]Customize each metric type:[/dim]\n")

    def _ask_metric(
        name: str, default_window: int, default_retention: int
    ) -> dict[str, int]:
        console.print(f"[bold]{name}[/bold]")
        ws = questionary.text(
            "  Window size (minutes):",
            default=str(default_window),
            validate=_validate_positive_int,
        ).ask()
        rd = questionary.text(
            "  Retention (days):",
            default=str(default_retention),
            validate=_validate_positive_int,
        ).ask()
        if ws is None or rd is None:
            raise KeyboardInterrupt
        return {"window_size_minutes": int(ws), "retention_days": int(rd)}

    infra = _ask_metric("Infrastructure Metrics", 15, 365)
    llm = _ask_metric("LLM Requests", 5, 180)
    billing = _ask_metric("Billing", 60, 730)

    return {
        "infra_metrics": infra,
        "llm_requests": llm,
        "billing": billing,
    }


# ---------------------------------------------------------------------------
# Review & save
# ---------------------------------------------------------------------------


def build_config(
    client_info: dict[str, str],
    pg: dict[str, Any],
    superset: dict[str, Any],
    providers: list[str],
    gcp: Optional[dict[str, Any]],
    azure: Optional[dict[str, Any]],
    aggregation: dict[str, Any],
) -> ClientConfig:
    """Build and validate the ClientConfig Pydantic model from wizard answers."""

    gcp_model = GCPConfig(**gcp) if gcp else None
    azure_model = AzureConfig(**azure) if azure else None

    # Build aggregation sub-models
    agg = AggregationConfig(
        infra_metrics=AggregationSettings(**aggregation["infra_metrics"]),
        llm_requests=AggregationSettings(**aggregation["llm_requests"]),
        billing=AggregationSettings(**aggregation["billing"]),
    )

    config = ClientConfig(
        client_id=client_info["client_id"],
        client_name=client_info["client_name"],
        postgresql=PostgreSQLConfig(**pg),
        superset=SupersetConfig(**superset),
        gcp=gcp_model,
        azure=azure_model,
        aggregation=agg,
    )

    return config


def display_summary(config: ClientConfig) -> None:
    """Display the full configuration summary using rich panels and tables."""
    console.rule("[bold green]Configuration Summary[/bold green]")

    # -- General --
    general_table = Table.grid(padding=(0, 2))
    general_table.add_row("Client ID", f"[cyan]{config.client_id}[/cyan]")
    general_table.add_row("Client Name", config.client_name)
    general_table.add_row("Created At", str(config.created_at))
    console.print(Panel(general_table, title="General", border_style="green"))

    # -- PostgreSQL --
    pg_table = Table.grid(padding=(0, 2))
    pg_table.add_row("Host", config.postgresql.host)
    pg_table.add_row("Port", str(config.postgresql.port))
    pg_table.add_row("Database", config.postgresql.database)
    pg_table.add_row("User", config.postgresql.user)
    pg_table.add_row("Password", "***")
    pg_table.add_row("SSL Mode", config.postgresql.ssl_mode)
    console.print(Panel(pg_table, title="PostgreSQL", border_style="green"))

    # -- Superset --
    ss_table = Table.grid(padding=(0, 2))
    ss_table.add_row("Host", config.superset.host)
    ss_table.add_row("Port", str(config.superset.port))
    ss_table.add_row("Admin Username", config.superset.admin_username)
    ss_table.add_row("Admin Password", "***")
    ss_table.add_row("Admin Email", config.superset.admin_email)
    ss_table.add_row("Secret Key", "***")
    console.print(Panel(ss_table, title="Superset", border_style="green"))

    # -- GCP --
    if config.gcp and config.gcp.enabled:
        gcp_table = Table.grid(padding=(0, 2))
        gcp_table.add_row("Billing Account", config.gcp.billing_account_id or "-")
        gcp_table.add_row("SA Key Path", config.gcp.service_account_key_path or "-")
        console.print(Panel(gcp_table, title="GCP", border_style="green"))

        proj_table = Table(show_lines=True)
        proj_table.add_column("Project ID", style="cyan")
        proj_table.add_column("Name")
        proj_table.add_column("Mode", style="magenta")
        has_csv_mode = any(
            p.ingestion_mode == GCPIngestionMode.csv for p in config.gcp.projects
        )
        has_bq_mode = any(
            p.ingestion_mode == GCPIngestionMode.bigquery for p in config.gcp.projects
        )
        if has_bq_mode:
            proj_table.add_column("Dataset")
            proj_table.add_column("Table")
        if has_csv_mode:
            proj_table.add_column("CSV Path")
        proj_table.add_column("Env")
        proj_table.add_column("Team")
        for p in config.gcp.projects:
            row_data = [
                p.project_id,
                p.project_name or "-",
                p.ingestion_mode.value,
            ]
            if has_bq_mode:
                if p.ingestion_mode == GCPIngestionMode.bigquery:
                    row_data.extend(
                        [p.bigquery_dataset or "-", p.bigquery_table or "-"]
                    )
                else:
                    row_data.extend(["-", "-"])
            if has_csv_mode:
                row_data.append(
                    p.csv_path or "-"
                    if p.ingestion_mode == GCPIngestionMode.csv
                    else "-"
                )
            row_data.extend(
                [
                    p.environment or "-",
                    p.team or "-",
                ]
            )
            proj_table.add_row(*row_data)
        console.print(proj_table)

    # -- Azure --
    if config.azure and config.azure.enabled:
        az_table = Table.grid(padding=(0, 2))
        console.print(Panel(az_table, title="Azure", border_style="green"))

        sub_table = Table(show_lines=True)
        sub_table.add_column("Subscription ID", style="cyan")
        sub_table.add_column("Name")
        sub_table.add_column("Tenant")
        sub_table.add_column("Scope")
        sub_table.add_column("Resource Groups")
        sub_table.add_column("Env")
        sub_table.add_column("Team")
        for s in config.azure.subscriptions:
            rg = ", ".join(s.resource_groups) if s.resource_groups else "(all)"
            sub_table.add_row(
                s.subscription_id,
                s.subscription_name or "-",
                s.tenant_id,
                s.scope,
                rg,
                s.environment or "-",
                s.team or "-",
            )
        console.print(sub_table)

    # -- Aggregation --
    agg_table = Table(show_lines=True)
    agg_table.add_column("Metric Type", style="cyan")
    agg_table.add_column("Window (min)")
    agg_table.add_column("Retention (days)")
    agg_table.add_row(
        "Infrastructure",
        str(config.aggregation.infra_metrics.window_size_minutes),
        str(config.aggregation.infra_metrics.retention_days),
    )
    agg_table.add_row(
        "LLM Requests",
        str(config.aggregation.llm_requests.window_size_minutes),
        str(config.aggregation.llm_requests.retention_days),
    )
    agg_table.add_row(
        "Billing",
        str(config.aggregation.billing.window_size_minutes),
        str(config.aggregation.billing.retention_days),
    )
    console.print(Panel(agg_table, title="Aggregation", border_style="green"))


def save_config(config: ClientConfig) -> None:
    """Save the validated configuration to disk.

    Creates:
      - clients/{client_id}/config.yaml  — full config (secrets masked in comments)
      - clients/{client_id}/.env         — secrets for dotenv loading
      - clients/registry.yaml            — appends client registration
    """
    client_dir = CLIENTS_DIR / config.client_id
    client_dir.mkdir(parents=True, exist_ok=True)

    # --- config.yaml ---
    config_yaml_path = client_dir / "config.yaml"
    config_dict = config.model_dump(mode="json")

    # Mask secrets in the YAML for safety — real secrets go in .env
    safe_dict = _mask_secrets(config_dict)

    with open(config_yaml_path, "w") as fh:
        yaml.dump(safe_dict, fh, default_flow_style=False, sort_keys=False)

    # --- .env ---
    env_path = client_dir / ".env"
    env_dict = config.to_env_dict()
    with open(env_path, "w") as fh:
        fh.write("# FinOps environment variables — DO NOT commit to version control\n")
        fh.write(f"# Generated {datetime.now().isoformat()}\n\n")
        for key, value in sorted(env_dict.items()):
            fh.write(f"{key}={value}\n")

    # --- registry.yaml ---
    _update_registry(config)


def _mask_secrets(d: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the dict with sensitive fields replaced by placeholders."""
    import copy

    d = copy.deepcopy(d)

    # PostgreSQL password
    if "postgresql" in d and "password" in d["postgresql"]:
        d["postgresql"]["password"] = "${PG_PASSWORD}"

    # Superset secrets
    if "superset" in d:
        d["superset"]["admin_password"] = "${SUPERSET_ADMIN_PASSWORD}"
        d["superset"]["secret_key"] = "${SUPERSET_SECRET_KEY}"

    # Azure client secrets
    if "azure" in d and "subscriptions" in d.get("azure", {}):
        for sub in d["azure"]["subscriptions"]:
            if "client_secret" in sub:
                sub["client_secret"] = "${AZURE_CLIENT_SECRET}"

    return d


def _update_registry(config: ClientConfig) -> None:
    """Append the client to the registry.yaml file."""
    CLIENTS_DIR.mkdir(parents=True, exist_ok=True)

    registry: list[dict[str, str]] = []
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH) as fh:
            data = yaml.safe_load(fh)
            if isinstance(data, list):
                registry = data
            elif isinstance(data, dict) and "clients" in data:
                registry = data["clients"]

    # Check for duplicate
    for entry in registry:
        if entry.get("client_id") == config.client_id:
            console.print(
                f"[yellow]Warning: client '{config.client_id}' already in registry — updating entry.[/yellow]"
            )
            entry["client_name"] = config.client_name
            entry["updated_at"] = datetime.now().isoformat()
            break
    else:
        registry.append(
            {
                "client_id": config.client_id,
                "client_name": config.client_name,
                "created_at": config.created_at.isoformat(),
            }
        )

    with open(REGISTRY_PATH, "w") as fh:
        yaml.dump({"clients": registry}, fh, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# Main wizard flow
# ---------------------------------------------------------------------------


def run_wizard() -> None:
    """Execute the full configuration wizard."""
    try:
        welcome_screen()

        # 1. Client identification
        client_info = ask_client_identification()

        # 2. PostgreSQL
        pg = ask_postgresql()

        # 3. Superset
        superset = ask_superset()

        # 4. Provider selection
        providers = ask_providers()

        # 5. Provider-specific sections
        gcp: Optional[dict[str, Any]] = None
        azure: Optional[dict[str, Any]] = None

        if "gcp" in providers:
            gcp = ask_gcp()
        if "azure" in providers:
            azure = ask_azure()

        # 6. Aggregation
        aggregation = ask_aggregation()

        # 7. Build and validate
        console.rule("[bold green]Validation[/bold green]")
        try:
            config = build_config(
                client_info, pg, superset, providers, gcp, azure, aggregation
            )
            console.print("[bold green]Configuration is valid![/bold green]")
        except Exception as exc:
            console.print(f"[bold red]Validation error:[/bold red] {exc}")
            console.print("[yellow]Please review your inputs and try again.[/yellow]")
            sys.exit(1)

        # 8. Review
        display_summary(config)

        # 9. Confirm and save
        save = questionary.confirm(
            "Save this configuration?",
            default=True,
        ).ask()

        if save is None:
            raise KeyboardInterrupt

        if save:
            save_config(config)
            client_dir = CLIENTS_DIR / config.client_id
            success = Text()
            success.append(
                "\nConfiguration saved successfully!\n\n", style="bold green"
            )
            success.append(f"  Config:  {client_dir / 'config.yaml'}\n", style="cyan")
            success.append(f"  Secrets: {client_dir / '.env'}\n", style="cyan")
            success.append(f"  Registry: {REGISTRY_PATH}\n", style="cyan")
            success.append("\nAdd the .env file to your .gitignore!", style="yellow")
            console.print(Panel(success, border_style="green", padding=(1, 2)))
        else:
            console.print("[yellow]Configuration not saved.[/yellow]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Wizard cancelled by user.[/yellow]")
        sys.exit(0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_wizard()
