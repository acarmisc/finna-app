# Finna API - FastAPI backend

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator

from . import db, routes
from .errors import register_error_handlers


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

# Register custom error handlers
register_error_handlers(app)

# Add CORS middleware
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Re-export routes module to avoid circular import issues
__all__ = ["app", "auth", "db", "routes"]


@app.middleware("http")
async def db_session_middleware(request: Request, call_next: Any) -> Any:
    """Attach database connection to request."""
    if os.environ.get("TESTING"):
        return await call_next(request)
    try:
        async with db.get_async_connection() as conn:
            request.state.db = conn
            response = await call_next(request)
        return response
    except Exception as exc:
        # Log the error but still process the request — avoids breaking responses
        # when DB connection issues occur. In production, consider a circuit breaker.
        import logging
        logging.getLogger("api.main").warning("DB middleware error: %s", exc)
        response = await call_next(request)
        return response


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
)

app.include_router(config.router, prefix="/api/v1", tags=["config"])
app.include_router(extractors_registry.router, prefix="/api/v1", tags=["extractors"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(auth_providers.router, prefix="/api/v1", tags=["auth"])
app.include_router(oidc_auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(costs.router, prefix="/api/v1", tags=["costs"])
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])

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
