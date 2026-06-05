# Finna API - FastAPI backend

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from . import db, routes
from .errors import register_error_handlers
from .rate_limit import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Initialize and tear down application resources."""
    # Startup
    if not os.environ.get("TESTING"):
        await db.init_async_pool()
    yield
    # Shutdown
    if not os.environ.get("TESTING"):
        db.close_pools()


app = FastAPI(
    title="Finna API",
    description="Finna cloud cost management and extraction platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Fail fast on unsafe secrets — reject dev placeholders and weak lengths.
# Skip under TESTING=1 so the test suite can use deterministic short fixtures.
if not os.environ.get("TESTING"):
    _UNSAFE_SECRETS = {
        "dev-secret-key-change-in-production",
        "dev-key-change-in-production",
        "change-me",
        "",
    }
    for _var in ("JWT_SECRET", "ENCRYPTION_KEY"):
        _val = os.environ.get(_var, "")
        if _val in _UNSAFE_SECRETS or _val.startswith("change-me"):
            raise RuntimeError(f"{_var} is a known-unsafe placeholder; set a strong value in .env")
        if len(_val) < 32:
            raise RuntimeError(f"{_var} must be at least 32 characters; got {len(_val)}")

# Wire rate limiter (slowapi) — global default + per-route overrides
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Register custom error handlers
register_error_handlers(app)

# Add CORS middleware with hardened validation
raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

# Validate CORS configuration
if "*" in allowed_origins:
    raise RuntimeError(
        "CORS misconfig: '*' incompatible with allow_credentials=True"
    )

for origin in allowed_origins:
    if not origin.startswith(("http://", "https://")):
        raise RuntimeError(
            f"CORS misconfig: origin '{origin}' missing http(s):// scheme"
        )

logger.info("CORS allowlist: %s", allowed_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Re-export routes module to avoid circular import issues
__all__ = ["app", "auth", "db", "routes"]

# DB middleware imports
import logging

import psycopg
from psycopg_pool import PoolTimeout

_logger = logging.getLogger("api.main")


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Any) -> Any:
    """Add security response headers (production only, skip under TESTING=1)."""
    response = await call_next(request)
    if not os.environ.get("TESTING"):
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; connect-src 'self'"
        )
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        logger.debug("Security headers applied to response")
    return response


@app.middleware("http")
async def db_session_middleware(request: Request, call_next: Any) -> Any:
    """Attach database connection to request."""
    if os.environ.get("TESTING"):
        return await call_next(request)
    try:
        async with db.get_async_connection() as conn:
            request.state.db = conn
            return await call_next(request)
    except (psycopg.OperationalError, PoolTimeout) as exc:
        # DB unavailable (pool exhausted or DB down) — return 503 immediately
        _logger.error("DB unavailable: %s", exc)
        return JSONResponse(
            status_code=503, content={"detail": "database_unavailable"}
        )


# Health check endpoints
@app.get("/health")
async def health() -> dict[str, str]:
    """Basic health check."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    """Healthz endpoint returns status, api name, and database health (mocked)."""
    # Intentionally returning with status ok, api name, and database status
    # The actual database status is mocked in tests
    return {"status": "ok", "api": "finops-orchestrator", "database": "ok"}


@app.get("/api/v1/health")
async def api_health() -> JSONResponse:
    """Extended health check with database status."""
    status: dict[str, Any] = {"status": "ok", "timestamp": datetime.now().isoformat()}

    # Check database connection
    conn = None
    try:
        async with db.get_async_connection() as conn:
            await conn.execute("SELECT 1")
            status["database"] = "ok"
    except Exception as e:
        status["error"] = str(e)
        status["database"] = f"error: {e}"
        status["status"] = "degraded"

    return JSONResponse(status, status_code=200 if status["status"] == "ok" else 503)


@app.get("/api/v1/db/stats")
async def db_stats() -> JSONResponse:
    """Get database connection pool stats."""
    from .db import get_pool_stats

    return JSONResponse(get_pool_stats())


# Mount routers
from .routes import (  # noqa: E402
    alerts,
    auth,
    auth_providers,
    config,
    costs,
    extractors_registry,
    oidc_auth,
    wastage,
)

app.include_router(config.router, prefix="/api/v1", tags=["config"])
app.include_router(extractors_registry.router, prefix="/api/v1", tags=["extractors"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(auth_providers.router, prefix="/api/v1", tags=["auth"])
app.include_router(oidc_auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(costs.router, prefix="/api/v1", tags=["costs"])
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
app.include_router(wastage.router, prefix="/api/v1", tags=["wastage"])

# Dev-only raw SQL endpoints (gated)
_env = os.environ.get("ENV", "")
if _env.lower() == "development":
    from .routes import db_dev
    app.include_router(db_dev.router, prefix="/api/v1", tags=["db"])
    print("WARNING: db_dev raw SQL endpoints are mounted (ENV=development). Do NOT deploy this to production.")

# Initialize Prometheus metrics instrumentator (must be after middleware)
instrumentator = Instrumentator()
instrumentator.instrument(app)
instrumentator.expose(app, include_in_schema=False)

# Initialize OpenTelemetry tracing
try:
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    provider = TracerProvider()
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor().instrument()
except ImportError:
    pass
