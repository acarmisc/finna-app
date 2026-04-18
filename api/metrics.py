"""Prometheus metrics for API."""

from prometheus_client import Counter, Gauge

config_count = Gauge(
    "finna_config_total",
    "Total number of cloud configurations",
    ["provider"],
)

extractor_run_total = Counter(
    "finna_extractor_run_total",
    "Total number of extractor runs",
    ["provider", "status"],
)

api_request_duration = Gauge(
    "finna_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
)

api_request_total = Counter(
    "finna_api_request_total",
    "Total number of API requests",
    ["method", "endpoint", "status"],
)
