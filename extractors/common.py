"""Cross-provider utilities shared by cost extractors.

Unlike ``extractors.gcp_shared`` (GCP-specific normalization), this module
holds logic with no per-provider variation: currency conversion and the
exchange-rate lookup used by any extractor that stores costs in a non-USD
currency.
"""

from __future__ import annotations

import logging
from decimal import Decimal

import psycopg
from psycopg import sql as psycopg_sql

logger = logging.getLogger("extractors.common")

# Table identifier is interpolated into SQL below; restrict to a fixed
# allowlist so it can never carry attacker- or config-controlled input.
ALLOWED_EXCHANGE_TABLES = {"exchange_rates"}


def load_exchange_rates(
    conn: psycopg.Connection, table: str = "exchange_rates"
) -> dict[str, Decimal]:
    """Load exchange rates from the database. Returns {currency_code: rate_to_usd}."""
    rates: dict[str, Decimal] = {"USD": Decimal("1")}
    if table not in ALLOWED_EXCHANGE_TABLES:
        raise ValueError(f"Invalid exchange rate table: {table}")
    try:
        with conn.cursor() as cur:
            cur.execute(
                psycopg_sql.SQL("SELECT currency, rate_to_usd FROM {}").format(
                    psycopg_sql.Identifier(table)
                )
            )
            for row in cur.fetchall():
                rates[row[0]] = Decimal(str(row[1]))
    except psycopg.Error:
        conn.rollback()
        logger.warning("Failed to load exchange rates from %s; assuming USD=1 only", table)
    return rates


def convert_to_usd(cost: Decimal, currency: str, rates: dict[str, Decimal]) -> Decimal:
    """Convert a cost in *currency* to USD using the provided rates dict."""
    if currency == "USD":
        return cost
    rate = rates.get(currency)
    if rate is None:
        logger.warning("No exchange rate for currency %s — treating as USD=1", currency)
        return cost
    return (cost * rate).quantize(Decimal("0.000001"))
