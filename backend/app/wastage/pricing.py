"""Price catalog loader for wastage cost estimation.

Usage::

    from backend.app.wastage.pricing import lookup

    monthly_usd = lookup("azure", "virtual_machine/Standard_D2_v3", "westeurope")
    # Returns Decimal("96.36") or Decimal("0") if not found.

The catalog files live under ``data/prices/`` relative to the repo root.
``lookup`` never raises — it returns ``Decimal("0")`` on any missing key or
parse error so rule authors don't need defensive try/except.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)

# Resolve catalog dir relative to this file:
# __file__ = <repo>/backend/app/wastage/pricing.py  →  parents[3] = <repo>
_PRICES_DIR = Path(__file__).resolve().parents[3] / "data" / "prices"

_CATALOGS: dict[str, dict[str, Any]] = {}


def _load_catalog(provider: str) -> dict[str, Any]:
    """Load and cache the price catalog JSON for *provider*."""
    if provider in _CATALOGS:
        return _CATALOGS[provider]

    catalog_path = _PRICES_DIR / f"{provider}_list_prices.json"
    if not catalog_path.exists():
        logger.warning("price catalog not found: %s", catalog_path)
        _CATALOGS[provider] = {}
        return {}

    with catalog_path.open() as fh:
        data = cast(dict[str, Any], json.load(fh))
    _CATALOGS[provider] = data
    return data


def lookup(provider: str, sku: str, region: str) -> Decimal:
    """Return the list price for *sku* in *region* for *provider*.

    SKU format is ``"<category>/<sku_name>"`` — e.g.:

    * ``"managed_disk/Premium_LRS"``          (Azure)
    * ``"virtual_machine/Standard_D2_v3"``    (Azure)
    * ``"app_service_plan/S2"``               (Azure)
    * ``"ebs/gp3"``                           (AWS)
    * ``"persistent_disk/pd-ssd"``            (GCP)

    Returns ``Decimal("0")`` when the combination is not catalogued.
    Never raises.
    """
    try:
        catalog = _load_catalog(provider)
        if not catalog:
            return Decimal("0")

        parts = sku.split("/", 1)
        if len(parts) != 2:
            logger.debug("lookup: invalid sku format %r", sku)
            return Decimal("0")

        category, sku_name = parts
        category_data = catalog.get(category)
        if not category_data:
            return Decimal("0")

        region_data = category_data.get(region)
        if not region_data:
            return Decimal("0")

        price = region_data.get(sku_name)
        if price is None:
            return Decimal("0")

        return Decimal(str(price))
    except (InvalidOperation, TypeError, KeyError, ValueError) as exc:
        logger.debug("lookup error for %s/%s/%s: %s", provider, sku, region, exc)
        return Decimal("0")


def reload() -> None:
    """Force reload of all cached catalogs (useful in tests or after file updates)."""
    _CATALOGS.clear()
