"""Unit tests for the wastage rule engine (registry, decorator, Finding).

Tests are pure-Python — no database, no network, no cloud credentials.
Each test registers a fresh rule or tests an existing one in isolation.

Run with::

    pytest tests/wastage/test_rules.py -v
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Optional
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pricing(price: float = 0.0) -> MagicMock:
    """Return a mock pricing object whose lookup() always returns *price*."""
    pricing = MagicMock()
    pricing.lookup.return_value = Decimal(str(price))
    return pricing


# ---------------------------------------------------------------------------
# Finding dataclass
# ---------------------------------------------------------------------------


class TestFinding:
    def test_finding_id_auto_derived(self):
        from backend.app.wastage.rules import Finding

        f = Finding(
            provider="azure",
            account_id="sub-001",
            resource_id="/subscriptions/sub-001/providers/disks/disk-01",
            resource_type="Microsoft.Compute/disks",
            rule_id="azure.disk.orphan",
            severity="high",
            category="storage",
            remediation="Delete the disk.",
        )
        raw = "azure:/subscriptions/sub-001/providers/disks/disk-01:azure.disk.orphan"
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert f.finding_id == expected

    def test_finding_id_explicit(self):
        from backend.app.wastage.rules import Finding

        f = Finding(
            provider="azure",
            account_id="sub-001",
            resource_id="r1",
            resource_type="T",
            rule_id="test.rule",
            severity="low",
            category="other",
            remediation=".",
            finding_id="my-custom-id",
        )
        assert f.finding_id == "my-custom-id"

    def test_to_dict_keys(self):
        from backend.app.wastage.rules import Finding

        f = Finding(
            provider="gcp",
            account_id="proj-001",
            resource_id="res-1",
            resource_type="compute#disk",
            rule_id="gcp.disk.orphan",
            severity="medium",
            category="storage",
            remediation="Remove disk.",
            estimated_monthly_usd=Decimal("12.50"),
            evidence={"size_gb": 100},
        )
        d = f.to_dict()
        assert d["finding_id"] == f.finding_id
        assert d["estimated_monthly_usd"] == Decimal("12.50")
        assert d["evidence"] == {"size_gb": 100}
        assert d["provider"] == "gcp"

    def test_finding_defaults(self):
        from backend.app.wastage.rules import Finding

        f = Finding(
            provider="aws",
            account_id="123",
            resource_id="vol-1",
            resource_type="AWS::EC2::Volume",
            rule_id="aws.ebs.unattached",
            severity="medium",
            category="storage",
            remediation="Delete the volume.",
        )
        assert f.estimated_monthly_usd == Decimal("0")
        assert f.evidence == {}
        assert f.tags == {}
        assert f.resource_group is None
        assert f.region is None


# ---------------------------------------------------------------------------
# @rule decorator & REGISTRY
# ---------------------------------------------------------------------------


class TestRegistry:
    def setup_method(self):
        """Save and restore REGISTRY around each test so they don't bleed."""
        from backend.app.wastage import rules as rules_module

        self._orig = dict(rules_module.REGISTRY)

    def teardown_method(self):
        from backend.app.wastage import rules as rules_module

        rules_module.REGISTRY.clear()
        rules_module.REGISTRY.update(self._orig)

    def test_decorator_registers_rule(self):
        from backend.app.wastage.rules import REGISTRY, Finding, rule

        @rule(id="test.trivial", severity="low", category="other", description="Trivial test rule.")
        def trivial_rule(inventory_row: dict, pricing) -> Optional[Finding]:
            """Always fires."""
            return Finding(
                provider="test",
                account_id="acct-1",
                resource_id="res-1",
                resource_type="TestResource",
                rule_id="test.trivial",
                severity="low",
                category="other",
                remediation="No action needed — this is a test.",
            )

        assert "test.trivial" in REGISTRY
        entry = REGISTRY["test.trivial"]
        assert entry.id == "test.trivial"
        assert entry.severity == "low"
        assert entry.category == "other"
        assert entry.description == "Trivial test rule."

    def test_decorator_preserves_callable(self):
        from backend.app.wastage.rules import Finding, rule

        @rule(id="test.callable", severity="info", category="compute")
        def my_rule(inventory_row: dict, pricing) -> Optional[Finding]:
            return None

        # The decorated function is still directly callable
        result = my_rule({}, _make_pricing())
        assert result is None

    def test_rule_fires_and_returns_finding(self):
        from backend.app.wastage.rules import Finding, rule

        @rule(id="test.fires", severity="high", category="storage")
        def disk_rule(inventory_row: dict, pricing) -> Optional[Finding]:
            if inventory_row.get("managed_by"):
                return None
            cost = pricing.lookup("azure", "managed_disk/Premium_LRS", "westeurope") * Decimal(
                str(inventory_row.get("size_gb", 0))
            )
            return Finding(
                provider="azure",
                account_id=inventory_row["account_id"],
                resource_id=inventory_row["resource_id"],
                resource_type="Microsoft.Compute/disks",
                rule_id="test.fires",
                severity="high",
                category="storage",
                remediation="Delete the orphaned disk.",
                estimated_monthly_usd=cost,
                evidence={"size_gb": inventory_row.get("size_gb")},
            )

        pricing = _make_pricing(price=0.1397)
        row = {
            "account_id": "sub-001",
            "resource_id": "/disks/disk-01",
            "managed_by": None,
            "size_gb": 128,
        }
        finding = disk_rule(row, pricing)
        assert finding is not None
        assert finding.rule_id == "test.fires"
        assert finding.estimated_monthly_usd == Decimal("0.1397") * 128
        assert finding.evidence["size_gb"] == 128
        pricing.lookup.assert_called_once_with("azure", "managed_disk/Premium_LRS", "westeurope")

    def test_rule_returns_none_when_no_match(self):
        from backend.app.wastage.rules import Finding, rule

        @rule(id="test.no_match", severity="medium", category="network")
        def ip_rule(inventory_row: dict, pricing) -> Optional[Finding]:
            if not inventory_row.get("attached"):
                return Finding(
                    provider="azure",
                    account_id="sub-1",
                    resource_id=inventory_row["id"],
                    resource_type="Microsoft.Network/publicIPAddresses",
                    rule_id="test.no_match",
                    severity="medium",
                    category="network",
                    remediation="Delete the unattached IP.",
                )
            return None

        result = ip_rule({"id": "pip-01", "attached": True}, _make_pricing())
        assert result is None

    def test_registry_description_falls_back_to_docstring(self):
        from backend.app.wastage.rules import REGISTRY, rule

        @rule(id="test.docstring", severity="low", category="other")
        def rule_with_docstring(inventory_row: dict, pricing):
            """This is the docstring description."""
            return None

        assert REGISTRY["test.docstring"].description == "This is the docstring description."

    def test_rule_fn_stored_is_original(self):
        from backend.app.wastage.rules import REGISTRY, rule

        @rule(id="test.fn_identity", severity="low", category="other")
        def my_fn(inventory_row: dict, pricing):
            return None

        assert REGISTRY["test.fn_identity"].fn is my_fn


# ---------------------------------------------------------------------------
# Pricing integration (uses real catalog files)
# ---------------------------------------------------------------------------


class TestPricing:
    def setup_method(self):
        from backend.app.wastage import pricing

        pricing.reload()

    def test_azure_vm_lookup(self):
        from backend.app.wastage.pricing import lookup

        price = lookup("azure", "virtual_machine/Standard_D2_v3", "westeurope")
        assert price > Decimal("0"), "Expected non-zero Azure VM price"

    def test_azure_disk_lookup(self):
        from backend.app.wastage.pricing import lookup

        price = lookup("azure", "managed_disk/Premium_LRS", "westeurope")
        assert price > Decimal("0")

    def test_aws_ebs_lookup(self):
        from backend.app.wastage.pricing import lookup

        price = lookup("aws", "ebs/gp3", "eu-west-1")
        assert price > Decimal("0")

    def test_gcp_pd_ssd_lookup(self):
        from backend.app.wastage.pricing import lookup

        price = lookup("gcp", "persistent_disk/pd-ssd", "europe-west1")
        assert price > Decimal("0")

    def test_missing_provider_returns_zero(self):
        from backend.app.wastage.pricing import lookup

        assert lookup("unknown_cloud", "some/sku", "us-east-1") == Decimal("0")

    def test_missing_region_returns_zero(self):
        from backend.app.wastage.pricing import lookup

        assert lookup("azure", "managed_disk/Premium_LRS", "nonexistent-region") == Decimal("0")

    def test_missing_sku_returns_zero(self):
        from backend.app.wastage.pricing import lookup

        assert lookup("azure", "managed_disk/NonExistentSKU", "westeurope") == Decimal("0")

    def test_invalid_sku_format_returns_zero(self):
        from backend.app.wastage.pricing import lookup

        assert lookup("azure", "no-slash-here", "westeurope") == Decimal("0")

    def test_never_raises(self):
        """lookup() must not raise under any adversarial input."""
        from backend.app.wastage.pricing import lookup

        for provider, sku, region in [
            (None, None, None),
            ("", "", ""),
            ("azure", "", ""),
            ("azure", "/", "westeurope"),
        ]:
            try:
                result = lookup(provider, sku, region)
                assert result == Decimal("0")
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"lookup raised unexpectedly: {exc}")
