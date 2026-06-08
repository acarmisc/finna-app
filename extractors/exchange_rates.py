"""ECB Exchange Rate Extractor for FinOps multi-cloud monitoring.

Fetches daily ECB (European Central Bank) exchange rates from their public XML
API, parses all currency rates against EUR, converts them to USD-denominated
rates, and upserts them into the ``exchange_rates`` PostgreSQL table.

Can run as a Cloud Run Job via ``python -m extractors.exchange_rates``.
"""

from __future__ import annotations

import logging
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import psycopg
from defusedxml import ElementTree as ET
from psycopg.rows import dict_row
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("extractors.exchange_rates")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ECB_URL: str = os.getenv(
    "ECB_URL",
    "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml",
)
PG_DSN: str = os.getenv("PG_DSN", "")
EXTRACTOR_NAME = "exchange_rates"

# XML namespaces used by the ECB feed
ECB_NS = {"gesmes": "http://www.gesmes.org/xml/2002-08-01", "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExchangeRate:
    """A single currency-to-USD exchange rate."""

    currency: str
    rate_to_usd: Decimal
    rate_date: date
    source: str = "ecb"


# ---------------------------------------------------------------------------
# ECB XML fetching and parsing
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type((urllib.error.URLError, urllib.error.HTTPError, TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _fetch_ecb_xml(url: str, timeout: int = 30) -> str:
    """Fetch the ECB daily exchange-rate XML document.

    Retries on transient network errors.
    """
    logger.info("Fetching ECB exchange rates from %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "finna-exchange-rates/1.0"})  # noqa: S310
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        payload = resp.read().decode("utf-8")
    logger.debug("Received %d bytes from ECB", len(payload))
    return payload  # type: ignore[no-any-return]


def _parse_ecb_xml(xml_text: str) -> tuple[date, dict[str, Decimal]]:
    """Parse the ECB XML and return (rate_date, {currency: rate_vs_eur}).

    The ECB feed provides rates as *1 EUR = X CUR*.  For example, if the USD
    rate is ``1.0850``, that means ``1 EUR = 1.0850 USD``.
    """
    root = ET.fromstring(xml_text)

    # The <Cube> hierarchy is:
    #   <gesmes:Envelope>
    #     <gesmes:subject>...</gesmes:subject>
    #     <gesmes:Sender>...</gesmes:Sender>
    #     <ecb:Cube>
    #       <ecb:Cube time="2025-01-15">        <-- date container
    #         <ecb:Cube currency="USD" rate="1.0850"/>
    #         <ecb:Cube currency="JPY" rate="164.32"/>
    #         ...
    #       </ecb:Cube>
    #     </ecb:Cube>
    #   </gesmes:Envelope>

    # Locate the date container — first <Cube> with a "time" attribute
    date_container = root.find(f".//{{{ECB_NS['ecb']}}}Cube[@time]")
    if date_container is None:
        raise ValueError("Could not find date container in ECB XML")

    rate_date = date.fromisoformat(date_container.get("time", ""))

    # Extract all currency rates from child <Cube currency="..." rate="..."/> elements
    rates_vs_eur: dict[str, Decimal] = {}
    for cube in date_container.findall(f"{{{ECB_NS['ecb']}}}Cube"):
        currency = cube.get("currency")
        rate_str = cube.get("rate")
        if currency and rate_str:
            rates_vs_eur[currency] = Decimal(rate_str)

    logger.info("Parsed %d currency rates for %s from ECB XML", len(rates_vs_eur), rate_date)
    return rate_date, rates_vs_eur


def _convert_to_usd_rates(rates_vs_eur: dict[str, Decimal]) -> dict[str, Decimal]:
    """Convert EUR-denominated rates to USD-denominated rates.

    ECB provides rates where 1 EUR = X CUR.
    We need rate_to_usd: 1 CUR = ? USD.

    Strategy:
    - USD rate from ECB: 1 EUR = usd_per_eur USD  =>  1 USD = 1/usd_per_eur EUR
    - For any other currency C: 1 EUR = c_per_eur C  =>  1 C = 1/c_per_eur EUR
      => 1 C = (1/c_per_eur) * (1/usd_per_eur)^{-1} ... no, let's think again.

    Actually:
    - 1 EUR = usd_per_eur USD   (from ECB)
    - 1 EUR = c_per_eur C      (from ECB)
    - Therefore: c_per_eur C = usd_per_eur USD
    - => 1 C = (usd_per_eur / c_per_eur) USD

    So rate_to_usd for currency C = usd_per_eur / c_per_eur.

    For EUR itself: rate_to_usd = 1 / usd_per_eur (inverse of the USD rate).
    """
    usd_per_eur = rates_vs_eur.get("USD")
    if usd_per_eur is None:
        raise ValueError("ECB XML does not contain USD rate — cannot convert to USD base")

    usd_rates: dict[str, Decimal] = {}

    # EUR -> USD: 1 EUR = usd_per_eur USD => 1 EUR = 1/usd_per_eur USD...
    # No — we want "how many USD per 1 EUR", which is simply usd_per_eur.
    # Wait — rate_to_usd means "1 of this currency = X USD".
    # For EUR: 1 EUR = usd_per_eur USD => rate_to_usd(EUR) = usd_per_eur.
    # Hmm, that's actually already given. But looking at the seed data in init.sql,
    # EUR has rate_to_usd = 1.0850, which matches "1 EUR = 1.0850 USD".
    # So yes, for EUR: rate_to_usd = usd_per_eur.

    usd_rates["EUR"] = usd_per_eur

    for currency, eur_rate in rates_vs_eur.items():
        if currency == "USD":
            # 1 USD = 1 USD
            usd_rates["USD"] = Decimal("1")
        else:
            # 1 C = (usd_per_eur / c_per_eur) USD
            rate_to_usd = (usd_per_eur / eur_rate).quantize(
                Decimal("0.00000001"), rounding=ROUND_HALF_UP
            )
            usd_rates[currency] = rate_to_usd

    logger.debug("Converted %d rates to USD base", len(usd_rates))
    return usd_rates


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type((psycopg.OperationalError, psycopg.InterfaceError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _get_pg_connection(dsn: str) -> psycopg.Connection:
    """Open a PostgreSQL connection with retry on transient errors."""
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=False)  # type: ignore[arg-type]


_UPSERT_SQL = """
    INSERT INTO exchange_rates (currency, rate_to_usd, rate_date, source, fetched_at)
    VALUES (%s, %s, %s, %s, now())
    ON CONFLICT (currency, rate_date) DO UPDATE
        SET rate_to_usd = EXCLUDED.rate_to_usd,
            source = EXCLUDED.source,
            fetched_at = now()
    """


def _upsert_rates(
    conn: psycopg.Connection,
    rates: dict[str, Decimal],
    rate_date: date,
    source: str = "ecb",
) -> int:
    """Upsert exchange rates into the ``exchange_rates`` table.

    Returns the number of rows upserted.
    """
    rows = [
        (currency, str(rate), rate_date, source)
        for currency, rate in sorted(rates.items())
    ]

    with conn.cursor() as cur:
        cur.executemany(_UPSERT_SQL, rows)
    conn.commit()

    logger.info("Upserted %d exchange rates for %s", len(rows), rate_date)
    return len(rows)


# ---------------------------------------------------------------------------
# Extractor health tracking
# ---------------------------------------------------------------------------

def _mark_health_start(conn: psycopg.Connection) -> None:
    """Mark the extractor as *running* in ``extractor_health``."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO extractor_health
                (extractor_name, last_run_start, status, records_extracted, updated_at)
            VALUES (%s, now(), 'running', 0, now())
            ON CONFLICT (extractor_name) DO UPDATE
                SET last_run_start = now(),
                    status = 'running',
                    records_extracted = 0,
                    error_message = NULL,
                    updated_at = now()
            """,
            (EXTRACTOR_NAME,),
        )
    conn.commit()


def _mark_health_success(conn: psycopg.Connection, record_count: int) -> None:
    """Mark the extractor as *success* in ``extractor_health``."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE extractor_health
            SET last_run_end = now(),
                status = 'success',
                records_extracted = %s,
                updated_at = now()
            WHERE extractor_name = %s
            """,
            (record_count, EXTRACTOR_NAME),
        )
    conn.commit()


def _mark_health_failure(conn: psycopg.Connection, error_message: str) -> None:
    """Mark the extractor as *failed* in ``extractor_health``."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE extractor_health
                SET last_run_end = now(),
                    status = 'failed',
                    error_message = %s,
                    updated_at = now()
                WHERE extractor_name = %s
                """,
                (error_message[:2000], EXTRACTOR_NAME),
            )
        conn.commit()
    except Exception:
        logger.exception("Failed to mark extractor health as failed")


# ---------------------------------------------------------------------------
# Core extractor logic
# ---------------------------------------------------------------------------

def extract(
    pg_dsn: str | None = None,
    ecb_url: str | None = None,
) -> int:
    """Run the full ECB exchange-rate extraction pipeline.

    Returns the total number of rates upserted into PostgreSQL.
    """
    dsn = pg_dsn or PG_DSN
    url = ecb_url or ECB_URL

    if not dsn:
        raise ValueError("PG_DSN is required (set env var or pass pg_dsn)")

    # Fetch and parse ECB XML
    xml_text = _fetch_ecb_xml(url)
    rate_date, rates_vs_eur = _parse_ecb_xml(xml_text)

    if not rates_vs_eur:
        logger.warning("No exchange rates found in ECB XML for %s", rate_date)
        return 0

    # Convert to USD base
    usd_rates = _convert_to_usd_rates(rates_vs_eur)

    # PostgreSQL connection
    pg_conn = _get_pg_connection(dsn)
    _mark_health_start(pg_conn)

    try:
        count = _upsert_rates(pg_conn, usd_rates, rate_date, source="ecb")
        _mark_health_success(pg_conn, count)
        logger.info("Exchange rate extraction complete: %d rates for %s", count, rate_date)
        return count

    except Exception as exc:
        logger.exception("Exchange rate extraction failed: %s", exc)
        _mark_health_failure(pg_conn, str(exc))
        raise
    finally:
        pg_conn.close()


# ---------------------------------------------------------------------------
# CLI entrypoint (Cloud Run Job)
# ---------------------------------------------------------------------------

def main() -> None:
    """Entrypoint for running the extractor as a Cloud Run Job."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s \u2014 %(message)s",
        stream=sys.stdout,
    )

    logger.info("Starting ECB exchange rate extractor")

    try:
        total = extract()
        logger.info("ECB exchange rate extractor finished: %d rates", total)
    except Exception:
        logger.exception("ECB exchange rate extractor failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
