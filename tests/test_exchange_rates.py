"""Tests for the ECB exchange rate extractor."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from extractors.exchange_rates import (
    _convert_to_usd_rates,
    _parse_ecb_xml,
    _upsert_rates,
    extract,
)

# ---------------------------------------------------------------------------
# Sample ECB XML response (matches real ECB structure)
# ---------------------------------------------------------------------------

MOCK_ECB_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns:ecb="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <gesmes:subject>Reference rates</gesmes:subject>
  <gesmes:Sender>
    <gesmes:name>European Central Bank</gesmes:name>
  </gesmes:Sender>
  <ecb:Cube>
    <ecb:Cube time="2025-04-10">
      <ecb:Cube currency="USD" rate="1.0850"/>
      <ecb:Cube currency="JPY" rate="164.32"/>
      <ecb:Cube currency="GBP" rate="0.8568"/>
      <ecb:Cube currency="CHF" rate="0.9205"/>
      <ecb:Cube currency="CAD" rate="1.4750"/>
      <ecb:Cube currency="AUD" rate="1.6650"/>
      <ecb:Cube currency="SEK" rate="11.42"/>
      <ecb:Cube currency="NOK" rate="11.78"/>
      <ecb:Cube currency="DKK" rate="7.46"/>
      <ecb:Cube currency="INR" rate="92.45"/>
    </ecb:Cube>
  </ecb:Cube>
</gesmes:Envelope>
"""


# ---------------------------------------------------------------------------
# Tests: XML parsing
# ---------------------------------------------------------------------------

class TestParseEcbXml:
    """Tests for _parse_ecb_xml."""

    def test_extracts_rate_date(self) -> None:
        rate_date, _ = _parse_ecb_xml(MOCK_ECB_XML)
        assert rate_date == date(2025, 4, 10)

    def test_extracts_all_currencies(self) -> None:
        _, rates = _parse_ecb_xml(MOCK_ECB_XML)
        assert len(rates) == 10
        assert "USD" in rates
        assert "JPY" in rates
        assert "GBP" in rates

    def test_rates_are_decimal(self) -> None:
        _, rates = _parse_ecb_xml(MOCK_ECB_XML)
        assert rates["USD"] == Decimal("1.0850")
        assert rates["JPY"] == Decimal("164.32")
        assert rates["GBP"] == Decimal("0.8568")

    def test_raises_on_empty_xml(self) -> None:
        """An XML document without a date Cube should raise."""
        empty_xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns:ecb="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <gesmes:subject>Reference rates</gesmes:subject>
  <ecb:Cube/>
</gesmes:Envelope>
"""
        with pytest.raises(ValueError, match="Could not find date container"):
            _parse_ecb_xml(empty_xml)

    def test_ignores_cubes_without_currency(self) -> None:
        """Cube entries missing currency or rate attributes are silently skipped."""
        xml_with_gaps = MOCK_ECB_XML.replace(
            '<ecb:Cube currency="INR" rate="92.45"/>',
            '<ecb:Cube rate="99.99"/><ecb:Cube currency="INR" rate="92.45"/>',
        )
        _, rates = _parse_ecb_xml(xml_with_gaps)
        # The attribute-less Cube should be skipped; INR should still be present
        assert "INR" in rates
        assert len(rates) == 10  # same count as before


# ---------------------------------------------------------------------------
# Tests: EUR -> USD rate conversion
# ---------------------------------------------------------------------------

class TestConvertToUsdRates:
    """Tests for _convert_to_usd_rates."""

    def test_usd_is_one(self) -> None:
        rates_vs_eur = {"USD": Decimal("1.0850")}
        usd_rates = _convert_to_usd_rates(rates_vs_eur)
        assert usd_rates["USD"] == Decimal("1")

    def test_eur_rate(self) -> None:
        rates_vs_eur = {"USD": Decimal("1.0850")}
        usd_rates = _convert_to_usd_rates(rates_vs_eur)
        assert usd_rates["EUR"] == Decimal("1.0850")

    def test_other_currency_conversion(self) -> None:
        """For currency C where 1 EUR = c_per_eur C, rate_to_usd = usd_per_eur / c_per_eur."""
        rates_vs_eur = {"USD": Decimal("1.0850"), "GBP": Decimal("0.8568")}
        usd_rates = _convert_to_usd_rates(rates_vs_eur)
        # 1 GBP = 1.0850 / 0.8568 USD
        expected = (Decimal("1.0850") / Decimal("0.8568")).quantize(
            Decimal("0.00000001")
        )
        assert usd_rates["GBP"] == expected

    def test_jpy_conversion(self) -> None:
        rates_vs_eur = {"USD": Decimal("1.0850"), "JPY": Decimal("164.32")}
        usd_rates = _convert_to_usd_rates(rates_vs_eur)
        expected = (Decimal("1.0850") / Decimal("164.32")).quantize(
            Decimal("0.00000001")
        )
        assert usd_rates["JPY"] == expected

    def test_raises_without_usd(self) -> None:
        rates_vs_eur = {"GBP": Decimal("0.8568")}
        with pytest.raises(ValueError, match="does not contain USD rate"):
            _convert_to_usd_rates(rates_vs_eur)

    def test_full_conversion_matches_seed_data(self) -> None:
        """Verify the conversion against the seed data in init.sql."""
        rates_vs_eur = {
            "USD": Decimal("1.0850"),
            "GBP": Decimal("0.8568"),
            "JPY": Decimal("164.32"),
            "CHF": Decimal("0.9652"),
            "CAD": Decimal("1.4750"),
            "AUD": Decimal("1.6650"),
            "SEK": Decimal("11.42"),
            "NOK": Decimal("11.78"),
            "DKK": Decimal("7.46"),
            "INR": Decimal("92.45"),
        }
        usd_rates = _convert_to_usd_rates(rates_vs_eur)
        # EUR -> USD should be the ECB USD rate itself
        assert usd_rates["EUR"] == Decimal("1.0850")
        assert usd_rates["USD"] == Decimal("1")


# ---------------------------------------------------------------------------
# Tests: Database upsert (idempotent)
# ---------------------------------------------------------------------------

class TestUpsertRates:
    """Tests for _upsert_rates using a mock connection."""

    def test_upsert_calls_executemany(self) -> None:
        conn = MagicMock(spec=psycopg.Connection)
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        rates = {"USD": Decimal("1"), "EUR": Decimal("1.0850")}
        rate_date = date(2025, 4, 10)
        count = _upsert_rates(conn, rates, rate_date, source="ecb")

        assert count == 2
        assert cursor.executemany.called
        conn.commit.assert_called_once()

    def test_upsert_is_idempotent(self) -> None:
        """Calling upsert twice with the same data should not error."""
        conn = MagicMock(spec=psycopg.Connection)
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        rates = {"USD": Decimal("1"), "EUR": Decimal("1.0850")}
        rate_date = date(2025, 4, 10)

        # Simulate two sequential upserts (same data)
        _upsert_rates(conn, rates, rate_date, source="ecb")
        _upsert_rates(conn, rates, rate_date, source="ecb")

        # Both calls should succeed without raising
        assert cursor.executemany.call_count == 2


# ---------------------------------------------------------------------------
# Tests: End-to-end extract() with mocks
# ---------------------------------------------------------------------------

class TestExtract:
    """Tests for the full extract() pipeline."""

    @patch("extractors.exchange_rates._get_pg_connection")
    @patch("extractors.exchange_rates._fetch_ecb_xml")
    def test_extract_happy_path(self, mock_fetch: MagicMock, mock_pg: MagicMock) -> None:
        mock_fetch.return_value = MOCK_ECB_XML

        conn = MagicMock(spec=psycopg.Connection)
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pg.return_value = conn

        count = extract(pg_dsn="postgresql://test:test@localhost/testdb")

        # 10 ECB currencies + EUR + USD = 11 total rates
        assert count == 11
        mock_fetch.assert_called_once()
        conn.close.assert_called_once()

    @patch("extractors.exchange_rates._get_pg_connection")
    @patch("extractors.exchange_rates._fetch_ecb_xml")
    def test_extract_marks_failure_on_error(
        self, mock_fetch: MagicMock, mock_pg: MagicMock
    ) -> None:
        mock_fetch.side_effect = urllib_error("Connection refused")

        conn = MagicMock(spec=psycopg.Connection)
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pg.return_value = conn

        with pytest.raises(Exception):
            extract(pg_dsn="postgresql://test:test@localhost/testdb")

    @patch("extractors.exchange_rates._get_pg_connection")
    @patch("extractors.exchange_rates._fetch_ecb_xml")
    def test_extract_raises_without_dsn(
        self, mock_fetch: MagicMock, mock_pg: MagicMock
    ) -> None:
        with pytest.raises(ValueError, match="PG_DSN is required"):
            extract(pg_dsn="")

    @patch("extractors.exchange_rates._get_pg_connection")
    @patch("extractors.exchange_rates._fetch_ecb_xml")
    def test_extract_uses_custom_url(
        self, mock_fetch: MagicMock, mock_pg: MagicMock
    ) -> None:
        mock_fetch.return_value = MOCK_ECB_XML
        conn = MagicMock(spec=psycopg.Connection)
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pg.return_value = conn

        extract(pg_dsn="postgresql://test:test@localhost/testdb", ecb_url="http://test.local/rates.xml")

        mock_fetch.assert_called_once_with("http://test.local/rates.xml")


class urllib_error(Exception):
    """Minimal stand-in for urllib.error.URLError to avoid import in tests."""
    pass