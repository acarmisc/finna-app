# Finna API - FastAPI backend

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator

from . import auth as auth_module
from . import db
from .api import routes
from .models import ErrorResponse, HealthStatus, HealthStatusDetail

app = FastAPI(
    title="Finna API",
    description="Finna cloud cost management and extraction platform",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Re-export routes module to avoid circular import issues
__all__ = ["app", "auth", "db", "routes"]


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database connection pool on startup."""
    await db.init_pool()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Close database connection pool on shutdown."""
    await db.close_pool()


@app.middleware("http")
async def db_session_middleware(request: Request, call_next: Any) -> Any:
    """Attach database connection to request."""
    conn = await db.get_connection()
    request.state.db = conn
    try:
        response = await call_next(request)
    finally:
        await db.release_connection(conn)
    return response


# Health check endpoint
@app.get("/health")
async def health() -> dict[str, str]:
    """Basic health check."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/v1/health")
async def api_health() -> JSONResponse:
    """Extended health check with database status."""
    status: dict[str, Any] = {"status": "ok", "timestamp": datetime.now().isoformat()}

    # Check database connection
    conn = None
    try:
        conn = await db.get_connection()
        await conn.fetchrow("SELECT 1")
        status["database"] = "ok"
    except Exception as e:
        status["error"] = str(e)
        status["database"] = f"error: {e}"
        status["status"] = "degraded"
    finally:
        if conn is not None:
            await db.release_connection(conn)

    return JSONResponse(status, status_code=200 if status["status"] == "ok" else 503)


@app.get("/api/v1/db/stats")
async def db_stats() -> JSONResponse:
    """Get database connection pool stats."""
    from .db import get_pool_stats

    return JSONResponse(get_pool_stats())


# Mount routers
from .routes import auth, config, extractors, costs, alerts, db_dev, extractors_registry  # noqa: E402
from .routes import create_rate_limiting_middleware  # noqa: E402

# Add rate limiting middleware (must be before routers)
app.middleware("http")(create_rate_limiting_middleware())

app.include_router(config.router, prefix="/api/v1", tags=["config"])
app.include_router(extractors.router, prefix="/api/v1", tags=["extractors"])
app.include_router(extractors_registry.router, prefix="/api/v1", tags=["extractors"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(costs.router, prefix="/api/v1", tags=["costs"])
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
app.include_router(db_dev.router, prefix="/api/v1", tags=["db"])

# Initialize Prometheus metrics instrumentator (must be after middleware)
instrumentator = Instrumentator()
instrumentator.instrument(app)
instrumentator.expose(app, include_in_schema=False)

# Initialize OpenTelemetry tracing
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    provider = TracerProvider()
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor().instrument(app)
except ImportError:
    pass
