"""Comprehensive unit tests for api/metrics.py - Prometheus metrics."""

from __future__ import annotations

import pytest


class TestConfigCountMetric:
    """Tests for config_count metric."""

    def test_config_count_metric_exists(self):
        """Test config_count metric is defined."""
        from api.metrics import config_count

        assert config_count is not None
        assert "finna_config_total" in config_count._name

    def test_config_count_labels(self):
        """Test config_count has provider label."""
        from api.metrics import config_count

        labels = config_count._labelnames
        assert "provider" in labels


class TestExtractorRunTotalMetric:
    """Tests for extractor_run_total metric."""

    def test_extractor_run_total_exists(self):
        """Test extractor_run_total metric is defined."""
        from api.metrics import extractor_run_total

        assert extractor_run_total is not None
        assert "finna_extractor_run" in extractor_run_total._name

    def test_extractor_run_total_labels(self):
        """Test extractor_run_total has correct labels."""
        from api.metrics import extractor_run_total

        labels = extractor_run_total._labelnames
        assert "provider" in labels
        assert "status" in labels


class TestApiRequestDurationMetric:
    """Tests for api_request_duration metric."""

    def test_api_request_duration_exists(self):
        """Test api_request_duration metric is defined."""
        from api.metrics import api_request_duration

        assert api_request_duration is not None
        assert "finna_api_request_duration_seconds" in api_request_duration._name

    def test_api_request_duration_labels(self):
        """Test api_request_duration has correct labels."""
        from api.metrics import api_request_duration

        labels = api_request_duration._labelnames
        assert "method" in labels
        assert "endpoint" in labels


class TestApiRequestTotalMetric:
    """Tests for api_request_total metric."""

    def test_api_request_total_exists(self):
        """Test api_request_total metric is defined."""
        from api.metrics import api_request_total

        assert api_request_total is not None
        assert "finna_api_request" in api_request_total._name

    def test_api_request_total_labels(self):
        """Test api_request_total has correct labels."""
        from api.metrics import api_request_total

        labels = api_request_total._labelnames
        assert "method" in labels
        assert "endpoint" in labels
        assert "status" in labels


class TestMetricOperations:
    """Tests for metric operations."""

    def test_counter_inc(self):
        """Test Counter increment operation."""
        from api.metrics import extractor_run_total

        # Should not raise
        extractor_run_total.labels(provider="azure", status="success").inc()

    def test_gauge_set(self):
        """Test Gauge set operation."""
        from api.metrics import config_count

        # Should not raise
        config_count.labels(provider="azure").set(42)

    def test_gauge_inc(self):
        """Test Gauge increment operation."""
        from api.metrics import api_request_duration

        # Should not raise
        api_request_duration.labels(method="GET", endpoint="/test").set(1.5)


class TestMetricDocumentation:
    """Tests for metric documentation."""

    def test_config_count_docs(self):
        """Test config_count has documentation."""
        from api.metrics import config_count

        assert config_count.__doc__ is not None
        assert "gauge" in config_count.__doc__.lower()

    def test_extractor_run_total_docs(self):
        """Test extractor_run_total has documentation."""
        from api.metrics import extractor_run_total

        assert extractor_run_total.__doc__ is not None
        assert "counter" in extractor_run_total.__doc__.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
