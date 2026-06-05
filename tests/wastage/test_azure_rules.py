"""Unit tests for Azure wastage rules.

Each test uses a minimal fixture row and asserts:
  - a Finding is returned (or None) as expected
  - finding_id is a 64-char hex string
  - rule_id, severity, category match the decorator
  - estimated_monthly_usd is a Decimal
  - remediation text is non-empty
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

import backend.app.wastage.rules.azure  # noqa: F401 — side-effect: register rules
from backend.app.wastage.rules import REGISTRY, Finding

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


def make_pricing(return_value: Decimal = Decimal("10.00")):
    """Return a mock pricing module where lookup() always returns *return_value*."""
    mock = MagicMock()
    mock.lookup.return_value = return_value
    return mock


def _base_row(**overrides) -> dict:
    base = {
        "provider": "azure",
        "account_id": "sub-1234",
        "resource_id": "/subscriptions/sub-1234/resourcegroups/rg-test/providers/x/y/z",
        "resource_name": "test-resource",
        "resource_group": "rg-test",
        "region": "westeurope",
        "tags": {},
    }
    base.update(overrides)
    return base


def _assert_finding(finding: Finding, rule_id: str) -> None:
    """Common assertions for every valid Finding."""
    assert finding is not None
    assert isinstance(finding, Finding)
    assert len(finding.finding_id) == 64, "finding_id must be a 64-char hex SHA-256"
    assert finding.rule_id == rule_id
    assert isinstance(finding.estimated_monthly_usd, Decimal)
    assert finding.remediation, "remediation must be non-empty"
    assert finding.provider == "azure"
    assert finding.account_id == "sub-1234"


# ---------------------------------------------------------------------------
# azure.disk.orphan
# ---------------------------------------------------------------------------


def test_disk_orphan_no_managed_by():
    """Unattached disk (managedBy='') should produce a Finding."""
    row = _base_row(
        resource_type="Microsoft.Compute/disks",
        managed_by="",
        size_gb=128,
        sku="Premium_LRS",
    )
    pricing = make_pricing(Decimal("0.1397"))
    finding = REGISTRY["azure.disk.orphan"].fn(row, pricing)

    _assert_finding(finding, "azure.disk.orphan")
    assert finding.severity == "high"
    assert finding.category == "storage"
    assert finding.estimated_monthly_usd == Decimal("0.1397") * Decimal("128")
    assert finding.evidence["size_gb"] == 128
    assert finding.evidence["sku"] == "Premium_LRS"


def test_disk_orphan_with_managed_by():
    """Attached disk (managedBy non-empty) should return None."""
    row = _base_row(
        resource_type="Microsoft.Compute/disks",
        managed_by="/subscriptions/sub-1234/resourceGroups/rg-prod/providers/Microsoft.Compute/virtualMachines/vm-1",
        size_gb=128,
        sku="Premium_LRS",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.disk.orphan"].fn(row, pricing) is None


def test_disk_orphan_wrong_type():
    """Rule should ignore rows of a different resource type."""
    row = _base_row(resource_type="Microsoft.Network/publicIPAddresses")
    pricing = make_pricing()
    assert REGISTRY["azure.disk.orphan"].fn(row, pricing) is None


# ---------------------------------------------------------------------------
# azure.public_ip.unattached
# ---------------------------------------------------------------------------


def test_public_ip_unattached_standard_no_config():
    """Standard IP with no ipConfiguration should be flagged."""
    row = _base_row(
        resource_type="Microsoft.Network/publicIPAddresses",
        sku_name="Standard",
        ip_configuration=None,
        allocation_method="Static",
        ip_address="",
    )
    pricing = make_pricing(Decimal("3.36"))
    finding = REGISTRY["azure.public_ip.unattached"].fn(row, pricing)

    _assert_finding(finding, "azure.public_ip.unattached")
    assert finding.severity == "medium"
    assert finding.category == "network"
    assert finding.estimated_monthly_usd == Decimal("3.36")


def test_public_ip_unattached_with_config():
    """Standard IP with ipConfiguration present should return None."""
    row = _base_row(
        resource_type="Microsoft.Network/publicIPAddresses",
        sku_name="Standard",
        ip_configuration={"id": "/subscriptions/..."},
        allocation_method="Static",
        ip_address="20.0.0.1",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.public_ip.unattached"].fn(row, pricing) is None


def test_public_ip_unattached_basic_sku_ignored():
    """Basic SKU IPs should be ignored by the unattached rule."""
    row = _base_row(
        resource_type="Microsoft.Network/publicIPAddresses",
        sku_name="Basic",
        ip_configuration=None,
        allocation_method="Dynamic",
        ip_address="",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.public_ip.unattached"].fn(row, pricing) is None


# ---------------------------------------------------------------------------
# azure.public_ip.basic_sku
# ---------------------------------------------------------------------------


def test_public_ip_basic_sku_flagged():
    """Basic-SKU IP should be flagged."""
    row = _base_row(
        resource_type="Microsoft.Network/publicIPAddresses",
        sku_name="Basic",
        allocation_method="Dynamic",
        ip_configuration=None,
        ip_address="",
    )
    pricing = make_pricing()
    finding = REGISTRY["azure.public_ip.basic_sku"].fn(row, pricing)

    _assert_finding(finding, "azure.public_ip.basic_sku")
    assert finding.severity == "low"
    assert finding.category == "network"
    assert finding.estimated_monthly_usd == Decimal("0")


def test_public_ip_basic_sku_standard_ignored():
    """Standard-SKU IP should be ignored by this rule."""
    row = _base_row(
        resource_type="Microsoft.Network/publicIPAddresses",
        sku_name="Standard",
        allocation_method="Static",
        ip_configuration=None,
        ip_address="",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.public_ip.basic_sku"].fn(row, pricing) is None


# ---------------------------------------------------------------------------
# azure.nic.orphan
# ---------------------------------------------------------------------------


def test_nic_orphan_no_vm():
    """NIC with no virtualMachine should be flagged."""
    row = _base_row(
        resource_type="Microsoft.Network/networkInterfaces",
        virtual_machine=None,
        private_ip_address="10.0.0.4",
    )
    pricing = make_pricing()
    finding = REGISTRY["azure.nic.orphan"].fn(row, pricing)

    _assert_finding(finding, "azure.nic.orphan")
    assert finding.severity == "medium"
    assert finding.category == "network"


def test_nic_orphan_with_vm():
    """NIC attached to a VM should return None."""
    vm_id = "/subscriptions/sub-1234/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-1"
    row = _base_row(
        resource_type="Microsoft.Network/networkInterfaces",
        virtual_machine={"id": vm_id},
        private_ip_address="10.0.0.4",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.nic.orphan"].fn(row, pricing) is None


# ---------------------------------------------------------------------------
# azure.snapshot.old
# ---------------------------------------------------------------------------


def test_snapshot_old_over_180_days():
    """Snapshot older than 180 days should be flagged."""
    row = _base_row(
        resource_type="Microsoft.Compute/snapshots",
        time_created="2020-01-01T00:00:00",
        size_gb=256,
        sku="Standard_LRS",
    )
    pricing = make_pricing(Decimal("0.045"))
    finding = REGISTRY["azure.snapshot.old"].fn(row, pricing)

    _assert_finding(finding, "azure.snapshot.old")
    assert finding.severity == "medium"
    assert finding.category == "storage"
    assert finding.evidence["age_days"] > 180
    assert finding.estimated_monthly_usd == Decimal("0.045") * Decimal("256")


def test_snapshot_old_recent():
    """Snapshot created 10 days ago should return None."""
    from datetime import datetime as _dt
    from datetime import timedelta
    from datetime import timezone as _tz

    recent_ts = (_dt.now(_tz.utc) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S")
    row = _base_row(
        resource_type="Microsoft.Compute/snapshots",
        time_created=recent_ts,
        size_gb=64,
        sku="Standard_LRS",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.snapshot.old"].fn(row, pricing) is None


def test_snapshot_old_no_timestamp():
    """Snapshot with missing timestamp should return None (cannot determine age)."""
    row = _base_row(
        resource_type="Microsoft.Compute/snapshots",
        time_created="",
        size_gb=64,
        sku="Standard_LRS",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.snapshot.old"].fn(row, pricing) is None


# ---------------------------------------------------------------------------
# azure.vm.stopped_with_disks
# ---------------------------------------------------------------------------


def test_vm_stopped_with_disks():
    """Deallocated VM with attached disks should be flagged."""
    row = _base_row(
        resource_type="Microsoft.Compute/virtualMachines",
        power_state="deallocated",
        vm_size="Standard_D2_v3",
        attached_disk_ids=["/subscriptions/sub-1234/resourceGroups/rg/providers/Microsoft.Compute/disks/disk-1"],
    )
    pricing = make_pricing(Decimal("96.36"))
    finding = REGISTRY["azure.vm.stopped_with_disks"].fn(row, pricing)

    _assert_finding(finding, "azure.vm.stopped_with_disks")
    assert finding.severity == "high"
    assert finding.category == "compute"
    assert finding.evidence["power_state"] == "deallocated"
    assert finding.evidence["attached_disk_count"] == 1


def test_vm_stopped_no_disks():
    """Deallocated VM with no attached disks should return None."""
    row = _base_row(
        resource_type="Microsoft.Compute/virtualMachines",
        power_state="deallocated",
        vm_size="Standard_D2_v3",
        attached_disk_ids=[],
    )
    pricing = make_pricing()
    assert REGISTRY["azure.vm.stopped_with_disks"].fn(row, pricing) is None


def test_vm_running_ignored():
    """Running VM should return None regardless of disk count."""
    row = _base_row(
        resource_type="Microsoft.Compute/virtualMachines",
        power_state="running",
        vm_size="Standard_D2_v3",
        attached_disk_ids=["disk-1"],
    )
    pricing = make_pricing()
    assert REGISTRY["azure.vm.stopped_with_disks"].fn(row, pricing) is None


# ---------------------------------------------------------------------------
# azure.aks.idle_nodepool
# ---------------------------------------------------------------------------


def test_aks_idle_nodepool():
    """AKS cluster with a zero-count node pool should be flagged."""
    row = _base_row(
        resource_type="Microsoft.ContainerService/managedClusters",
        agent_pool_profiles=[
            {"name": "nodepool1", "count": 0, "vm_size": "Standard_D2_v3", "mode": "System"},
            {"name": "nodepool2", "count": 3, "vm_size": "Standard_D4_v3", "mode": "User"},
        ],
        kubernetes_version="1.29.0",
    )
    pricing = make_pricing()
    finding = REGISTRY["azure.aks.idle_nodepool"].fn(row, pricing)

    _assert_finding(finding, "azure.aks.idle_nodepool")
    assert finding.severity == "high"
    assert finding.category == "compute"
    assert finding.evidence["idle_pool_names"] == ["nodepool1"]
    assert finding.evidence["idle_pool_count"] == 1


def test_aks_all_pools_active():
    """AKS cluster with all pools having nodes should return None."""
    row = _base_row(
        resource_type="Microsoft.ContainerService/managedClusters",
        agent_pool_profiles=[
            {"name": "nodepool1", "count": 3, "vm_size": "Standard_D2_v3", "mode": "System"},
        ],
        kubernetes_version="1.29.0",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.aks.idle_nodepool"].fn(row, pricing) is None


# ---------------------------------------------------------------------------
# azure.asp.oversized_nonprod
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sku", ["S1", "S2", "S3", "P1v2", "P2v3"])
def test_asp_oversized_nonprod_flagged(sku: str):
    """S*/P* ASP in a dev/test/stage RG should be flagged."""
    row = _base_row(
        resource_type="Microsoft.Web/serverFarms",
        sku_name=sku,
        sku_tier="Standard" if sku.startswith("S") else "PremiumV2",
        number_of_workers=1,
        resource_group="rg-dev",
    )
    pricing = make_pricing(Decimal("69.35"))
    finding = REGISTRY["azure.asp.oversized_nonprod"].fn(row, pricing)

    _assert_finding(finding, "azure.asp.oversized_nonprod")
    assert finding.severity == "medium"
    assert finding.category == "compute"


def test_asp_oversized_prod_rg_ignored():
    """Same expensive SKU in a prod RG should NOT be flagged."""
    row = _base_row(
        resource_type="Microsoft.Web/serverFarms",
        sku_name="S2",
        sku_tier="Standard",
        number_of_workers=1,
        resource_group="rg-production",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.asp.oversized_nonprod"].fn(row, pricing) is None


def test_asp_cheap_sku_nonprod_ignored():
    """B1/B2 plans in non-prod should NOT be flagged."""
    row = _base_row(
        resource_type="Microsoft.Web/serverFarms",
        sku_name="B1",
        sku_tier="Basic",
        number_of_workers=1,
        resource_group="rg-dev",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.asp.oversized_nonprod"].fn(row, pricing) is None


# ---------------------------------------------------------------------------
# azure.storage.legacy_kind
# ---------------------------------------------------------------------------


def test_storage_legacy_kind():
    """Storage account with kind='Storage' should be flagged."""
    row = _base_row(
        resource_type="Microsoft.Storage/storageAccounts",
        kind="Storage",
        sku_name="Standard_LRS",
        sku_tier="Standard",
        access_tier="",
    )
    pricing = make_pricing()
    finding = REGISTRY["azure.storage.legacy_kind"].fn(row, pricing)

    _assert_finding(finding, "azure.storage.legacy_kind")
    assert finding.severity == "low"
    assert finding.category == "storage"
    assert finding.estimated_monthly_usd == Decimal("0")


def test_storage_v2_not_flagged():
    """StorageV2 account should not be flagged by legacy-kind rule."""
    row = _base_row(
        resource_type="Microsoft.Storage/storageAccounts",
        kind="StorageV2",
        sku_name="Standard_LRS",
        sku_tier="Standard",
        access_tier="Hot",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.storage.legacy_kind"].fn(row, pricing) is None


# ---------------------------------------------------------------------------
# azure.storage.ragrs_nonprod
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sku", ["Standard_RAGRS", "Standard_GRS"])
def test_storage_ragrs_nonprod_flagged(sku: str):
    """RA-GRS/GRS storage in dev/test RG should be flagged."""
    row = _base_row(
        resource_type="Microsoft.Storage/storageAccounts",
        kind="StorageV2",
        sku_name=sku,
        sku_tier="Standard",
        access_tier="Hot",
        resource_group="rg-test",
    )
    pricing = make_pricing()
    finding = REGISTRY["azure.storage.ragrs_nonprod"].fn(row, pricing)

    _assert_finding(finding, "azure.storage.ragrs_nonprod")
    assert finding.severity == "medium"
    assert finding.category == "storage"


def test_storage_ragrs_prod_rg_ignored():
    """RA-GRS storage in a prod RG should NOT be flagged."""
    row = _base_row(
        resource_type="Microsoft.Storage/storageAccounts",
        kind="StorageV2",
        sku_name="Standard_RAGRS",
        sku_tier="Standard",
        access_tier="Hot",
        resource_group="rg-production",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.storage.ragrs_nonprod"].fn(row, pricing) is None


def test_storage_lrs_nonprod_ignored():
    """LRS storage in a dev RG should NOT be flagged (cheap replication)."""
    row = _base_row(
        resource_type="Microsoft.Storage/storageAccounts",
        kind="StorageV2",
        sku_name="Standard_LRS",
        sku_tier="Standard",
        access_tier="Hot",
        resource_group="rg-dev",
    )
    pricing = make_pricing()
    assert REGISTRY["azure.storage.ragrs_nonprod"].fn(row, pricing) is None


# ---------------------------------------------------------------------------
# Registry presence check
# ---------------------------------------------------------------------------


def test_all_azure_rules_registered():
    """All 10 Azure rules must be present in the REGISTRY after import."""
    expected_rules = {
        "azure.disk.orphan",
        "azure.public_ip.unattached",
        "azure.public_ip.basic_sku",
        "azure.nic.orphan",
        "azure.snapshot.old",
        "azure.vm.stopped_with_disks",
        "azure.aks.idle_nodepool",
        "azure.asp.oversized_nonprod",
        "azure.storage.legacy_kind",
        "azure.storage.ragrs_nonprod",
    }
    for rule_id in expected_rules:
        assert rule_id in REGISTRY, f"Rule {rule_id!r} is not registered"
