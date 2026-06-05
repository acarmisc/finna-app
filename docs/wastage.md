# Resource Wastage

Rule-based, deterministic detection of unused and orphaned cloud resources.

## Rule Catalog

All rules live in `backend/app/wastage/rules/` and are registered via the `@rule` decorator.
Rules are loaded automatically when the API starts; call `GET /api/v1/wastage/rules` to see
the live catalog.

### Azure rules (Phase 4 / Agent B)

| Rule ID | Severity | Category | Description |
|---------|----------|----------|-------------|
| `azure.disk.orphan` | high | storage | Managed disk with no `managedBy` — not attached to any VM |
| `azure.public_ip.unattached` | medium | network | Standard-SKU public IP with no `ipConfiguration` |
| `azure.public_ip.basic_sku` | low | network | Basic-SKU public IP (deprecated by Azure, retire before Sept 2025) |
| `azure.nic.orphan` | medium | network | NIC with no `virtualMachine` association |
| `azure.snapshot.old` | low | storage | Snapshot older than 180 days |
| `azure.vm.stopped_with_disks` | high | compute | Deallocated VM still paying for attached managed disks |
| `azure.aks.idle_nodepool` | high | compute | AKS node pool with `count == 0` (still billed for system pool) |
| `azure.asp.oversized_nonprod` | medium | compute | App Service Plan on S/P tier in a dev/test/stage resource group |
| `azure.storage.legacy_kind` | low | storage | Storage account `kind == 'Storage'` (non-V2, limited features) |
| `azure.storage.ragrs_nonprod` | low | storage | RAGRS/GRS replication in a dev/stage resource group (overkill) |

Prices are sourced from `data/prices/azure_list_prices.json` (West Europe, EUR).

## How to Add a Rule

1. Create (or open) a file under `backend/app/wastage/rules/`.
2. Import and apply the `@rule` decorator:

```python
from backend.app.wastage.rules import rule, Finding
from backend.app.wastage import pricing

@rule(
    id="azure.redis.c0_nonprod",
    severity="low",
    category="database",
    description="Redis Cache C0 tier in a non-production resource group",
)
def azure_redis_c0_nonprod(row: dict, pricing) -> Finding | None:
    if row.get("sku_name") != "C0":
        return None
    rg = (row.get("resource_group") or "").lower()
    if not any(env in rg for env in ("dev", "test", "stage")):
        return None
    cost = pricing.lookup("azure", "redis/C0", row.get("region", "westeurope"))
    return Finding(
        provider="azure",
        account_id=row["account_id"],
        resource_group=row.get("resource_group"),
        region=row.get("region"),
        resource_id=row["resource_id"],
        resource_type="Microsoft.Cache/Redis",
        rule_id="azure.redis.c0_nonprod",
        severity="low",
        category="database",
        estimated_monthly_usd=cost,
        evidence={"sku": "C0"},
        remediation="Downgrade to Basic C0 or delete the cache if unused.",
    )
```

3. Add a unit test in `tests/wastage/test_rules.py` — one fixture row, assert the Finding fields.
4. Add a price entry in `data/prices/azure_list_prices.json` if the SKU is missing.
5. The rule is automatically registered and visible in `GET /api/v1/wastage/rules` on next startup.

**Rule function signature:** `(inventory_row: dict, pricing_module) -> Optional[Finding]`

- Return `None` if the resource is not wasteful.
- The `finding_id` is auto-derived as SHA-256(`provider:resource_id:rule_id`) — do not set it manually.

## Price Refresh Process

Public list prices are stored as plain JSON files in `data/prices/`.  
See [`data/prices/README.md`](../data/prices/README.md) for the full refresh instructions.

Short version:

1. Open the relevant Azure/AWS/GCP pricing page or use the provider CLI to dump current prices.
2. Edit the JSON file, keeping the same structure: `{ "<region>": { "<sku>": <monthly_usd> } }`.
3. Call `pricing.reload()` in your local shell (or restart the API) to pick up changes.
4. Run `pytest tests/wastage/` to verify no golden-output tests break.
5. Commit with message `chore(prices): refresh <provider> list prices <YYYY-MM-DD>`.

> **Disclaimer**: estimates are based on list prices and do not account for reservations,
> savings plans, or negotiated discounts. Always verify in Cost Analysis before acting.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/wastage` | List findings (filters: `provider`, `severity`, `rule_id`, `status`, `account_id`; pagination: `limit`, `offset`) |
| GET | `/api/v1/wastage/summary` | Findings grouped by category with summed savings |
| GET | `/api/v1/wastage/rules` | Live rule catalog |
| GET | `/api/v1/wastage/scans` | Scan run history |
| GET | `/api/v1/wastage/{finding_id}` | Single finding detail |
| POST | `/api/v1/wastage/{finding_id}/ack` | Acknowledge finding |
| POST | `/api/v1/wastage/{finding_id}/resolve` | Mark as resolved |
| POST | `/api/v1/wastage/{finding_id}/ignore` | Ignore with optional reason (body: `{"reason": "..."}`) |
| POST | `/api/v1/wastage/scan` | Enqueue a scan (body: `{"provider": "azure"}`) |

All endpoints require a JWT bearer token (`Authorization: Bearer <token>`).
