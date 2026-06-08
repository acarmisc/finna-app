"""Wastage rule engine: registry, decorator, and Finding dataclass.

Usage — defining a rule::

    from backend.app.wastage.rules import rule, Finding

    @rule(id="azure.disk.orphan", severity="high", category="storage")
    def azure_disk_orphan(inventory_row: dict, pricing) -> Optional[Finding]:
        if inventory_row.get("managed_by"):
            return None
        size_gb = inventory_row.get("size_gb", 0)
        sku = inventory_row.get("sku", "Premium_LRS")
        region = inventory_row.get("region", "westeurope")
        cost = pricing.lookup("azure", f"managed_disk/{sku}", region) * size_gb
        return Finding(
            provider="azure",
            account_id=inventory_row["account_id"],
            resource_group=inventory_row.get("resource_group"),
            region=region,
            resource_id=inventory_row["resource_id"],
            resource_type="Microsoft.Compute/disks",
            rule_id="azure.disk.orphan",
            severity="high",
            category="storage",
            estimated_monthly_usd=cost,
            evidence={"size_gb": size_gb, "sku": sku},
            remediation="Delete the orphaned managed disk or re-attach it to a VM.",
        )

The REGISTRY maps rule_id -> Rule namedtuple so Phase 4/6 can iterate all rules.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, NamedTuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Finding dataclass
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """A single wastage finding produced by a rule.

    ``finding_id`` is auto-derived from (provider, resource_id, rule_id) if
    not supplied — matching the hash used by the runner's upsert logic.
    """

    provider: str
    account_id: str
    resource_id: str
    resource_type: str
    rule_id: str
    severity: str  # critical | high | medium | low | info
    category: str  # compute | storage | network | database | other
    remediation: str

    # Optional location fields
    resource_group: str | None = None
    region: str | None = None

    # Cost estimate (Decimal so callers can sum without float rounding)
    estimated_monthly_usd: Decimal = field(default_factory=lambda: Decimal("0"))

    # Free-form evidence payload persisted as JSONB
    evidence: dict[str, Any] = field(default_factory=dict)

    # Tags forwarded from inventory row
    tags: dict[str, str] = field(default_factory=dict)

    # Derived / settable
    finding_id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.finding_id:
            self.finding_id = _derive_finding_id(
                self.provider, self.resource_id, self.rule_id
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict suitable for DB upsert or JSON serialisation."""
        return {
            "finding_id": self.finding_id,
            "provider": self.provider,
            "account_id": self.account_id,
            "resource_group": self.resource_group,
            "region": self.region,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "category": self.category,
            "estimated_monthly_usd": self.estimated_monthly_usd,
            "evidence": self.evidence,
            "tags": self.tags,
        }


def _derive_finding_id(provider: str, resource_id: str, rule_id: str) -> str:
    """Stable SHA-256 fingerprint for (provider, resource_id, rule_id)."""
    raw = f"{provider}:{resource_id}:{rule_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

RuleFn = Callable[[dict, Any], Finding | None]


class Rule(NamedTuple):
    """Metadata + callable for a registered wastage rule."""

    id: str
    severity: str
    category: str
    description: str
    fn: RuleFn


#: Global rule registry.  Populated by the ``@rule`` decorator.
REGISTRY: dict[str, Rule] = {}


def rule(
    id: str,
    severity: str,
    category: str,
    description: str = "",
) -> Callable[[RuleFn], RuleFn]:
    """Decorator that registers a rule function in REGISTRY.

    Args:
        id: Stable dot-separated rule identifier, e.g. ``"azure.disk.orphan"``.
        severity: ``critical | high | medium | low | info``.
        category: ``compute | storage | network | database | other``.
        description: Human-readable one-liner shown in the API rule catalog.

    The decorated function is returned unchanged so it can still be called
    directly (useful in tests).
    """

    def decorator(fn: RuleFn) -> RuleFn:
        if id in REGISTRY:
            logger.warning("rule %r already registered — overwriting", id)
        REGISTRY[id] = Rule(
            id=id,
            severity=severity,
            category=category,
            description=description or fn.__doc__ or "",
            fn=fn,
        )
        return fn

    return decorator
