"""Prometheus metrics for API."""

from prometheus_client import Counter, Gauge

config_count = Gauge(
    "finna_config_total",
    "Total number of cloud configurations",
    ["provider"],
)
"""Gauge metric tracking total cloud configurations by provider."""

extractor_run_total = Counter(
    "finna_extractor_run_total",
    "Total number of extractor runs",
    ["provider", "status"],
)
"""Counter metric tracking extractor runs by provider and status."""

api_request_duration = Gauge(
    "finna_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
)
"""Gauge metric tracking API request durations."""

api_request_total = Counter(
    "finna_api_request_total",
    "Total number of API requests",
    ["method", "endpoint", "status"],
)
"""Counter metric tracking total API requests by method, endpoint, and status."""
