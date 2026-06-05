"""Integration tests for extractors/inventory/azure_inventory.py.

Uses unittest.mock to stub the ResourceGraphClient so no real Azure
credentials are needed.  The tests verify:
  - normaliser output shape for each resource type
  - pagination handling
  - error-resilience (bad rows don't abort the whole stream)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from extractors.inventory.azure_inventory import (
    _normalize_aks,
    _normalize_asp,
    _normalize_disk,
    _normalize_nic,
    _normalize_public_ip,
    _normalize_redis,
    _normalize_snapshot,
    _normalize_storage,
    _normalize_vm,
    stream_inventory,
)

# ---------------------------------------------------------------------------
# Normaliser unit tests
# ---------------------------------------------------------------------------


def _base(overrides: dict | None = None) -> dict:
    base: dict[str, Any] = {
        "id": "/subscriptions/sub-abc/resourceGroups/rg-prod/providers/Microsoft.Compute/disks/disk-1",
        "name": "disk-1",
        "resourceGroup": "rg-prod",
        "location": "westeurope",
        "subscriptionId": "sub-abc",
        "tags": {"env": "prod"},
    }
    if overrides:
        base.update(overrides)
    return base


def test_normalize_disk():
    row = _base({
        "managedBy": "", "diskSizeGb": 128, "sku": "Premium_LRS",
        "diskState": "Unattached", "timeCreated": "2024-01-01T00:00:00",
    })
    out = _normalize_disk(row)
    assert out["resource_type"] == "Microsoft.Compute/disks"
    assert out["managed_by"] == ""
    assert out["size_gb"] == 128.0
    assert out["sku"] == "Premium_LRS"
    assert out["provider"] == "azure"
    assert out["account_id"] == "sub-abc"
    assert out["tags"] == {"env": "prod"}


def test_normalize_public_ip_unattached():
    row = _base({
        "id": "/subscriptions/sub-abc/resourceGroups/rg-prod/providers/Microsoft.Network/publicIPAddresses/pip-1",
        "skuName": "Standard",
        "allocationMethod": "Static",
        "ipConfiguration": None,
        "ipAddress": "",
    })
    out = _normalize_public_ip(row)
    assert out["resource_type"] == "Microsoft.Network/publicIPAddresses"
    assert out["sku_name"] == "Standard"
    assert out["ip_configuration"] is None


def test_normalize_public_ip_attached():
    row = _base({
        "skuName": "Standard",
        "allocationMethod": "Static",
        "ipConfiguration": {"id": "/subscriptions/..."},
        "ipAddress": "20.0.0.1",
    })
    out = _normalize_public_ip(row)
    assert out["ip_configuration"] is not None


def test_normalize_nic_orphan():
    row = _base({
        "id": "/subscriptions/sub-abc/resourceGroups/rg/providers/Microsoft.Network/networkInterfaces/nic-1",
        "virtualMachine": None,
        "privateIpAddress": "10.0.0.5",
    })
    out = _normalize_nic(row)
    assert out["resource_type"] == "Microsoft.Network/networkInterfaces"
    assert out["virtual_machine"] is None


def test_normalize_snapshot():
    row = _base({
        "id": "/subscriptions/sub-abc/resourceGroups/rg/providers/Microsoft.Compute/snapshots/snap-1",
        "diskSizeGb": 64,
        "sku": "Standard_LRS",
        "timeCreated": "2020-01-01T00:00:00",
    })
    out = _normalize_snapshot(row)
    assert out["resource_type"] == "Microsoft.Compute/snapshots"
    assert out["size_gb"] == 64.0
    assert out["time_created"] == "2020-01-01T00:00:00"


def test_normalize_vm_deallocated():
    row = _base({
        "id": "/subscriptions/sub-abc/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-1",
        "vmSize": "Standard_D2_v3",
        "powerState": "PowerState/deallocated",
        "osDiskId": "/subscriptions/sub-abc/resourceGroups/rg/providers/Microsoft.Compute/disks/os-disk-1",
        "dataDisks": [],
    })
    out = _normalize_vm(row)
    assert out["resource_type"] == "Microsoft.Compute/virtualMachines"
    assert out["power_state"] == "deallocated"
    assert len(out["attached_disk_ids"]) == 1


def test_normalize_aks():
    row = _base({
        "id": "/subscriptions/sub-abc/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/aks-1",
        "agentPoolProfiles": [
            {"name": "nodepool1", "count": 0, "vmSize": "Standard_D2_v3", "mode": "System"},
        ],
        "kubernetesVersion": "1.29.0",
    })
    out = _normalize_aks(row)
    assert out["resource_type"] == "Microsoft.ContainerService/managedClusters"
    assert len(out["agent_pool_profiles"]) == 1
    assert out["agent_pool_profiles"][0]["count"] == 0


def test_normalize_asp():
    row = _base({
        "id": "/subscriptions/sub-abc/resourceGroups/rg-dev/providers/Microsoft.Web/serverFarms/asp-1",
        "resourceGroup": "rg-dev",
        "skuName": "S2",
        "skuTier": "Standard",
        "numberOfWorkers": 1,
    })
    out = _normalize_asp(row)
    assert out["resource_type"] == "Microsoft.Web/serverFarms"
    assert out["sku_name"] == "S2"
    assert out["resource_group"] == "rg-dev"


def test_normalize_storage():
    row = _base({
        "id": "/subscriptions/sub-abc/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/st1",
        "kind": "StorageV2",
        "skuName": "Standard_RAGRS",
        "skuTier": "Standard",
        "accessTier": "Hot",
    })
    out = _normalize_storage(row)
    assert out["resource_type"] == "Microsoft.Storage/storageAccounts"
    assert out["kind"] == "StorageV2"
    assert out["sku_name"] == "Standard_RAGRS"


def test_normalize_redis():
    row = _base({
        "id": "/subscriptions/sub-abc/resourceGroups/rg/providers/Microsoft.Cache/Redis/redis-1",
        "skuName": "Standard",
        "skuFamily": "C",
        "skuCapacity": 1,
    })
    out = _normalize_redis(row)
    assert out["resource_type"] == "Microsoft.Cache/Redis"
    assert out["sku_name"] == "Standard"
    assert out["sku_capacity"] == 1


# ---------------------------------------------------------------------------
# stream_inventory integration tests (mocked ResourceGraphClient)
# ---------------------------------------------------------------------------


def _make_rg_result(data: list[dict], skip_token: str | None = None):
    result = MagicMock()
    result.data = data
    result.skip_token = skip_token
    return result


def _disk_row() -> dict:
    return {
        "id": "/subscriptions/sub-abc/resourceGroups/rg-prod/providers/Microsoft.Compute/disks/disk-1",
        "name": "disk-1",
        "resourceGroup": "rg-prod",
        "location": "westeurope",
        "subscriptionId": "sub-abc",
        "tags": {},
        "managedBy": "",
        "diskSizeGb": 128,
        "sku": "Premium_LRS",
        "diskState": "Unattached",
        "timeCreated": "2024-01-01T00:00:00",
    }


@patch("extractors.inventory.azure_inventory._build_resource_graph_client")
def test_stream_inventory_yields_disk(mock_build_client):
    """stream_inventory should yield at least one disk row."""
    mock_client = MagicMock()

    # Only the disks query returns data; all others return empty
    def _resources(request):
        kql = request.query
        if "microsoft.compute/disks" in kql.lower():
            return _make_rg_result([_disk_row()])
        return _make_rg_result([])

    mock_client.resources.side_effect = _resources
    mock_build_client.return_value = mock_client

    rows = list(stream_inventory(subscription_ids=["sub-abc"]))
    disk_rows = [r for r in rows if r["resource_type"] == "Microsoft.Compute/disks"]

    assert len(disk_rows) == 1
    row = disk_rows[0]
    assert row["provider"] == "azure"
    assert row["account_id"] == "sub-abc"
    assert row["managed_by"] == ""
    assert row["size_gb"] == 128.0


@patch("extractors.inventory.azure_inventory._build_resource_graph_client")
def test_stream_inventory_pagination(mock_build_client):
    """Paginated results (skip_token) should be fully collected."""
    mock_client = MagicMock()

    _sub = "/subscriptions/sub-abc/resourceGroups/rg/providers/Microsoft.Compute/disks"
    page1_disk = dict(_disk_row(), id=f"{_sub}/disk-1")
    page2_disk = dict(_disk_row(), id=f"{_sub}/disk-2", name="disk-2")

    call_count = {"disks": 0}

    def _resources(request):
        kql = request.query
        if "microsoft.compute/disks" in kql.lower():
            call_count["disks"] += 1
            if call_count["disks"] == 1:
                return _make_rg_result([page1_disk], skip_token="token-abc")
            else:
                return _make_rg_result([page2_disk])
        return _make_rg_result([])

    mock_client.resources.side_effect = _resources
    mock_build_client.return_value = mock_client

    rows = list(stream_inventory(subscription_ids=["sub-abc"]))
    disk_rows = [r for r in rows if r["resource_type"] == "Microsoft.Compute/disks"]

    assert len(disk_rows) == 2
    names = {r["resource_name"] for r in disk_rows}
    assert names == {"disk-1", "disk-2"}


@patch("extractors.inventory.azure_inventory._build_resource_graph_client")
def test_stream_inventory_query_error_continues(mock_build_client):
    """If one resource-type query fails, stream_inventory should continue with others."""
    mock_client = MagicMock()

    call_count = {"calls": 0}

    def _resources(request):
        kql = request.query
        call_count["calls"] += 1
        if "microsoft.compute/disks" in kql.lower():
            raise RuntimeError("simulated API error for disks")
        if "microsoft.network/publicipaddresses" in kql.lower():
            pip_row = {
                "id": "/subscriptions/sub-abc/resourceGroups/rg/providers/Microsoft.Network/publicIPAddresses/pip-1",
                "name": "pip-1",
                "resourceGroup": "rg",
                "location": "westeurope",
                "subscriptionId": "sub-abc",
                "tags": {},
                "skuName": "Standard",
                "allocationMethod": "Static",
                "ipConfiguration": None,
                "ipAddress": "",
            }
            return _make_rg_result([pip_row])
        return _make_rg_result([])

    mock_client.resources.side_effect = _resources
    mock_build_client.return_value = mock_client

    rows = list(stream_inventory(subscription_ids=["sub-abc"]))

    # Disks failed but public IPs should still be present
    pip_rows = [r for r in rows if r["resource_type"] == "Microsoft.Network/publicIPAddresses"]
    assert len(pip_rows) == 1


@patch("extractors.inventory.azure_inventory._build_resource_graph_client")
def test_stream_inventory_empty_subscriptions(mock_build_client):
    """Passing empty subscription_ids should yield nothing and not call the API."""
    rows = list(stream_inventory(subscription_ids=[]))
    mock_build_client.assert_not_called()
    assert rows == []
