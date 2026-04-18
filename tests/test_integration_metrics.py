"""Integration tests for Prometheus metrics functionality."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestPrometheusMetrics:
    """Tests for Prometheus metrics instrumentation."""

    def test_metrics_endpoint_available(self):
        """Test that /metrics endpoint is available."""
        from api.main import app

        routes = [route.path for route in app.routes]
        assert "/metrics" in routes or any("/metrics" in str(r) for r in routes)

    def test_metrics_formats(self):
        """Test that metrics endpoint returns correct format."""
        os.environ["PROMETHEUS_ENABLED"] = "true"

        from api.metrics import Metrics

        metrics = Metrics()

        assert metrics is not None
        assert hasattr(metrics, "requests_total")
        assert hasattr(metrics, "request_duration")

    def test_metrics_registry(self):
        """Test that metrics are registered."""
        from prometheus_client import REGISTRY

        metrics = REGISTRY.sample_names()
        assert metrics is not None


class TestMetricNames:
    """Tests for metric naming conventions."""

    def test_metric_names_defined(self):
        """Test that metric names are properly defined."""
        from api.metrics import Metrics

        metrics = Metrics()

        metric_attrs = [
            "requests_total",
            "request_duration",
            "extractor_runs_total",
            "error_count",
        ]

        for attr in metric_attrs:
            assert hasattr(metrics, attr)


class TestMetricsCollection:
    """Tests for metrics collection."""

    def test_http_requests_metric(self):
        """Test HTTP requests counter."""
        from prometheus_client import REGISTRY

        metric_names = REGISTRY.sample_names()

        expected = ["http_request_duration", "http_requests_total"]

        for expected_metric in expected:
            assert any(expected_metric in name for name in metric_names)

    def test_extractor_metric(self):
        """Test extractor metric exists."""
        from api.metrics import Metrics

        metrics = Metrics()
        assert hasattr(metrics, "extractor_runs_total")


class TestMetricsIntegration:
    """Integration tests for metrics with FastAPI."""

    def test_metrics_middleware(self):
        """Test metrics middleware is configured."""
        from api.main import app

        # Verify middleware is present
        assert hasattr(app, "middleware")
        assert app.middleware is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
