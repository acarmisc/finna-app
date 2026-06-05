"""Azure wastage rules.

10 rules covering the most common wastage patterns found in real Azure
subscriptions.  Import this module to register them in the global REGISTRY::

    import backend.app.wastage.rules.azure  # side-effect: populates REGISTRY

Each function signature: (inventory_row: dict, pricing_module) -> Optional[Finding]
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from backend.app.wastage.rules import Finding, rule

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NONPROD_RE = re.compile(r"(dev|test|stage|staging|uat|qa)", re.IGNORECASE)


def _is_nonprod_rg(resource_group: str) -> bool:
    """Return True when the resource group name looks non-production."""
    return bool(_NONPROD_RE.search(resource_group))


def _parse_iso(ts: str) -> Optional[datetime]:
    """Best-effort parse of an ISO-8601 timestamp string. Returns None on failure."""
    if not ts:
        return None
    ts = ts.rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _age_days(ts: str) -> Optional[float]:
    """Return age in days from an ISO timestamp to now, or None if unparseable."""
    dt = _parse_iso(ts)
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


@rule(
    id="azure.disk.orphan",
    severity="high",
    category="storage",
    description="Managed disk has no VM attachment (managedBy is empty).",
)
def azure_disk_orphan(row: dict, pricing) -> Optional[Finding]:
    """Flag unattached managed disks."""
    if row.get("resource_type", "").lower() != "microsoft.compute/disks":
        return None
    if row.get("managed_by", "").strip():
        return None  # attached

    size_gb = float(row.get("size_gb") or 0)
    sku = str(row.get("sku") or "Standard_LRS")
    region = row.get("region", "westeurope")

    monthly_cost = pricing.lookup("azure", f"managed_disk/{sku}", region) * Decimal(
        str(size_gb)
    )

    return Finding(
        provider="azure",
        account_id=row["account_id"],
        resource_group=row.get("resource_group"),
        region=region,
        resource_id=row["resource_id"],
        resource_type="Microsoft.Compute/disks",
        rule_id="azure.disk.orphan",
        severity="high",
        category="storage",
        estimated_monthly_usd=monthly_cost,
        evidence={
            "size_gb": size_gb,
            "sku": sku,
            "disk_state": row.get("disk_state", ""),
            "managed_by": row.get("managed_by", ""),
        },
        tags=row.get("tags", {}),
        remediation=(
            "Delete the orphaned managed disk if no longer needed, or "
            "re-attach it to a virtual machine."
        ),
    )


@rule(
    id="azure.public_ip.unattached",
    severity="medium",
    category="network",
    description="Standard-SKU public IP has no associated IP configuration (unattached).",
)
def azure_public_ip_unattached(row: dict, pricing) -> Optional[Finding]:
    """Flag Standard-SKU public IPs with no IP configuration (unattached)."""
    if row.get("resource_type", "").lower() != "microsoft.network/publicipaddresses":
        return None
    if str(row.get("sku_name") or "").lower() != "standard":
        return None
    if row.get("ip_configuration") is not None:
        return None  # attached

    region = row.get("region", "westeurope")
    monthly_cost = pricing.lookup("azure", "public_ip/Standard_Static", region)

    return Finding(
        provider="azure",
        account_id=row["account_id"],
        resource_group=row.get("resource_group"),
        region=region,
        resource_id=row["resource_id"],
        resource_type="Microsoft.Network/publicIPAddresses",
        rule_id="azure.public_ip.unattached",
        severity="medium",
        category="network",
        estimated_monthly_usd=monthly_cost,
        evidence={
            "sku_name": row.get("sku_name", ""),
            "allocation_method": row.get("allocation_method", ""),
            "ip_address": row.get("ip_address", ""),
        },
        tags=row.get("tags", {}),
        remediation=(
            "Delete the unattached public IP address or associate it with a "
            "network interface or load balancer frontend."
        ),
    )


@rule(
    id="azure.public_ip.basic_sku",
    severity="low",
    category="network",
    description="Public IP uses deprecated Basic SKU; migrate to Standard.",
)
def azure_public_ip_basic_sku(row: dict, pricing) -> Optional[Finding]:
    """Flag Basic-SKU public IPs (deprecated, limited SLA, security posture)."""
    if row.get("resource_type", "").lower() != "microsoft.network/publicipaddresses":
        return None
    if str(row.get("sku_name") or "").lower() != "basic":
        return None

    region = row.get("region", "westeurope")
    # Basic IPs are free when dynamic; flag the configuration risk only
    monthly_cost = Decimal("0")

    return Finding(
        provider="azure",
        account_id=row["account_id"],
        resource_group=row.get("resource_group"),
        region=region,
        resource_id=row["resource_id"],
        resource_type="Microsoft.Network/publicIPAddresses",
        rule_id="azure.public_ip.basic_sku",
        severity="low",
        category="network",
        estimated_monthly_usd=monthly_cost,
        evidence={
            "sku_name": row.get("sku_name", ""),
            "allocation_method": row.get("allocation_method", ""),
        },
        tags=row.get("tags", {}),
        remediation=(
            "Migrate from Basic to Standard SKU public IP address. "
            "Basic SKU is deprecated and offers no zone redundancy or SLA."
        ),
    )


@rule(
    id="azure.nic.orphan",
    severity="medium",
    category="network",
    description="Network interface has no virtual machine association.",
)
def azure_nic_orphan(row: dict, pricing) -> Optional[Finding]:
    """Flag NICs not attached to any virtual machine."""
    if row.get("resource_type", "").lower() != "microsoft.network/networkinterfaces":
        return None
    if row.get("virtual_machine") is not None:
        return None  # attached

    region = row.get("region", "westeurope")

    return Finding(
        provider="azure",
        account_id=row["account_id"],
        resource_group=row.get("resource_group"),
        region=region,
        resource_id=row["resource_id"],
        resource_type="Microsoft.Network/networkInterfaces",
        rule_id="azure.nic.orphan",
        severity="medium",
        category="network",
        estimated_monthly_usd=Decimal("0"),  # NICs are free but signal waste
        evidence={
            "private_ip_address": row.get("private_ip_address", ""),
        },
        tags=row.get("tags", {}),
        remediation=(
            "Delete the orphaned network interface. "
            "Confirm it is not required before removal."
        ),
    )


@rule(
    id="azure.snapshot.old",
    severity="medium",
    category="storage",
    description="Managed disk snapshot older than 180 days.",
)
def azure_snapshot_old(row: dict, pricing) -> Optional[Finding]:
    """Flag snapshots more than 180 days old."""
    if row.get("resource_type", "").lower() != "microsoft.compute/snapshots":
        return None

    age = _age_days(str(row.get("time_created") or ""))
    if age is None or age <= 180:
        return None

    size_gb = float(row.get("size_gb") or 0)
    sku = str(row.get("sku") or "Standard_LRS")
    region = row.get("region", "westeurope")

    monthly_cost = pricing.lookup("azure", f"snapshot/{sku}", region) * Decimal(
        str(size_gb)
    )

    return Finding(
        provider="azure",
        account_id=row["account_id"],
        resource_group=row.get("resource_group"),
        region=region,
        resource_id=row["resource_id"],
        resource_type="Microsoft.Compute/snapshots",
        rule_id="azure.snapshot.old",
        severity="medium",
        category="storage",
        estimated_monthly_usd=monthly_cost,
        evidence={
            "age_days": round(age, 1),
            "size_gb": size_gb,
            "sku": sku,
            "time_created": row.get("time_created", ""),
        },
        tags=row.get("tags", {}),
        remediation=(
            "Review and delete snapshots older than 180 days. "
            "Consider a retention policy to automate cleanup."
        ),
    )


@rule(
    id="azure.vm.stopped_with_disks",
    severity="high",
    category="compute",
    description="VM is deallocated but still incurring managed-disk costs.",
)
def azure_vm_stopped_with_disks(row: dict, pricing) -> Optional[Finding]:
    """Flag deallocated VMs that still have attached managed disks."""
    if row.get("resource_type", "").lower() != "microsoft.compute/virtualmachines":
        return None
    if row.get("power_state", "").lower() != "deallocated":
        return None

    disk_ids = row.get("attached_disk_ids") or []
    if not disk_ids:
        return None  # no disks attached

    region = row.get("region", "westeurope")
    vm_size = str(row.get("vm_size") or "")

    # Estimate just the compute cost for a conservative lower-bound on waste
    vm_cost = pricing.lookup("azure", f"virtual_machine/{vm_size}", region)

    return Finding(
        provider="azure",
        account_id=row["account_id"],
        resource_group=row.get("resource_group"),
        region=region,
        resource_id=row["resource_id"],
        resource_type="Microsoft.Compute/virtualMachines",
        rule_id="azure.vm.stopped_with_disks",
        severity="high",
        category="compute",
        estimated_monthly_usd=vm_cost,
        evidence={
            "power_state": row.get("power_state", ""),
            "vm_size": vm_size,
            "attached_disk_count": len(disk_ids),
            "attached_disk_ids": disk_ids[:5],  # truncate for readability
        },
        tags=row.get("tags", {}),
        remediation=(
            "Delete the VM and its managed disks if no longer needed, "
            "or start it if it is required. Deallocated VMs still incur "
            "managed-disk and IP address charges."
        ),
    )


@rule(
    id="azure.aks.idle_nodepool",
    severity="high",
    category="compute",
    description="AKS cluster has an agent pool with zero nodes.",
)
def azure_aks_idle_nodepool(row: dict, pricing) -> Optional[Finding]:
    """Flag AKS clusters that have at least one node pool scaled to 0."""
    if (
        row.get("resource_type", "").lower()
        != "microsoft.containerservice/managedclusters"
    ):
        return None

    profiles = row.get("agent_pool_profiles") or []
    idle_pools = [p for p in profiles if int(p.get("count") or 0) == 0]

    if not idle_pools:
        return None

    region = row.get("region", "westeurope")

    return Finding(
        provider="azure",
        account_id=row["account_id"],
        resource_group=row.get("resource_group"),
        region=region,
        resource_id=row["resource_id"],
        resource_type="Microsoft.ContainerService/managedClusters",
        rule_id="azure.aks.idle_nodepool",
        severity="high",
        category="compute",
        estimated_monthly_usd=Decimal("0"),
        evidence={
            "idle_pool_names": [p["name"] for p in idle_pools],
            "idle_pool_count": len(idle_pools),
            "kubernetes_version": row.get("kubernetes_version", ""),
        },
        tags=row.get("tags", {}),
        remediation=(
            "Remove idle node pools from the AKS cluster or scale them down "
            "to their minimum required count. Consider enabling cluster autoscaler."
        ),
    )


@rule(
    id="azure.asp.oversized_nonprod",
    severity="medium",
    category="compute",
    description="App Service Plan in non-prod RG uses an expensive production-grade SKU.",
)
def azure_asp_oversized_nonprod(row: dict, pricing) -> Optional[Finding]:
    """Flag Premium/Standard App Service Plans in dev/test/stage resource groups."""
    if row.get("resource_type", "").lower() != "microsoft.web/serverfarms":
        return None

    sku_name = str(row.get("sku_name") or "")
    # Flag S1/S2/S3 and any P* (Premium) tier in non-prod RGs
    is_expensive = bool(
        re.match(r"^(S[1-3]|P\d)", sku_name, re.IGNORECASE)
    )
    if not is_expensive:
        return None

    rg = str(row.get("resource_group") or "")
    if not _is_nonprod_rg(rg):
        return None

    region = row.get("region", "westeurope")
    monthly_cost = pricing.lookup("azure", f"app_service_plan/{sku_name}", region)

    return Finding(
        provider="azure",
        account_id=row["account_id"],
        resource_group=row.get("resource_group"),
        region=region,
        resource_id=row["resource_id"],
        resource_type="Microsoft.Web/serverFarms",
        rule_id="azure.asp.oversized_nonprod",
        severity="medium",
        category="compute",
        estimated_monthly_usd=monthly_cost,
        evidence={
            "sku_name": sku_name,
            "sku_tier": row.get("sku_tier", ""),
            "number_of_workers": row.get("number_of_workers", 0),
            "resource_group": rg,
        },
        tags=row.get("tags", {}),
        remediation=(
            f"Downscale the App Service Plan from {sku_name} to B1 or B2 "
            "in non-production environments to reduce costs significantly."
        ),
    )


@rule(
    id="azure.storage.legacy_kind",
    severity="low",
    category="storage",
    description="Storage account uses legacy 'Storage' kind; migrate to StorageV2.",
)
def azure_storage_legacy_kind(row: dict, pricing) -> Optional[Finding]:
    """Flag storage accounts with kind=='Storage' (legacy BlobStorage and Storage)."""
    if row.get("resource_type", "").lower() != "microsoft.storage/storageaccounts":
        return None
    if str(row.get("kind") or "").lower() != "storage":
        return None

    region = row.get("region", "westeurope")

    return Finding(
        provider="azure",
        account_id=row["account_id"],
        resource_group=row.get("resource_group"),
        region=region,
        resource_id=row["resource_id"],
        resource_type="Microsoft.Storage/storageAccounts",
        rule_id="azure.storage.legacy_kind",
        severity="low",
        category="storage",
        estimated_monthly_usd=Decimal("0"),
        evidence={
            "kind": row.get("kind", ""),
            "sku_name": row.get("sku_name", ""),
        },
        tags=row.get("tags", {}),
        remediation=(
            "Migrate the storage account to StorageV2 to unlock hot/cool/archive "
            "tiering and lower per-GB costs. Create a new StorageV2 account and "
            "migrate data using AzCopy."
        ),
    )


@rule(
    id="azure.storage.ragrs_nonprod",
    severity="medium",
    category="storage",
    description="Storage account uses RA-GRS or GRS replication in a non-prod RG.",
)
def azure_storage_ragrs_nonprod(row: dict, pricing) -> Optional[Finding]:
    """Flag RA-GRS/GRS storage accounts in dev/test/stage resource groups."""
    if row.get("resource_type", "").lower() != "microsoft.storage/storageaccounts":
        return None

    sku_name = str(row.get("sku_name") or "").upper()
    if not (sku_name.endswith("_RAGRS") or sku_name.endswith("_GRS")):
        return None

    rg = str(row.get("resource_group") or "")
    if not _is_nonprod_rg(rg):
        return None

    region = row.get("region", "westeurope")

    return Finding(
        provider="azure",
        account_id=row["account_id"],
        resource_group=row.get("resource_group"),
        region=region,
        resource_id=row["resource_id"],
        resource_type="Microsoft.Storage/storageAccounts",
        rule_id="azure.storage.ragrs_nonprod",
        severity="medium",
        category="storage",
        estimated_monthly_usd=Decimal("0"),
        evidence={
            "sku_name": sku_name,
            "kind": row.get("kind", ""),
            "resource_group": rg,
        },
        tags=row.get("tags", {}),
        remediation=(
            f"Downgrade replication from {sku_name} to LRS for non-production "
            "storage accounts. GRS/RA-GRS replication roughly doubles storage costs "
            "and is unnecessary in dev/test/stage environments."
        ),
    )
