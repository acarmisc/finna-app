"""OAuth device-code authentication for cloud providers.

Provides TUI-integrated OAuth flows for Azure and GCP, with secure
credential persistence via OS keyring. Extractors can retrieve saved
credentials at runtime without re-prompting.

Usage:
    python -m config.auth azure
    python -m config.auth gcp
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import keyring
from rich.console import Console
from rich.panel import Panel

logger = logging.getLogger("config.auth")

console = Console()

KEYRING_SERVICE = "finna-app"
KEYRING_AZURE_TOKEN_KEY = "azure-token-cache"
KEYRING_GCP_ADC_STATUS = "gcp-adc-status"

AZURE_FINNA_PUBLIC_CLIENT_ID = "04b07795-a71b-4e6a-8f4e-d9e78e1a5c0e"
AZURE_DEFAULT_SCOPE = "https://management.azure.com/.default"


def _is_headless() -> bool:
    return not sys.stdout.isatty()


def _keyring_available() -> bool:
    try:
        keyring.get_keyring()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Azure OAuth
# ---------------------------------------------------------------------------


def azure_device_flow(
    tenant_id: str = "organizations",
    client_id: str = AZURE_FINNA_PUBLIC_CLIENT_ID,
    scope: str = AZURE_DEFAULT_SCOPE,
) -> dict[str, Any]:
    """Run Azure device-code OAuth flow and return credential metadata.

    Stores the token cache in the OS keyring for later retrieval by extractors.

    Returns:
        dict with keys: tenant_id, client_id, auth_method="device_code"
    """
    from azure.identity import DeviceCodeCredential
    from msal_extensions import PersistedTokenCache, build_encrypted_persistence

    persistence = build_encrypted_persistence("finna-app-azure-cache")
    token_cache = PersistedTokenCache(persistence)

    def _prompt(verification_uri: str, user_code: str, expires_on: Any) -> None:
        console.print(
            Panel(
                f"[bold]Azure Authentication Required[/bold]\n\n"
                f"1. Open: [cyan link={verification_uri}]{verification_uri}[/cyan]\n"
                f"2. Enter code: [bold yellow]{user_code}[/bold]\n\n"
                f"Code expires at {expires_on}",
                title="Device Login",
                border_style="blue",
            )
        )

    credential = DeviceCodeCredential(
        client_id=client_id,
        tenant_id=tenant_id,
        prompt_callback=_prompt,
        cache=token_cache,
        disable_automatic_authentication=False,
    )

    token = credential.get_token(scope)
    if token is None:
        raise RuntimeError("Azure device-code flow failed: no token received")

    console.print("[bold green]Azure authentication successful![/bold green]")

    meta = {
        "tenant_id": tenant_id,
        "client_id": client_id,
        "auth_method": "device_code",
        "scope": scope,
    }

    if _keyring_available():
        keyring.set_password(KEYRING_SERVICE, KEYRING_AZURE_TOKEN_KEY, json.dumps(meta))
        console.print("[dim]Credential metadata saved to OS keyring.[/dim]")

    return meta


def azure_auth_interactive(
    tenant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    auto_select: bool = False,
    method: Optional[str] = None,
) -> dict[str, Any]:
    """Interactive TUI flow for Azure authentication + subscription/resource group discovery.

    Steps:
    1. Authenticate (OAuth device code or service principal)
    2. List accessible subscriptions from Azure
    3. User selects which subscriptions to extract
    4. Optionally list and select resource groups per subscription
    5. Persist selections in keyring

    Returns credential metadata dict with subscription selections.
    """
    import questionary

    console.rule("[bold blue]Azure Authentication[/bold blue]")

    tenant = tenant_id or "organizations"

    if method is None:
        method = questionary.select(
            "Authentication method:",
            choices=[
                "Azure CLI (az login — recommended)",
                "OAuth device code (browser login)",
                "Manual (service principal credentials)",
            ],
        ).ask()

        if method is None:
            raise KeyboardInterrupt

    if "Azure CLI" in method or method == "azure_cli":
        from azure.identity import AzureCliCredential

        console.print("[dim]Verifying az login...[/dim]")
        cred = AzureCliCredential()
        token = cred.get_token(AZURE_DEFAULT_SCOPE)
        if token is None:
            raise RuntimeError("Azure CLI credential failed: no token received")
        console.print("[bold green]Azure authentication successful![/bold green]")
        meta = {
            "tenant_id": tenant,
            "client_id": "cli",
            "auth_method": "azure_cli",
            "scope": AZURE_DEFAULT_SCOPE,
        }

        if _keyring_available():
            keyring.set_password(KEYRING_SERVICE, KEYRING_AZURE_TOKEN_KEY, json.dumps(meta))
            console.print("[dim]Credential metadata saved to OS keyring.[/dim]")
    elif "OAuth" in method:
        cli_client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        app_client_id = (
            cli_client_id
            or questionary.text(
                "Client ID / App ID:",
                default=AZURE_FINNA_PUBLIC_CLIENT_ID,
            ).ask()
        )
        meta = azure_device_flow(tenant_id=tenant, client_id=app_client_id)
    else:
        client_id = questionary.text("Client ID / App ID:").ask()
        client_secret = questionary.password("Client secret:").ask()
        if client_id is None:
            raise KeyboardInterrupt
        meta = {
            "tenant_id": tenant.strip(),
            "client_id": client_id.strip(),
            "client_secret": client_secret or "",
            "auth_method": "client_secret",
        }
        if _keyring_available() and client_secret:
            keyring.set_password(KEYRING_SERVICE, f"azure-client-secret-{tenant.strip()}", client_secret)
            console.print("[dim]Client secret saved to OS keyring.[/dim]")

    credential = _build_credential_from_meta(meta)

    subscriptions = _discover_azure_subscriptions(credential)
    if not subscriptions:
        console.print("[yellow]No accessible Azure subscriptions found.[/yellow]")
        return meta

    if auto_select:
        console.print(f"[dim]Auto-selecting all {len(subscriptions)} subscription(s)[/dim]")
        selected = subscriptions
    else:
        selected = _select_azure_subscriptions(subscriptions)
    if not selected:
        console.print("[yellow]No subscriptions selected.[/yellow]")
        return meta

    rg_selections = {}
    for sub in selected:
        rgs = _discover_azure_resource_groups(credential, sub["subscription_id"])
        if rgs:
            if auto_select:
                console.print(
                    f"[dim]Auto-selecting all {len(rgs)} resource group(s) for {sub['subscription_id']}[/dim]"
                )
                chosen = rgs
            else:
                chosen = _select_azure_resource_groups(sub["subscription_id"], sub.get("display_name", ""), rgs)
            if chosen is not None:
                rg_selections[sub["subscription_id"]] = chosen

    meta["subscriptions"] = [
        {
            "subscription_id": s["subscription_id"],
            "display_name": s.get("display_name", ""),
            "resource_groups": rg_selections.get(s["subscription_id"], []),
        }
        for s in selected
    ]

    if _keyring_available():
        keyring.set_password(KEYRING_SERVICE, KEYRING_AZURE_TOKEN_KEY, json.dumps(meta))
        console.print("[dim]Subscription selections saved to OS keyring.[/dim]")

    console.print(f"\n[bold green]Configured {len(selected)} subscription(s) for extraction.[/bold green]")
    return meta


def _build_credential_from_meta(meta: dict[str, Any]):
    """Build an Azure credential object from stored metadata."""
    if meta.get("auth_method") == "client_secret":
        from azure.identity import ClientSecretCredential

        return ClientSecretCredential(
            tenant_id=meta.get("tenant_id", "organizations"),
            client_id=meta.get("client_id", ""),
            client_secret=meta.get("client_secret", ""),
        )

    if meta.get("auth_method") == "azure_cli":
        from azure.identity import AzureCliCredential

        return AzureCliCredential()

    from azure.identity import DeviceCodeCredential
    from msal_extensions import PersistedTokenCache, build_encrypted_persistence

    persistence = build_encrypted_persistence("finna-app-azure-cache")
    token_cache = PersistedTokenCache(persistence)
    return DeviceCodeCredential(
        client_id=meta.get("client_id", AZURE_FINNA_PUBLIC_CLIENT_ID),
        tenant_id=meta.get("tenant_id", "organizations"),
        cache=token_cache,
        disable_automatic_authentication=True,
    )


def _discover_azure_subscriptions(credential) -> list[dict[str, str]]:
    """List Azure subscriptions accessible to the current credential."""
    try:
        import requests

        token = credential.get_token("https://management.azure.com/.default")
        if not token:
            return []

        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json",
        }

        resp = requests.get(
            "https://management.azure.com/subscriptions?api-version=2020-01-01",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()

        subs = []
        for item in resp.json().get("value", []):
            subs.append(
                {
                    "subscription_id": item.get("subscriptionId", ""),
                    "display_name": item.get("displayName", ""),
                    "state": item.get("state", ""),
                }
            )
        subs.sort(key=lambda s: s.get("display_name", ""))
        return subs
    except Exception as exc:
        console.print(f"[red]Failed to list subscriptions: {exc}[/red]")
        return []


def _select_azure_subscriptions(subs: list[dict[str, str]]) -> list[dict[str, str]]:
    """Let the user pick which subscriptions to extract."""
    import questionary
    from rich.table import Table

    table = Table(title="Available Azure Subscriptions", show_lines=True)
    table.add_column("#", style="dim")
    table.add_column("Subscription ID", style="cyan")
    table.add_column("Name")
    table.add_column("State")
    for i, s in enumerate(subs, 1):
        table.add_row(str(i), s["subscription_id"], s["display_name"], s.get("state", ""))
    console.print(table)

    choices = [
        f"{s['display_name']} ({s['subscription_id']})" if s["display_name"] else s["subscription_id"] for s in subs
    ]
    choices.append("ALL")

    selected = questionary.checkbox(
        "Select subscriptions to extract:",
        choices=choices,
    ).ask()

    if selected is None:
        raise KeyboardInterrupt

    if "ALL" in selected:
        return subs

    result = []
    for choice in selected:
        for s in subs:
            label = f"{s['display_name']} ({s['subscription_id']})" if s["display_name"] else s["subscription_id"]
            if label == choice:
                result.append(s)
                break

    return result


def _discover_azure_resource_groups(credential, subscription_id: str) -> list[str]:
    """List resource groups in an Azure subscription."""
    try:
        from azure.mgmt.resource import ResourceManagementClient

        client = ResourceManagementClient(credential, subscription_id)
        rgs = [rg.name for rg in client.resource_groups.list()]
        rgs.sort()
        return rgs
    except Exception as exc:
        console.print(f"[dim]Could not list resource groups for {subscription_id}: {exc}[/dim]")
        return []


def _select_azure_resource_groups(sub_id: str, sub_name: str, rgs: list[str]) -> Optional[list[str]]:
    """Let the user pick resource groups for a subscription."""
    import questionary
    from rich.table import Table

    label = f"{sub_name} ({sub_id})" if sub_name else sub_id
    console.rule(f"[bold blue]Resource Groups — {label}[/bold blue]")

    table = Table(show_lines=True)
    table.add_column("Resource Group", style="cyan")
    for rg in rgs:
        table.add_row(rg)
    console.print(table)

    use_all = questionary.confirm(
        f"Extract ALL resource groups in this subscription? ({len(rgs)} found)",
        default=True,
    ).ask()

    if use_all is None:
        return None

    if use_all:
        return []

    choices = rgs + ["ALL"]
    selected = questionary.checkbox(
        "Select resource groups:",
        choices=choices,
    ).ask()

    if selected is None:
        return None

    if "ALL" in selected:
        return []

    return selected


def get_azure_subscription_selections() -> Optional[list[dict[str, Any]]]:
    """Retrieve saved Azure subscription selections from keyring."""
    meta = get_saved_azure_meta()
    if meta and "subscriptions" in meta:
        return meta["subscriptions"]
    return None


def get_azure_credential(
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    subscription_id: str | None = None,
):
    """Build an Azure credential object for extractor use.

    Tries in order:
    1. Explicit client_secret params (production / env vars)
    2. Saved device-code token cache in keyring
    3. Azure CLI credentials (az login)
    4. Environment variables (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)
    """
    from azure.identity import (
        AzureCliCredential,
        ClientSecretCredential,
        DefaultAzureCredential,
        DeviceCodeCredential,
    )

    explicit_tenant = tenant_id or os.getenv("AZURE_TENANT_ID")
    explicit_client_id = client_id or os.getenv("AZURE_CLIENT_ID")
    explicit_secret = client_secret or os.getenv("AZURE_CLIENT_SECRET")
    auth_method = os.getenv("AZURE_AUTH_METHOD", "").lower()

    # Check for CLI auth method first (takes precedence over explicit params)
    if auth_method == "cli":
        logger.info("Using AzureCliCredential (AZURE_AUTH_METHOD=cli)")
        return AzureCliCredential()

    # Use explicit params only if no CLI auth method specified
    if explicit_tenant and explicit_client_id and explicit_secret:
        logger.info("Using ClientSecretCredential (explicit/env vars)")
        return ClientSecretCredential(
            tenant_id=explicit_tenant,
            client_id=explicit_client_id,
            client_secret=explicit_secret,
        )

    if _keyring_available():
        try:
            saved = keyring.get_password(KEYRING_SERVICE, KEYRING_AZURE_TOKEN_KEY)
            if saved:
                meta = json.loads(saved)
                from msal_extensions import (
                    PersistedTokenCache,
                    build_encrypted_persistence,
                )

                persistence = build_encrypted_persistence("finna-app-azure-cache")
                token_cache = PersistedTokenCache(persistence)
                cred = DeviceCodeCredential(
                    client_id=meta.get("client_id", AZURE_FINNA_PUBLIC_CLIENT_ID),
                    tenant_id=meta.get("tenant_id", explicit_tenant or "organizations"),
                    cache=token_cache,
                    disable_automatic_authentication=True,
                )
                try:
                    cred.get_token(AZURE_DEFAULT_SCOPE)
                    logger.info("Using cached device-code credentials from keyring")
                    return cred
                except Exception:
                    logger.debug("Cached device-code token expired, falling through")
        except Exception:
            logger.debug("Keyring lookup failed, falling through")

    try:
        AzureCliCredential().get_token(AZURE_DEFAULT_SCOPE)
        logger.info("Using Azure CLI credentials")
        return AzureCliCredential()
    except Exception:
        pass

    logger.info("Using DefaultAzureCredential (final fallback)")
    return DefaultAzureCredential()


# ---------------------------------------------------------------------------
# GCP OAuth (ADC delegation)
# ---------------------------------------------------------------------------


def gcp_auth_interactive() -> dict[str, Any]:
    """Interactive TUI flow for GCP authentication.

    Checks for existing ADC; if not found, offers to run gcloud auth login.
    """
    import questionary
    from google.auth import default as google_auth_default
    from google.auth.exceptions import DefaultCredentialsError

    console.rule("[bold blue]GCP Authentication[/bold blue]")

    try:
        creds, project = google_auth_default()
        if creds and creds.valid:
            console.print(f"[bold green]GCP credentials found![/bold green] Project: [cyan]{project}[/cyan]")
            return {"auth_method": "adc", "project": project, "valid": True}
    except (DefaultCredentialsError, Exception):
        pass

    console.print("[yellow]No GCP Application Default Credentials found.[/yellow]")

    method = questionary.select(
        "How to authenticate GCP?",
        choices=[
            "Run 'gcloud auth login' (opens browser — recommended)",
            "Set GOOGLE_APPLICATION_CREDENTIALS env var (service account)",
            "Skip GCP for now",
        ],
    ).ask()

    if method is None or "Skip" in (method or ""):
        return {"auth_method": "skipped"}

    if "gcloud" in method:
        scope = "https://www.googleapis.com/auth/cloud-platform"
        cmd = ["gcloud", "auth", "login", "--update-adc", f"--scopes={scope}"]
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            console.print("[red]gcloud CLI not found. Install from https://cloud.google.com/sdk[/red]")
            return {"auth_method": "failed", "error": "gcloud not found"}
        except subprocess.CalledProcessError as exc:
            console.print(f"[red]gcloud auth login failed: {exc}[/red]")
            return {"auth_method": "failed", "error": str(exc)}

        try:
            creds, project = google_auth_default()
            if creds and creds.valid:
                console.print(f"[bold green]GCP authenticated![/bold green] Project: [cyan]{project}[/cyan]")
                if _keyring_available():
                    keyring.set_password(KEYRING_SERVICE, KEYRING_GCP_ADC_STATUS, "configured")
                return {"auth_method": "adc", "project": project, "valid": True}
        except Exception:
            console.print("[yellow]ADC still not detected after gcloud login.[/yellow]")
            return {"auth_method": "failed", "error": "ADC not detected after login"}

    if "GOOGLE_APPLICATION_CREDENTIALS" in method:
        sa_path = questionary.text(
            "Path to service account JSON key file:",
        ).ask()
        if sa_path:
            expanded = str(Path(sa_path).expanduser())
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = expanded
            try:
                creds, project = google_auth_default()
                if creds and creds.valid:
                    console.print(
                        f"[bold green]GCP authenticated via service account![/bold green] "
                        f"Project: [cyan]{project}[/cyan]"
                    )
                    return {
                        "auth_method": "service_account",
                        "project": project,
                        "path": expanded,
                        "valid": True,
                    }
            except Exception as exc:
                console.print(f"[red]Failed to load service account: {exc}[/red]")
                return {"auth_method": "failed", "error": str(exc)}

    return {"auth_method": "skipped"}


def get_gcp_credentials():
    """Get GCP credentials for extractor use.

    Uses ADC chain:
    1. GOOGLE_APPLICATION_CREDENTIALS env var (service account)
    2. gcloud user credentials (from gcloud auth login)
    3. Compute metadata (if on GCP)

    No separate keyring storage needed — ADC handles it.
    """
    from google.auth import default as google_auth_default

    creds, project = google_auth_default()
    if not creds or not creds.valid:
        raise RuntimeError(
            "No GCP credentials available. Run 'python -m config.auth gcp' or set GOOGLE_APPLICATION_CREDENTIALS."
        )
    return creds, project


# ---------------------------------------------------------------------------
# Credential metadata helpers
# ---------------------------------------------------------------------------


def get_saved_azure_meta() -> Optional[dict[str, Any]]:
    """Retrieve saved Azure credential metadata from keyring."""
    if not _keyring_available():
        return None
    try:
        raw = keyring.get_password(KEYRING_SERVICE, KEYRING_AZURE_TOKEN_KEY)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def get_saved_gcp_meta() -> Optional[dict[str, Any]]:
    """Retrieve saved GCP credential status from keyring."""
    if not _keyring_available():
        return None
    try:
        raw = keyring.get_password(KEYRING_SERVICE, KEYRING_GCP_ADC_STATUS)
        return {"status": raw} if raw else None
    except Exception:
        return None


def clear_credentials(provider: str = "all") -> None:
    """Remove saved credentials from keyring."""
    if provider in ("azure", "all"):
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_AZURE_TOKEN_KEY)
        except Exception:
            pass
    if provider in ("gcp", "all"):
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_GCP_ADC_STATUS)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

# API integration helpers


def push_config_to_api(meta: dict[str, Any], api_url: str) -> dict[str, Any]:
    """Push config to API endpoint.

    Args:
        meta: Configuration metadata from auth flow
        api_url: Base URL of the API (e.g., http://localhost:8000)

    Returns:
        API response with config_id
    """
    import requests

    provider = meta.get("provider", "azure")

    # Map auth method to credential type
    auth_method = meta.get("auth_method", "service_principal")
    cred_type_map = {
        "azure_cli": "cli",
        "azure_auth": "cli",
        "device_code": "device_code",
    }
    credential_type = cred_type_map.get(auth_method, "service_principal")

    # Build config payload
    if provider == "azure":
        config_payload = {
            "provider": "azure",
            "name": meta.get("display_name", "Azure Config"),
            "credential_type": credential_type,
            "config": {
                "tenant_id": meta.get("tenant_id", ""),
                "client_id": meta.get("client_id", ""),
                "client_secret": meta.get("client_secret", ""),
                "subscription_id": "",
                "resource_groups": [],
                "scope": "resourcegroup",
            },
        }

        # Add subscriptions if present
        if "subscriptions" in meta and meta["subscriptions"]:
            subs = meta["subscriptions"]
            if subs:
                sub = subs[0]
                config_payload["config"]["subscription_id"] = sub.get("subscription_id", "")
                config_payload["config"]["resource_groups"] = sub.get("resource_groups", [])

    elif provider == "gcp":
        config_payload = {
            "provider": "gcp",
            "name": meta.get("project_name", "GCP Config"),
            "credential_type": "service_account",
            "config": {
                "project_id": meta.get("project_id", ""),
            },
        }
    else:
        raise ValueError(f"Unknown provider: {provider}")

    url = f"{api_url.rstrip('/')}/api/v1/config"
    console.print(f"[dim]Pushing config to {url}...[/dim]")

    response = requests.post(url, json=config_payload, timeout=30)
    response.raise_for_status()

    result = response.json()
    console.print(f"[green]Config pushed successfully! config_id={result.get('id')}[/green]")

    return result


def run_extractor_via_api(provider: str, api_url: str) -> dict[str, Any]:
    """Trigger extractor run via API.

    Args:
        provider: Cloud provider (azure, gcp)
        api_url: Base URL of the API

    Returns:
        API response with run_id
    """
    import requests

    url = f"{api_url.rstrip('/')}/api/v1/extractors/run"
    console.print(f"[dim]Triggering extractor for {provider}...[/dim]")

    response = requests.post(
        url,
        json={"provider": provider},
        timeout=30,
    )
    response.raise_for_status()

    result = response.json()
    console.print(f"[green]Extractor started! run_id={result.get('id')}, status={result.get('status')}[/green]")

    return result


def main() -> None:
    """CLI entrypoint for config.auth module."""
    import argparse

    parser = argparse.ArgumentParser(description="FinOps cloud provider authentication")
    parser.add_argument("provider", choices=["azure", "gcp"], help="Cloud provider to authenticate")
    parser.add_argument("--tenant-id", default=None, help="Azure AD tenant ID")
    parser.add_argument("--client-id", default=None, help="Azure app client ID")
    parser.add_argument(
        "--subscription-id",
        default=None,
        help="Subscription ID (auto-select all if not provided)",
    )
    parser.add_argument("--auto-select", action="store_true", help="Auto-select all subscriptions")
    parser.add_argument("--clear", action="store_true", help="Clear saved credentials")
    parser.add_argument(
        "--api-url",
        default=None,
        help="Push config to API after auth (e.g., http://localhost:8000)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Trigger extractor run after auth (requires --api-url)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")

    if args.clear:
        clear_credentials(args.provider)
        console.print(f"[green]Cleared {args.provider} credentials.[/green]")
        return

    api_url = args.api_url
    if args.run and not api_url:
        console.print("[red]--run requires --api-url[/red]")
        return

    if args.provider == "azure":
        method = "azure_cli" if args.auto_select else None
        result = azure_auth_interactive(
            tenant_id=args.tenant_id,
            client_id=args.client_id,
            auto_select=args.auto_select,
            method=method,
        )
        console.print(f"\nResult: {json.dumps(result, indent=2, default=str)}")

        # Push to API if requested
        if api_url:
            result["provider"] = "azure"
            try:
                config_result = push_config_to_api(result, api_url)
                console.print(f"[green]Config pushed to API: {config_result.get('id')}[/green]")

                # Trigger run if requested
                if args.run:
                    run_result = run_extractor_via_api("azure", api_url)
                    console.print(f"[green]Extractor triggered: {run_result.get('id')}[/green]")
            except Exception as e:
                console.print(f"[red]API error: {e}[/red]")

    elif args.provider == "gcp":
        result = gcp_auth_interactive()
        console.print(f"\nResult: {json.dumps(result, indent=2, default=str)}")

        # Push to API if requested
        if api_url:
            result["provider"] = "gcp"
            try:
                config_result = push_config_to_api(result, api_url)
                console.print(f"[green]Config pushed to API: {config_result.get('id')}[/green]")

                # Trigger run if requested
                if args.run:
                    run_result = run_extractor_via_api("gcp", api_url)
                    console.print(f"[green]Extractor triggered: {run_result.get('id')}[/green]")
            except Exception as e:
                console.print(f"[red]API error: {e}[/red]")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Azure Service Account Authentication (CLI)  
# ---------------------------------------------------------------------------


def azure_service_account_auth(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    subscription_id: str | None = None,
    auto_select: bool = False,
) -> dict[str, Any]:
    """Authenticate Azure using service account (client secret).

    This is the non-interactive method for production use.

    Args:
        tenant_id: Azure AD tenant ID
        client_id: Application/client ID
        client_secret: Application client secret
        subscription_id: Optional subscription ID
        auto_select: Auto-select all subscriptions if no subscription_id provided

    Returns:
        dict with credential metadata and subscription selections
    """
    from azure.identity import ClientSecretCredential

    console.rule("[bold blue]Azure Service Account Authentication[/bold blue]")

    console.print("[dim]Building ClientSecretCredential...[/dim]")
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    # Verify credentials
    try:
        token = credential.get_token(AZURE_DEFAULT_SCOPE)
        console.print("[bold green]Azure service account authentication successful![/bold green]")
    except Exception as exc:
        console.print(f"[red]Authentication failed: {exc}[/red]")
        raise

    meta = {
        "tenant_id": tenant_id,
        "client_id": client_id,
        "auth_method": "service_account",
        "scope": AZURE_DEFAULT_SCOPE,
    }

    # Discover subscriptions if auto_select
    if auto_select:
        subscriptions = _discover_azure_subscriptions(credential)
        if not subscriptions:
            console.print("[yellow]No accessible Azure subscriptions found.[/yellow]")
            return meta

        console.print(f"[dim]Auto-selecting all {len(subscriptions)} subscription(s)[/dim]")
        selected = subscriptions

        rg_selections = {}
        for sub in selected:
            rgs = _discover_azure_resource_groups(credential, sub["subscription_id"])
            if rgs:
                console.print(
                    f"[dim]Auto-selecting all {len(rgs)} resource group(s) for {sub['subscription_id']}[/dim]"
                )
                rg_selections[sub["subscription_id"]] = rgs

        meta["subscriptions"] = [
            {
                "subscription_id": s["subscription_id"],
                "display_name": s.get("display_name", ""),
                "resource_groups": rg_selections.get(s["subscription_id"], []),
            }
            for s in selected
        ]

        if subscription_id:
            meta["subscription_id"] = subscription_id
    else:
        if subscription_id:
            meta["subscription_id"] = subscription_id

    console.print(f"\n[bold green]Service account configured successfully![/bold green]")

    return meta
