"""Azure resource-inventory extractor for wastage scanning.

Uses azure-mgmt-resourcegraph to run KQL queries across one or more
subscriptions and stream back normalized inventory dicts suitable for
passing directly into wastage rules.

Each resource type is fetched with its own KQL query so rule authors get
consistently named fields regardless of the underlying ARM schema.

Normalised dict keys (common across all resource types):
  provider          str  "azure"
  account_id        str  subscription ID
  resource_id       str  ARM resource ID (lower-cased for stable hashing)
  resource_name     str
  resource_type     str  e.g. "Microsoft.Compute/disks"
  resource_group    str
  region            str  Azure location, lower-cased (e.g. "westeurope")
  tags              dict[str, str]

Resource-specific keys documented per KQL query below.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# KQL queries — one per resource type
# ---------------------------------------------------------------------------

_KQL_DISKS = """
Resources
| where type == "microsoft.compute/disks"
| project
    id,
    name,
    resourceGroup,
    location,
    subscriptionId,
    tags,
    managedBy = properties.managedBy,
    diskSizeGb = properties.diskSizeGB,
    sku = sku.name,
    diskState = properties.diskState,
    timeCreated = properties.timeCreated
"""

_KQL_PUBLIC_IPS = """
Resources
| where type == "microsoft.network/publicipaddresses"
| project
    id,
    name,
    resourceGroup,
    location,
    subscriptionId,
    tags,
    skuName = sku.name,
    allocationMethod = properties.publicIPAllocationMethod,
    ipConfiguration = properties.ipConfiguration,
    ipAddress = properties.ipAddress
"""

_KQL_NICS = """
Resources
| where type == "microsoft.network/networkinterfaces"
| project
    id,
    name,
    resourceGroup,
    location,
    subscriptionId,
    tags,
    virtualMachine = properties.virtualMachine,
    privateIpAddress = properties.ipConfigurations[0].properties.privateIPAddress
"""

_KQL_SNAPSHOTS = """
Resources
| where type == "microsoft.compute/snapshots"
| project
    id,
    name,
    resourceGroup,
    location,
    subscriptionId,
    tags,
    diskSizeGb = properties.diskSizeGB,
    sku = sku.name,
    timeCreated = properties.timeCreated
"""

_KQL_VMS = """
Resources
| where type == "microsoft.compute/virtualmachines"
| extend powerState = properties.extended.instanceView.powerState.code
| project
    id,
    name,
    resourceGroup,
    location,
    subscriptionId,
    tags,
    vmSize = properties.hardwareProfile.vmSize,
    powerState,
    storageProfile = properties.storageProfile,
    osDiskId = properties.storageProfile.osDisk.managedDisk.id,
    dataDisks = properties.storageProfile.dataDisks
"""

_KQL_AKS = """
Resources
| where type == "microsoft.containerservice/managedclusters"
| project
    id,
    name,
    resourceGroup,
    location,
    subscriptionId,
    tags,
    agentPoolProfiles = properties.agentPoolProfiles,
    kubernetesVersion = properties.kubernetesVersion,
    provisioningState = properties.provisioningState
"""

_KQL_ASPS = """
Resources
| where type == "microsoft.web/serverfarms"
| project
    id,
    name,
    resourceGroup,
    location,
    subscriptionId,
    tags,
    skuName = sku.name,
    skuTier = sku.tier,
    numberOfWorkers = sku.capacity
"""

_KQL_STORAGE = """
Resources
| where type == "microsoft.storage/storageaccounts"
| project
    id,
    name,
    resourceGroup,
    location,
    subscriptionId,
    tags,
    kind,
    skuName = sku.name,
    skuTier = sku.tier,
    accessTier = properties.accessTier
"""

_KQL_REDIS = """
Resources
| where type == "microsoft.cache/redis"
| project
    id,
    name,
    resourceGroup,
    location,
    subscriptionId,
    tags,
    skuName = properties.sku.name,
    skuFamily = properties.sku.family,
    skuCapacity = properties.sku.capacity,
    provisioningState = properties.provisioningState
"""

# ---------------------------------------------------------------------------
# Auth helpers (reuse pattern from azure_cost.py)
# ---------------------------------------------------------------------------


def _build_resource_graph_client(
    subscription_ids: list[str],
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> Any:
    """Create an authenticated ResourceGraphClient."""
    from azure.mgmt.resourcegraph import ResourceGraphClient

    if tenant_id and client_id and client_secret:
        from azure.identity import ClientSecretCredential

        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
    else:
        from config.auth import get_azure_credential

        credential = get_azure_credential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    return ResourceGraphClient(credential=credential)


# ---------------------------------------------------------------------------
# Query runner with pagination
# ---------------------------------------------------------------------------


def _run_kql(
    client: Any,
    subscription_ids: list[str],
    kql: str,
    resource_type_label: str,
) -> list[dict[str, Any]]:
    """Execute a KQL query via Resource Graph, handling pagination."""
    from azure.mgmt.resourcegraph.models import QueryRequest, QueryRequestOptions

    all_rows: list[dict[str, Any]] = []
    skip_token: str | None = None

    while True:
        options = QueryRequestOptions(result_format="objectArray", top=1000)
        if skip_token:
            options.skip_token = skip_token

        request = QueryRequest(
            subscriptions=subscription_ids,
            query=kql,
            options=options,
        )

        result = client.resources(request)

        data = result.data or []
        if isinstance(data, list):
            all_rows.extend(data)
        else:
            # Some SDK versions return dicts/objects
            all_rows.extend(list(data))

        skip_token = getattr(result, "skip_token", None)
        if not skip_token:
            break

        logger.debug(
            "Resource Graph (%s): paginating, %d rows so far",
            resource_type_label,
            len(all_rows),
        )

    logger.info(
        "Resource Graph (%s): fetched %d rows",
        resource_type_label,
        len(all_rows),
    )
    return all_rows


# ---------------------------------------------------------------------------
# Row normalizers — one per resource type
# ---------------------------------------------------------------------------


def _common(row: dict[str, Any]) -> dict[str, Any]:
    """Extract common fields present in every KQL result."""
    tags_raw = row.get("tags") or {}
    if not isinstance(tags_raw, dict):
        tags_raw = {}
    tags: dict[str, str] = {str(k): str(v) for k, v in tags_raw.items()}

    return {
        "provider": "azure",
        "account_id": str(row.get("subscriptionId", "") or ""),
        "resource_id": str(row.get("id", "") or "").lower(),
        "resource_name": str(row.get("name", "") or ""),
        "resource_group": str(row.get("resourceGroup", "") or "").lower(),
        "region": str(row.get("location", "") or "").lower().replace(" ", ""),
        "tags": tags,
    }


def _normalize_disk(row: dict[str, Any]) -> dict[str, Any]:
    out = _common(row)
    out["resource_type"] = "Microsoft.Compute/disks"
    out["managed_by"] = str(row.get("managedBy") or "").strip()
    out["size_gb"] = float(row.get("diskSizeGb") or 0)
    out["sku"] = str(row.get("sku") or "Standard_LRS")
    out["disk_state"] = str(row.get("diskState") or "")
    out["time_created"] = str(row.get("timeCreated") or "")
    return out


def _normalize_public_ip(row: dict[str, Any]) -> dict[str, Any]:
    out = _common(row)
    out["resource_type"] = "Microsoft.Network/publicIPAddresses"
    out["sku_name"] = str(row.get("skuName") or "Basic")
    out["allocation_method"] = str(row.get("allocationMethod") or "Dynamic")
    ip_config = row.get("ipConfiguration")
    out["ip_configuration"] = ip_config  # None if unattached
    out["ip_address"] = str(row.get("ipAddress") or "")
    return out


def _normalize_nic(row: dict[str, Any]) -> dict[str, Any]:
    out = _common(row)
    out["resource_type"] = "Microsoft.Network/networkInterfaces"
    vm = row.get("virtualMachine")
    out["virtual_machine"] = vm  # None if orphaned
    out["private_ip_address"] = str(row.get("privateIpAddress") or "")
    return out


def _normalize_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    out = _common(row)
    out["resource_type"] = "Microsoft.Compute/snapshots"
    out["size_gb"] = float(row.get("diskSizeGb") or 0)
    out["sku"] = str(row.get("sku") or "Standard_LRS")
    out["time_created"] = str(row.get("timeCreated") or "")
    return out


def _normalize_vm(row: dict[str, Any]) -> dict[str, Any]:
    out = _common(row)
    out["resource_type"] = "Microsoft.Compute/virtualMachines"
    power_raw = str(row.get("powerState") or "")
    # powerState codes look like "PowerState/deallocated"
    if "/" in power_raw:
        out["power_state"] = power_raw.split("/", 1)[1].lower()
    else:
        out["power_state"] = power_raw.lower()
    out["vm_size"] = str(row.get("vmSize") or "")

    # Collect attached disk IDs (OS + data disks)
    disk_ids: list[str] = []
    os_disk_id = row.get("osDiskId")
    if os_disk_id:
        disk_ids.append(str(os_disk_id).lower())
    data_disks = row.get("dataDisks") or []
    if isinstance(data_disks, list):
        for dd in data_disks:
            if isinstance(dd, dict):
                did = dd.get("managedDisk", {})
                if isinstance(did, dict):
                    mid = did.get("id")
                    if mid:
                        disk_ids.append(str(mid).lower())
    out["attached_disk_ids"] = disk_ids
    return out


def _normalize_aks(row: dict[str, Any]) -> dict[str, Any]:
    out = _common(row)
    out["resource_type"] = "Microsoft.ContainerService/managedClusters"
    profiles = row.get("agentPoolProfiles") or []
    if not isinstance(profiles, list):
        profiles = []

    pools: list[dict[str, Any]] = []
    for p in profiles:
        if isinstance(p, dict):
            pools.append(
                {
                    "name": str(p.get("name") or ""),
                    "count": int(p.get("count") or 0),
                    "vm_size": str(p.get("vmSize") or ""),
                    "mode": str(p.get("mode") or ""),
                }
            )
    out["agent_pool_profiles"] = pools
    out["kubernetes_version"] = str(row.get("kubernetesVersion") or "")
    return out


def _normalize_asp(row: dict[str, Any]) -> dict[str, Any]:
    out = _common(row)
    out["resource_type"] = "Microsoft.Web/serverFarms"
    out["sku_name"] = str(row.get("skuName") or "")
    out["sku_tier"] = str(row.get("skuTier") or "")
    out["number_of_workers"] = int(row.get("numberOfWorkers") or 0)
    return out


def _normalize_storage(row: dict[str, Any]) -> dict[str, Any]:
    out = _common(row)
    out["resource_type"] = "Microsoft.Storage/storageAccounts"
    out["kind"] = str(row.get("kind") or "")
    out["sku_name"] = str(row.get("skuName") or "")
    out["sku_tier"] = str(row.get("skuTier") or "")
    out["access_tier"] = str(row.get("accessTier") or "")
    return out


def _normalize_redis(row: dict[str, Any]) -> dict[str, Any]:
    out = _common(row)
    out["resource_type"] = "Microsoft.Cache/Redis"
    out["sku_name"] = str(row.get("skuName") or "")
    out["sku_family"] = str(row.get("skuFamily") or "")
    out["sku_capacity"] = int(row.get("skuCapacity") or 0)
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_RESOURCE_QUERIES: list[tuple[str, str, Any]] = [
    ("disks", _KQL_DISKS, _normalize_disk),
    ("public_ips", _KQL_PUBLIC_IPS, _normalize_public_ip),
    ("nics", _KQL_NICS, _normalize_nic),
    ("snapshots", _KQL_SNAPSHOTS, _normalize_snapshot),
    ("vms", _KQL_VMS, _normalize_vm),
    ("aks", _KQL_AKS, _normalize_aks),
    ("asps", _KQL_ASPS, _normalize_asp),
    ("storage_accounts", _KQL_STORAGE, _normalize_storage),
    ("redis", _KQL_REDIS, _normalize_redis),
]


def stream_inventory(
    subscription_ids: list[str],
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Yield normalized inventory rows for all supported resource types.

    Args:
        subscription_ids: One or more Azure subscription IDs to scan.
        tenant_id: Service-principal tenant (optional; falls back to env/keyring).
        client_id: Service-principal app ID (optional).
        client_secret: Service-principal secret (optional).

    Yields:
        One dict per resource, normalized for direct consumption by wastage rules.
    """
    if not subscription_ids:
        logger.warning("stream_inventory: no subscription_ids provided — skipping")
        return

    client = _build_resource_graph_client(
        subscription_ids=subscription_ids,
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    for label, kql, normalizer in _RESOURCE_QUERIES:
        try:
            rows = _run_kql(client, subscription_ids, kql, label)
        except Exception:
            logger.exception("Resource Graph query failed for %s — skipping", label)
            continue

        for raw in rows:
            try:
                yield normalizer(raw)
            except Exception:
                logger.exception(
                    "Normalization failed for %s row %r — skipping", label, raw
                )


def fetch_inventory_for_subscription(
    subscription_id: str,
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> list[dict[str, Any]]:
    """Convenience wrapper: fetch all inventory rows for a single subscription.

    Internally calls :func:`stream_inventory` and collects results into a list.
    """
    return list(
        stream_inventory(
            subscription_ids=[subscription_id],
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
    )
