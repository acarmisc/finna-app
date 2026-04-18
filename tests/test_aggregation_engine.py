"""Tests for the aggregation engine.

Covers window alignment, statistical calculations (avg/max/p95/sum/sample_count),
configurable window sizes, and empty input handling.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aggregation.config import AggregationConfig, MetricAggregationSettings
from aggregation.engine import (
    aggregate,
    align_to_window,
    compute_aggregates,
    compute_percentile,
)

# ---------------------------------------------------------------------------
# Tests: window alignment
# ---------------------------------------------------------------------------


class TestWindowAlignment:
    def test_15m_exact_boundary(self):
        ts = datetime(2025, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
        assert align_to_window(ts, 15) == ts

    def test_15m_mid_window(self):
        ts = datetime(2025, 3, 1, 10, 7, 30, tzinfo=timezone.utc)
        expected = datetime(2025, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
        assert align_to_window(ts, 15) == expected

    def test_15m_near_boundary(self):
        ts = datetime(2025, 3, 1, 10, 29, 59, tzinfo=timezone.utc)
        expected = datetime(2025, 3, 1, 10, 15, 0, tzinfo=timezone.utc)
        assert align_to_window(ts, 15) == expected

    def test_5m_alignment(self):
        ts = datetime(2025, 3, 1, 10, 37, 42, tzinfo=timezone.utc)
        expected = datetime(2025, 3, 1, 10, 35, 0, tzinfo=timezone.utc)
        assert align_to_window(ts, 5) == expected

    def test_1m_alignment(self):
        ts = datetime(2025, 3, 1, 10, 37, 42, tzinfo=timezone.utc)
        expected = datetime(2025, 3, 1, 10, 37, 0, tzinfo=timezone.utc)
        assert align_to_window(ts, 1) == expected

    def test_30m_alignment(self):
        ts = datetime(2025, 3, 1, 10, 45, 0, tzinfo=timezone.utc)
        expected = datetime(2025, 3, 1, 10, 30, 0, tzinfo=timezone.utc)
        assert align_to_window(ts, 30) == expected

    def test_naive_timestamp_gets_utc(self):
        ts = datetime(2025, 3, 1, 10, 7, 30)  # no tzinfo
        result = align_to_window(ts, 15)
        assert result.tzinfo is not None
        assert result.hour == 10
        assert result.minute == 0

    def test_hour_boundary_15m(self):
        """10:00:00 is a valid 15m boundary."""
        ts = datetime(2025, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
        assert align_to_window(ts, 15) == ts

    def test_midnight_15m(self):
        ts = datetime(2025, 3, 1, 0, 14, 59, tzinfo=timezone.utc)
        expected = datetime(2025, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert align_to_window(ts, 15) == expected


# ---------------------------------------------------------------------------
# Tests: percentile computation
# ---------------------------------------------------------------------------


class TestPercentile:
    def test_single_value(self):
        assert compute_percentile([42.0], 50) == 42.0
        assert compute_percentile([42.0], 95) == 42.0
        assert compute_percentile([42.0], 0) == 42.0

    def test_two_values_p50(self):
        result = compute_percentile([10.0, 20.0], 50)
        assert result == pytest.approx(15.0)

    def test_p95_with_many_values(self):
        values = [float(i) for i in range(1, 101)]  # 1..100
        p95 = compute_percentile(values, 95)
        # With 100 values, rank = 0.95 * 99 = 94.05
        # Interpolation: values[94] + 0.05 * (values[95] - values[94])
        # = 95 + 0.05 * (96 - 95) = 95.05
        assert p95 == pytest.approx(95.05)

    def test_p0_returns_min(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert compute_percentile(values, 0) == 1.0

    def test_p100_returns_max(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert compute_percentile(values, 100) == 5.0

    def test_empty_list(self):
        assert compute_percentile([], 95) == 0.0


# ---------------------------------------------------------------------------
# Tests: compute_aggregates
# ---------------------------------------------------------------------------


class TestComputeAggregates:
    def test_basic_stats(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = compute_aggregates(values)

        assert result["avg"] == pytest.approx(30.0)
        assert result["max"] == pytest.approx(50.0)
        assert result["sum"] == pytest.approx(150.0)
        assert result["sample_count"] == 5

    def test_p95_calculation(self):
        values = [float(i) for i in range(1, 21)]  # 1..20
        result = compute_aggregates(values)
        # rank = 0.95 * 19 = 18.05
        # values[18] + 0.05 * (values[19] - values[18]) = 19 + 0.05 * 1 = 19.05
        assert result["p95"] == pytest.approx(19.05)

    def test_single_value(self):
        result = compute_aggregates([42.0])
        assert result["avg"] == pytest.approx(42.0)
        assert result["max"] == pytest.approx(42.0)
        assert result["p95"] == pytest.approx(42.0)
        assert result["sum"] == pytest.approx(42.0)
        assert result["sample_count"] == 1

    def test_empty_input(self):
        result = compute_aggregates([])
        assert result["avg"] is None
        assert result["max"] is None
        assert result["p95"] is None
        assert result["sum"] is None
        assert result["sample_count"] == 0

    def test_negative_values(self):
        values = [-10.0, -5.0, 0.0, 5.0, 10.0]
        result = compute_aggregates(values)
        assert result["avg"] == pytest.approx(0.0)
        assert result["max"] == pytest.approx(10.0)
        assert result["sum"] == pytest.approx(0.0)
        assert result["sample_count"] == 5

    def test_duplicate_values(self):
        values = [5.0, 5.0, 5.0, 5.0]
        result = compute_aggregates(values)
        assert result["avg"] == pytest.approx(5.0)
        assert result["max"] == pytest.approx(5.0)
        assert result["p95"] == pytest.approx(5.0)
        assert result["sum"] == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# Tests: aggregate() function
# ---------------------------------------------------------------------------


def _make_data_point(
    ts: datetime,
    metric_name: str,
    value: float,
    provider: str = "gcp",
    project_id: str = "ml-platform",
    resource_id: str = "vm-001",
) -> dict:
    return {
        "timestamp": ts,
        "metric_name": metric_name,
        "value": value,
        "labels": {
            "provider": provider,
            "project_id": project_id,
            "resource_id": resource_id,
        },
    }


class TestAggregate:
    def test_single_data_point(self):
        ts = datetime(2025, 3, 1, 10, 5, 0, tzinfo=timezone.utc)
        dps = [_make_data_point(ts, "cpu", 75.0)]

        results = aggregate(dps, window_minutes=15)
        assert len(results) == 1

        r = results[0]
        assert r["window_start"] == datetime(2025, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
        assert r["window_end"] == datetime(2025, 3, 1, 10, 15, 0, tzinfo=timezone.utc)
        assert r["cpu_avg"] == pytest.approx(75.0)
        assert r["cpu_max"] == pytest.approx(75.0)
        assert r["cpu_p95"] == pytest.approx(75.0)
        assert r["sample_count"] == 1

    def test_multiple_metrics_same_window(self):
        base = datetime(2025, 3, 1, 10, 5, 0, tzinfo=timezone.utc)
        dps = [
            _make_data_point(base, "cpu", 75.0),
            _make_data_point(base, "cpu", 80.0),
            _make_data_point(base, "memory", 4096.0),
            _make_data_point(base, "memory", 8192.0),
            _make_data_point(base, "network_in", 1024.0),
            _make_data_point(base, "network_out", 512.0),
        ]

        results = aggregate(dps, window_minutes=15)
        assert len(results) == 1

        r = results[0]
        assert r["cpu_avg"] == pytest.approx(77.5)
        assert r["cpu_max"] == pytest.approx(80.0)
        assert r["memory_avg_bytes"] == pytest.approx(6144.0)
        assert r["memory_max_bytes"] == pytest.approx(8192.0)
        assert r["network_in_bytes"] == pytest.approx(1024.0)
        assert r["network_out_bytes"] == pytest.approx(512.0)
        assert r["sample_count"] == 2  # max of (2 cpu, 2 memory, 1 net_in, 1 net_out)

    def test_different_windows(self):
        # Two data points in different 15-minute windows
        ts1 = datetime(2025, 3, 1, 10, 5, 0, tzinfo=timezone.utc)  # -> 10:00
        ts2 = datetime(2025, 3, 1, 10, 20, 0, tzinfo=timezone.utc)  # -> 10:15

        dps = [
            _make_data_point(ts1, "cpu", 50.0),
            _make_data_point(ts2, "cpu", 90.0),
        ]

        results = aggregate(dps, window_minutes=15)
        assert len(results) == 2

        # Sort by window_start for deterministic checking
        results.sort(key=lambda r: r["window_start"])
        assert results[0]["cpu_avg"] == pytest.approx(50.0)
        assert results[1]["cpu_avg"] == pytest.approx(90.0)

    def test_different_resources_same_window(self):
        ts = datetime(2025, 3, 1, 10, 5, 0, tzinfo=timezone.utc)
        dps = [
            _make_data_point(ts, "cpu", 50.0, resource_id="vm-001"),
            _make_data_point(ts, "cpu", 80.0, resource_id="vm-002"),
        ]

        results = aggregate(dps, window_minutes=15)
        assert len(results) == 2

    def test_5m_window(self):
        ts = datetime(2025, 3, 1, 10, 7, 30, tzinfo=timezone.utc)
        dps = [_make_data_point(ts, "cpu", 65.0)]

        results = aggregate(dps, window_minutes=5)
        assert len(results) == 1
        assert results[0]["window_start"] == datetime(2025, 3, 1, 10, 5, 0, tzinfo=timezone.utc)
        assert results[0]["window_end"] == datetime(2025, 3, 1, 10, 10, 0, tzinfo=timezone.utc)

    def test_1m_window(self):
        ts = datetime(2025, 3, 1, 10, 7, 42, tzinfo=timezone.utc)
        dps = [_make_data_point(ts, "cpu", 65.0)]

        results = aggregate(dps, window_minutes=1)
        assert len(results) == 1
        assert results[0]["window_start"] == datetime(2025, 3, 1, 10, 7, 0, tzinfo=timezone.utc)

    def test_30m_window(self):
        ts = datetime(2025, 3, 1, 10, 45, 0, tzinfo=timezone.utc)
        dps = [_make_data_point(ts, "cpu", 65.0)]

        results = aggregate(dps, window_minutes=30)
        assert len(results) == 1
        assert results[0]["window_start"] == datetime(2025, 3, 1, 10, 30, 0, tzinfo=timezone.utc)

    def test_empty_input(self):
        results = aggregate([], window_minutes=15)
        assert results == []

    def test_iso_string_timestamps(self):
        dps = [
            {
                "timestamp": "2025-03-01T10:05:00+00:00",
                "metric_name": "cpu",
                "value": 75.0,
                "labels": {
                    "provider": "gcp",
                    "project_id": "ml-platform",
                    "resource_id": "vm-001",
                },
            }
        ]

        results = aggregate(dps, window_minutes=15)
        assert len(results) == 1
        assert results[0]["cpu_avg"] == pytest.approx(75.0)

    def test_p95_with_many_cpu_samples(self):
        base = datetime(2025, 3, 1, 10, 5, 0, tzinfo=timezone.utc)
        # 100 cpu samples from 1..100
        dps = [_make_data_point(base, "cpu", float(i)) for i in range(1, 101)]

        results = aggregate(dps, window_minutes=15)
        assert len(results) == 1
        r = results[0]
        assert r["cpu_avg"] == pytest.approx(50.5)
        assert r["cpu_max"] == pytest.approx(100.0)
        assert r["cpu_p95"] == pytest.approx(95.05)
        assert r["sample_count"] == 100


# ---------------------------------------------------------------------------
# Tests: aggregation config
# ---------------------------------------------------------------------------


class TestAggregationConfig:
    def test_defaults(self):
        config = AggregationConfig()
        assert config.infra_metrics.window_size_minutes == 15
        assert config.infra_metrics.retention_days == 365
        assert config.llm_requests.window_size_minutes == 5
        assert config.llm_requests.retention_days == 180
        assert config.billing.window_size_minutes == 60
        assert config.billing.retention_days == 730

    def test_get_settings_known_type(self):
        config = AggregationConfig()
        settings = config.get_settings("llm_requests")
        assert settings.window_size_minutes == 5
        assert settings.retention_days == 180

    def test_get_settings_unknown_type_falls_back(self):
        config = AggregationConfig()
        settings = config.get_settings("custom_metric")
        # Falls back to infra_metrics
        assert settings.window_size_minutes == 15
        assert settings.retention_days == 365

    def test_custom_values(self):
        config = AggregationConfig(
            infra_metrics=MetricAggregationSettings(window_size_minutes=5, retention_days=90),
        )
        assert config.infra_metrics.window_size_minutes == 5
        assert config.infra_metrics.retention_days == 90

    def test_load_from_yaml(self, tmp_path):
        yaml_content = """
aggregation:
  infra_metrics:
    window_size_minutes: 15
    retention_days: 365
  llm_requests:
    window_size_minutes: 5
    retention_days: 180
  billing:
    window_size_minutes: 60
    retention_days: 730
"""
        config_file = tmp_path / "agg_config.yaml"
        config_file.write_text(yaml_content)

        from aggregation.config import load_aggregation_config

        config = load_aggregation_config(str(config_file))
        assert config.infra_metrics.window_size_minutes == 15
        assert config.llm_requests.window_size_minutes == 5

    def test_load_client_config_from_yaml(self, tmp_path):
        yaml_content = """
client_id: acme-corp
client_name: Acme Corporation
aggregation:
  infra_metrics:
    window_size_minutes: 10
    retention_days: 90
  llm_requests:
    window_size_minutes: 5
    retention_days: 180
"""
        config_file = tmp_path / "client_config.yaml"
        config_file.write_text(yaml_content)

        from aggregation.config import load_client_config

        client_config = load_client_config(str(config_file))
        assert client_config.client_id == "acme-corp"
        assert client_config.client_name == "Acme Corporation"
        assert client_config.aggregation.infra_metrics.window_size_minutes == 10
        assert client_config.aggregation.infra_metrics.retention_days == 90

    def test_missing_config_file_raises(self):
        from aggregation.config import load_aggregation_config

        with pytest.raises(FileNotFoundError):
            load_aggregation_config("/nonexistent/config.yaml")
