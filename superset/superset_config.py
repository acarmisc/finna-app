# =============================================================================
# FinOps Multi-Cloud Monitoring -- Apache Superset Configuration
# =============================================================================
# This file is mounted into the Superset container at /app/pythonpath/
# Override SECRET_KEY via the SUPERSET_SECRET_KEY environment variable in
# docker-compose.yml before deploying to production.
# =============================================================================

import os

# ---------------------------------------------------------------------------
# Secret key -- MUST be changed in production
# ---------------------------------------------------------------------------
# A placeholder is used here; the real value is injected via the
# SUPERSET_SECRET_KEY environment variable.
SECRET_KEY = os.getenv("SUPERSET_SECRET_KEY", "CHANGE_ME_TO_A_RANDOM_SECRET")

# ---------------------------------------------------------------------------
# Metadata database (Superset's own state)
# ---------------------------------------------------------------------------
# Points to a dedicated PostgreSQL database on the same Postgres instance.
DATABASE_URI = os.getenv(
    "SUPERSET_DATABASE_URI",
    "postgresql://finops:finops_dev@postgres:5432/superset_meta",
)
SQLALCHEMY_DATABASE_URI = DATABASE_URI

# Prevent Superset from opening its own database sessions that conflict
# with the container-level connection pool.
SQLALCHEMY_TRACK_MODIFICATIONS = False

# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------
FEATURE_FLAGS = {
    "ALERT_REPORTS": True,  # Enable scheduled alerts and reports
}

# ---------------------------------------------------------------------------
# Cache configuration
# ---------------------------------------------------------------------------
# Use Redis when available; fall back to SimpleCache for local development.
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

try:
    import redis  # noqa: F401

    CACHE_CONFIG = {
        "CACHE_TYPE": "RedisCache",
        "CACHE_DEFAULT_TIMEOUT": 300,
        "CACHE_KEY_PREFIX": "superset_",
        "CACHE_REDIS_URL": REDIS_URL,
    }
    DATA_CACHE_CONFIG = CACHE_CONFIG
    FILTER_STATE_CACHE_CONFIG = {
        **CACHE_CONFIG,
        "CACHE_KEY_PREFIX": "superset_filter_",
    }
    EXPLORE_CACHE_CONFIG = {
        **CACHE_CONFIG,
        "CACHE_KEY_PREFIX": "superset_explore_",
    }
except ImportError:
    CACHE_CONFIG = {
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 300,
    }
    DATA_CACHE_CONFIG = CACHE_CONFIG
    FILTER_STATE_CACHE_CONFIG = CACHE_CONFIG
    EXPLORE_CACHE_CONFIG = CACHE_CONFIG

# ---------------------------------------------------------------------------
# CSRF / security
# ---------------------------------------------------------------------------
WTF_CSRF_ENABLED = True
WTF_CSRF_EXEMPT_LIST = ["superset.views.core.api"]
WTF_CSRF_TIME_LIMIT = 60 * 60 * 24 * 7  # 7 days

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
SUPERSET_WEBSERVER_PROTOCOL = "http"
SUPERSET_WEBSERVER_ADDRESS = "0.0.0.0"
SUPERSET_WEBSERVER_PORT = 8088

# Prefer the modern native filter bar
ENABLE_NATIVE_FILTERS = True

# Allow dashboard edits
DASHBOARD_AUTO_REFRESH_MODE = "fetch"

# Logging level
LOG_FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
LOG_LEVEL = os.getenv("SUPERSET_LOG_LEVEL", "INFO")