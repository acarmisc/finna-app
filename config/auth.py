"""Authentication helpers for cloud extractors.

Provides credential resolution using environment variables as the primary
mechanism, with fallbacks to Azure CLI / GCP default credentials when
available.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("config.auth")


def get_azure_credential(
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> Any:
    """Return an Azure credential object.

    Resolution order:
    1. ClientSecretCredential if tenant_id, client_id, client_secret are provided
       (either as arguments or via environment variables).
    2. DefaultAzureCredential as a catch-all fallback.
    """
    from azure.identity import ClientSecretCredential, DefaultAzureCredential

    tid = tenant_id or os.getenv("AZURE_TENANT_ID")
    cid = client_id or os.getenv("AZURE_CLIENT_ID")
    csec = client_secret or os.getenv("AZURE_CLIENT_SECRET")

    if tid and cid and csec:
        logger.info("Using ClientSecretCredential for tenant=%s client=%s", tid, cid)
        return ClientSecretCredential(
            tenant_id=tid,
            client_id=cid,
            client_secret=csec,
        )

    logger.info("Falling back to DefaultAzureCredential")
    return DefaultAzureCredential()


def get_azure_subscription_selections() -> list[dict[str, Any]]:
    """Return saved Azure subscription selections from environment variables.

    Reads AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUPS to construct
    a subscription selection list for multi-RG extraction. Includes
    tenant/client credentials from env vars when available so the
    extractor can authenticate with ClientSecretCredential.
    """
    sub_id = os.getenv("AZURE_SUBSCRIPTION_ID", "")
    rgs_raw = os.getenv("AZURE_RESOURCE_GROUPS", "")
    rgs = [rg.strip() for rg in rgs_raw.split(",") if rg.strip()]

    if not sub_id:
        return []

    selection: dict[str, Any] = {
        "subscription_id": sub_id,
        "resource_groups": rgs,
    }

    # Include credential info from env vars so the extractor
    # can use ClientSecretCredential instead of DefaultAzureCredential
    tid = os.getenv("AZURE_TENANT_ID", "")
    cid = os.getenv("AZURE_CLIENT_ID", "")
    csec = os.getenv("AZURE_CLIENT_SECRET", "")
    if tid:
        selection["tenant_id"] = tid
    if cid:
        selection["client_id"] = cid
    if csec:
        selection["client_secret"] = csec

    return [selection]


def get_gcp_credentials() -> tuple[Any, str]:
    """Return (credentials, project_id) for GCP.

    Uses Application Default Credentials when available, with the project
    ID read from the GCP_PROJECT environment variable.
    """
    import google.auth
    from google.auth.credentials import AnonymousCredentials

    project_id = os.getenv("GCP_PROJECT", os.getenv("GCP_PROJECT_ID", ""))

    if os.getenv("GCP_SERVICE_ACCOUNT_KEY"):
        try:
            sa_info = json.loads(os.environ["GCP_SERVICE_ACCOUNT_KEY"])
            from google.oauth2.service_account import Credentials

            creds = Credentials.from_service_account_info(sa_info)
            project_id = project_id or creds.project_id
            logger.info("Using GCP service account credentials for project=%s", project_id)
            return creds, project_id
        except Exception:
            logger.exception("Failed to parse GCP_SERVICE_ACCOUNT_KEY, falling back to defaults")

    try:
        creds, project = google.auth.default()
        project_id = project_id or project
        logger.info("Using GCP default credentials for project=%s", project_id)
        return creds, project_id
    except Exception:
        logger.warning("No GCP credentials available, using AnonymousCredentials")
        return AnonymousCredentials(), project_id
