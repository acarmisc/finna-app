"""Prometheus metrics for API."""

from prometheus_client import Counter, Gauge, Histogram

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

api_request_duration_histogram = Histogram(
    "finna_api_request_duration_seconds_bucket",
    "API request duration histogram in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
"""Histogram metric tracking API request durations with configurable buckets."""
