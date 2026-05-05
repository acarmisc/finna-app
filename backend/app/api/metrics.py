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

extractor_duration_seconds = Histogram(
    "finna_extractor_duration_seconds",
    "Extractor run duration in seconds",
    ["provider", "status"],
    buckets=[30, 60, 120, 300, 600, 1200, 3600],
)
"""Histogram metric tracking extractor run durations by provider and status."""
