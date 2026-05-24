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

# OIDC circuit breaker metrics
oidc_discovery_fallback_total = Counter(
    "finna_oidc_discovery_fallback_total",
    "Total number of OIDC discovery fallbacks from stale cache",
)
"""Counter metric tracking OIDC discovery fallbacks from stale cache."""

oidc_jwks_fallback_total = Counter(
    "finna_oidc_jwks_fallback_total",
    "Total number of OIDC JWKS fallbacks from stale cache",
)
"""Counter metric tracking OIDC JWKS fallbacks from stale cache."""

oidc_jwks_fetch_duration_seconds = Histogram(
    "finna_oidc_jwks_fetch_duration_seconds",
    "OIDC JWKS fetch duration in seconds",
    ["status"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60],
)
"""Histogram metric tracking JWKS fetch durations by status."""

oidc_discovery_fetch_duration_seconds = Histogram(
    "finna_oidc_discovery_fetch_duration_seconds",
    "OIDC discovery fetch duration in seconds",
    ["status"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60],
)
"""Histogram metric tracking discovery fetch durations by status."""

oidc_circuit_breaker_state = Gauge(
    "finna_oidc_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 0.5=half_open)",
    ["service"],
)
"""Gauge metric tracking circuit breaker state (0=closed, 1=open, 0.5=half_open)."""

oidc_circuit_breaker_failures = Counter(
    "finna_oidc_circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["service"],
)
"""Counter metric tracking circuit breaker failures by service."""
