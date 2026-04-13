"""Tests for the Bifrost LLM cost extractor.

Uses mock Bifrost PostgreSQL data to verify normalization, key mapping,
incremental extraction, and batch insertion logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from extractors.bifrost_llm import (
    EXTRACTOR_NAME,
    batch_insert,
    fetch_bifrost_logs,
    get_last_ingested_ts,
    load_key_mapping,
    mark_extractor_done,
    mark_extractor_failed,
    mark_extractor_running,
    normalize_log,
)
from models import NormalizedCostRecord, Provider, ServiceCategory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

KEY_MAPPING = {
    "vk-ml-platform": {
        "project_id": "ml-platform",
        "project_name": "ML Platform",
        "team": "ml",
        "environment": "prod",
    },
    "vk-finops-prod": {
        "project_id": "finops-prod",
        "project_name": "FinOps Production",
        "team": "platform",
        "environment": "prod",
    },
    "vk-dev-sandbox": {
        "project_id": "dev-sandbox",
        "project_name": "Dev Sandbox",
        "team": "devops",
        "environment": "dev",
    },
}

MOCK_LOGS = [
    {
        "model": "gpt-4o",
        "provider": "openai",
        "input_tokens": 1500,
        "output_tokens": 800,
        "cost": 0.153,
        "latency": 1200.5,
        "virtual_key": "vk-ml-platform",
        "timestamp": datetime(2025, 3, 1, 10, 30, 0, tzinfo=timezone.utc),
    },
    {
        "model": "claude-3-5-sonnet",
        "provider": "anthropic",
        "input_tokens": 2000,
        "output_tokens": 1000,
        "cost": 0.09,
        "latency": 950.0,
        "virtual_key": "vk-finops-prod",
        "timestamp": datetime(2025, 3, 1, 10, 31, 0, tzinfo=timezone.utc),
    },
    {
        "model": "gpt-4o-mini",
        "provider": "openai",
        "input_tokens": 500,
        "output_tokens": 200,
        "cost": 0.009,
        "latency": 400.0,
        "virtual_key": "vk-dev-sandbox",
        "timestamp": datetime(2025, 3, 1, 10, 32, 0, tzinfo=timezone.utc),
    },
]


# ---------------------------------------------------------------------------
# Tests: load_key_mapping
# ---------------------------------------------------------------------------


class TestLoadKeyMapping:
    def test_loads_valid_yaml(self, tmp_path):
        mapping_file = tmp_path / "mapping.yaml"
        mapping_file.write_text(
            "mappings:\n"
            "  vk-test:\n"
            "    project_id: test-proj\n"
            "    team: qa\n"
        )
        result = load_key_mapping(str(mapping_file))
        assert "vk-test" in result
        assert result["vk-test"]["project_id"] == "test-proj"

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_key_mapping("/nonexistent/path.yaml")

    def test_raises_on_empty_mappings(self, tmp_path):
        mapping_file = tmp_path / "empty.yaml"
        mapping_file.write_text("mappings: {}\n")
        with pytest.raises(ValueError, match="No mappings"):
            load_key_mapping(str(mapping_file))


# ---------------------------------------------------------------------------
# Tests: normalize_log
# ---------------------------------------------------------------------------


class TestNormalizeLog:
    def test_basic_normalization(self):
        log = MOCK_LOGS[0]
        record = normalize_log(log, KEY_MAPPING)

        assert isinstance(record, NormalizedCostRecord)
        assert record.provider == Provider.LLM
        assert record.service_category == ServiceCategory.LLM
        assert record.project_id == "ml-platform"
        assert record.project_name == "ML Platform"
        assert record.team == "ml"
        assert record.environment == "prod"
        assert record.service_name == "gpt-4o"
        assert record.model_name == "gpt-4o"
        assert record.input_tokens == 1500
        assert record.output_tokens == 800
        assert record.total_tokens == 2300
        assert record.cost_usd == Decimal("0.153")
        assert record.net_cost_usd == Decimal("0.153")
        assert record.latency_ms == 1200.5
        assert record.tags["virtual_key"] == "vk-ml-platform"
        assert record.tags["llm_provider"] == "openai"

    def test_different_providers(self):
        log = MOCK_LOGS[1]  # Anthropic
        record = normalize_log(log, KEY_MAPPING)
        assert record.model_name == "claude-3-5-sonnet"
        assert record.tags["llm_provider"] == "anthropic"
        assert record.project_id == "finops-prod"

    def test_unmapped_virtual_key_returns_none(self):
        log = {**MOCK_LOGS[0], "virtual_key": "vk-unknown"}
        record = normalize_log(log, KEY_MAPPING)
        assert record is None

    def test_naive_timestamp_gets_utc(self):
        log = {
            "model": "gpt-4o",
            "provider": "openai",
            "input_tokens": 100,
            "output_tokens": 50,
            "cost": 0.01,
            "latency": 500.0,
            "virtual_key": "vk-ml-platform",
            "timestamp": datetime(2025, 3, 1, 10, 0, 0),  # naive
        }
        record = normalize_log(log, KEY_MAPPING)
        assert record is not None
        assert record.usage_start.tzinfo is not None

    def test_zero_cost(self):
        log = {**MOCK_LOGS[0], "cost": 0}
        record = normalize_log(log, KEY_MAPPING)
        assert record is not None
        assert record.cost_usd == Decimal("0")

    def test_none_latency(self):
        log = {**MOCK_LOGS[0], "latency": None}
        record = normalize_log(log, KEY_MAPPING)
        assert record is not None
        assert record.latency_ms is None


# ---------------------------------------------------------------------------
# Tests: fetch_bifrost_logs
# ---------------------------------------------------------------------------


class TestFetchBifrostLogs:
    def test_fetch_without_since(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = MOCK_LOGS

        result = fetch_bifrost_logs(mock_conn, since=None, batch_size=1000)
        assert len(result) == 3
        # Should NOT have the WHERE clause parameter
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert call_args[1] == (1000,)

    def test_fetch_with_since(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [MOCK_LOGS[1]]

        since = datetime(2025, 3, 1, 10, 30, 0, tzinfo=timezone.utc)
        result = fetch_bifrost_logs(mock_conn, since=since, batch_size=500)
        assert len(result) == 1
        call_args = mock_cursor.execute.call_args
        assert call_args[1] == (since, 500)


# ---------------------------------------------------------------------------
# Tests: incremental extraction state
# ---------------------------------------------------------------------------


class TestExtractorHealth:
    def test_get_last_ingested_ts_parses_stored_watermark(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = {
            "error_message": "2025-03-01T10:30:00+00:00"
        }

        result = get_last_ingested_ts(mock_conn)
        assert result == datetime(2025, 3, 1, 10, 30, 0, tzinfo=timezone.utc)

    def test_get_last_ingested_ts_returns_none_when_no_row(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None

        result = get_last_ingested_ts(mock_conn)
        assert result is None

    def test_mark_extractor_running_inserts(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mark_extractor_running(mock_conn)
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_mark_extractor_done_updates(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        ts = datetime(2025, 3, 1, 10, 30, 0, tzinfo=timezone.utc)
        mark_extractor_done(mock_conn, records_extracted=42, watermark=ts)
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert call_args[1][0] == 42
        mock_conn.commit.assert_called_once()

    def test_mark_extractor_failed_updates(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mark_extractor_failed(mock_conn, "Connection refused")
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "Connection refused" in call_args[1][0]
        mock_conn.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: batch_insert
# ---------------------------------------------------------------------------


class TestBatchInsert:
    def test_inserts_records(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        records = [normalize_log(log, KEY_MAPPING) for log in MOCK_LOGS]
        # Filter None (shouldn't happen with our test data)
        records = [r for r in records if r is not None]

        inserted = batch_insert(mock_conn, records)
        assert inserted == 3
        mock_cursor.execute_batch.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_insert_empty_list(self):
        mock_conn = MagicMock()
        result = batch_insert(mock_conn, [])
        assert result == 0
        mock_conn.cursor.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: end-to-end normalization pipeline
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_full_pipeline_logs_to_records(self):
        """Simulate the full pipeline: logs -> normalized records."""
        records = []
        skipped = 0
        for log_entry in MOCK_LOGS:
            rec = normalize_log(log_entry, KEY_MAPPING)
            if rec is not None:
                records.append(rec)
            else:
                skipped += 1

        assert len(records) == 3
        assert skipped == 0

        # Verify all records are valid NormalizedCostRecord
        for rec in records:
            assert rec.provider == Provider.LLM
            assert rec.service_category == ServiceCategory.LLM
            assert rec.account_id == "bifrost-gateway"
            assert rec.usage_unit == "tokens"

    def test_pipeline_with_unmapped_key(self):
        """Logs with unmapped keys are skipped."""
        logs = MOCK_LOGS + [
            {
                "model": "gemini-1.5-pro",
                "provider": "google",
                "input_tokens": 3000,
                "output_tokens": 1500,
                "cost": 0.20,
                "latency": 800.0,
                "virtual_key": "vk-unknown-project",
                "timestamp": datetime(2025, 3, 1, 11, 0, 0, tzinfo=timezone.utc),
            },
        ]

        records = []
        skipped = 0
        for log_entry in logs:
            rec = normalize_log(log_entry, KEY_MAPPING)
            if rec is not None:
                records.append(rec)
            else:
                skipped += 1

        assert len(records) == 3
        assert skipped == 1