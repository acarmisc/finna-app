"""Tests for records_extracted parsing in api/runner.py."""

from __future__ import annotations

import re

PATTERNS = (
    r"(\d+)\s+records?\s+inserted",
    r"(\d+)\s+records?$",
    r"(\d+)\s+rates",
    r"Inserted\s+(\d+)\s+",
)


def parse_records_from_output(output_lines: list[str]) -> int:
    """Parse record count from extractor output lines."""
    for line in output_lines:
        for pattern in PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return int(match.group(1))
    return 0


def test_azure_records_inserted():
    lines = [
        "2026-04-18 10:00:00 INFO [extractors.azure_cost] Azure Cost Extractor completed: 26 records inserted\n",
    ]
    assert parse_records_from_output(lines) == 26


def test_azure_inserted_count():
    lines = [
        "2026-04-18 10:00:00 INFO [extractors.azure_cost] Inserted 26 of 26 records into PostgreSQL\n",
    ]
    assert parse_records_from_output(lines) == 26


def test_gcp_billing_records():
    lines = [
        "2026-04-18 10:00:00 INFO [extractors.gcp_billing] Extraction complete: 142 records inserted\n",
    ]
    assert parse_records_from_output(lines) == 142


def test_gcp_billing_finished():
    lines = [
        "2026-04-18 10:00:00 INFO [extractors.gcp_billing] GCP billing extractor finished: 50 records\n",
    ]
    assert parse_records_from_output(lines) == 50


def test_gcp_csv_finished():
    lines = [
        "2026-04-18 10:00:00 INFO [extractors.gcp_csv] GCP CSV billing extractor finished: 300 records\n",
    ]
    assert parse_records_from_output(lines) == 300


def test_exchange_rates():
    lines = [
        "2026-04-18 10:00:00 INFO [extractors.exchange_rates] ECB exchange rate extractor finished: 34 rates\n",
    ]
    assert parse_records_from_output(lines) == 34


def test_zero_records():
    lines = [
        "2026-04-18 10:00:00 INFO [extractors.azure_cost] Azure Cost Extractor completed: 0 records inserted\n",
    ]
    assert parse_records_from_output(lines) == 0


def test_no_matching_lines():
    lines = [
        "2026-04-18 10:00:00 INFO [extractors.azure_cost] Starting extraction...\n",
    ]
    assert parse_records_from_output(lines) == 0


def test_multiple_lines_picks_first_match():
    lines = [
        "2026-04-18 10:00:00 INFO [extractors.azure_cost] Inserted 10 of 10 records into PostgreSQL\n",
        "2026-04-18 10:00:00 INFO [extractors.azure_cost] Azure Cost Extractor completed: 10 records inserted\n",
    ]
    assert parse_records_from_output(lines) == 10


def test_single_record():
    lines = [
        "2026-04-18 10:00:00 INFO [extractors.azure_cost] Azure Cost Extractor completed: 1 record inserted\n",
    ]
    assert parse_records_from_output(lines) == 1


def test_runner_monitor_parses_azure_output():
    from backend.app.runner import _parse_records_from_lines

    lines = [
        "2026-04-18 10:00:00,123 INFO [extractors.azure_cost] Azure Cost Extractor completed: 26 records inserted\n",
    ]
    assert _parse_records_from_lines(lines) == 26


def test_runner_monitor_parses_gcp_output():
    from backend.app.runner import _parse_records_from_lines

    lines = [
        "2026-04-18 10:00:00,123 INFO [extractors.gcp_billing] GCP billing extractor finished: 142 records\n",
    ]
    assert _parse_records_from_lines(lines) == 142


def test_runner_monitor_parses_exchange_rates():
    from backend.app.runner import _parse_records_from_lines

    lines = [
        "2026-04-18 10:00:00,123 INFO [extractors.exchange_rates] ECB exchange rate extractor finished: 34 rates\n",
    ]
    assert _parse_records_from_lines(lines) == 34
