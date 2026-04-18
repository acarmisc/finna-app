"""FastAPI application for FinOps orchestrator."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

logger = logging.getLogger("backend.app.main")

limiter = Limiter(key_func=get_remote_address)


def rate_limit_from_env(var_name: str, default: int) -> int:
    """Parse rate limit from environment variable."""
    value = os.getenv(var_name)
    if value is not None:
        try:
            return int(value)
        except ValueError:
            pass
    return default


RATE_LIMIT_PER_MINUTE = rate_limit_from_env("RATE_LIMIT_PER_MINUTE", 60)
RATE_LIMIT_PER_HOUR = rate_limit_from_env("RATE_LIMIT_PER_HOUR", 1000)

EXTRACTOR_LIMIT_PER_MINUTE = rate_limit_from_env("EXTRACTOR_LIMIT_PER_MINUTE", 30)
EXTRACTOR_LIMIT_PER_HOUR = rate_limit_from_env("EXTRACTOR_LIMIT_PER_HOUR", 200)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Custom rate limit middleware to handle 429 responses properly."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except RateLimitExceeded as e:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": str(e),
                    "detail": "Too many requests. Please try again later.",
                },
            )


class TokenVerificationMiddleware(BaseHTTPMiddleware):
    """Middleware to verify JWT token on all protected routes."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/v1/") and request.url.path not in [
            "/api/v1/auth/token",
            "/api/v1/healthz",
        ]:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    from backend.app.auth import decode_token

                    decode_token(token)
                except HTTPException:
                    return JSONResponse(
                        status_code=401,
                        content={
                            "error": "invalid_token",
                            "message": "Invalid or expired token",
                            "detail": "Could not validate credentials",
                        },
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            else:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "missing_token",
                        "message": "Not authenticated",
                        "detail": "Not authenticated",
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return await call_next(request)


class RequestDurationMiddleware(BaseHTTPMiddleware):
    """Middleware to record request duration in Prometheus histogram."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        from backend.app.metrics import api_request_duration_histogram

        endpoint = request.url.path
        api_request_duration_histogram.labels(method=request.method, endpoint=endpoint).observe(duration)
        return response


def setup_telemetry(app: FastAPI) -> None:
    """Configure OpenTelemetry tracing for FastAPI."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanExporter
        from opentelemetry.sdk.resources import Resource

        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        service_name = os.getenv("OTEL_SERVICE_NAME", "finna-api")

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )

                exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                provider.add_span_processor(
                    __import__("opentelemetry.sdk.trace.export", fromlist=["BatchSpanProcessor"]).BatchSpanProcessor(
                        exporter
                    )
                )
            except Exception:
                pass

        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry tracing configured (service=%s)", service_name)
    except ImportError:
        logger.debug("OpenTelemetry packages not installed — skipping tracing setup")


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Application lifecycle: startup and shutdown."""
    # Startup: initialize connection pool
    from backend.app.db import get_pg_dsn
    from backend.app.metrics import config_count

    if get_pg_dsn():
        try:
            from backend.app.db import init_sync_pool

            init_sync_pool()
            logger.info("Connection pool initialized")
        except Exception as e:
            logger.warning(f"Could not initialize connection pool: {e}. Will retry on first request.")

        try:
            from backend.app.db import init_db

            init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.warning(f"Could not initialize DB: {e}. Will retry on first request.")

        # Initialize config_count metric
        try:
            from backend.app.db import query_all

            rows = query_all("SELECT provider, COUNT(*) as count FROM cloud_config GROUP BY provider")
            for row in rows:
                config_count.labels(provider=row["provider"]).set(row["count"])
        except Exception as e:
            logger.warning(f"Could not initialize config_count metric: {e}")

        # Auto-migrate if enabled
        if os.getenv("AUTO_MIGRATE", "false").lower() == "true":
            try:
                from alembic.config import Config

                from alembic import command

                alembic_cfg = Config("alembic.ini")
                command.upgrade(alembic_cfg, "head")
                logger.info("Alembic migrations applied successfully")
            except Exception as e:
                logger.warning(f"Could not run migrations: {e}")

    # Initialize Prometheus metrics instrumentator
    instrumentator = Instrumentator(
        should_group_routes=True,
        should_ignore_health_status=True,
        excluded_handlers=["/metrics", "/healthz"],
    )
    instrumentator.instrument(app)

    # Configure OpenTelemetry tracing
    setup_telemetry(app)

    yield

    # Shutdown: close connection pools
    from backend.app.db import close_pools

    close_pools()
    logger.info("Connection pools closed")


app = FastAPI(
    title="FinOps Orchestrator API",
    description="Centralized orchestration for FinOps extractors",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(RateLimitMiddleware)

# Request duration middleware
app.add_middleware(RequestDurationMiddleware)

# Token verification middleware
app.add_middleware(TokenVerificationMiddleware)

# CORS middleware for CLI (local development)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Expose Prometheus metrics."""
    from backend.app.metrics import api_request_duration_histogram  # noqa: F401

    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
async def healthz() -> JSONResponse:
    """Health check endpoint."""
    from backend.app.db import get_connection, release_connection

    status = {
        "status": "ok",
        "api": "finops-orchestrator",
    }

    # Check database
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        status["database"] = "ok"
    except Exception as e:
        status["database"] = f"error: {e}"
        status["status"] = "degraded"
    finally:
        if conn is not None:
            release_connection(conn)

    return JSONResponse(status, status_code=200 if status["status"] == "ok" else 503)


@app.get("/api/v1/db/stats")
async def db_stats() -> JSONResponse:
    """Get database connection pool stats."""
    from backend.app.db import get_pool_stats

    return JSONResponse(get_pool_stats())


# Mount routers
from backend.app.routes import auth, extractors  # noqa: E402
from backend.app.routes import config as config_router  # noqa: E402
from backend.app.routes import plugins as plugins_router  # noqa: E402

app.include_router(config_router.router, prefix="/api/v1", tags=["config"])
app.include_router(extractors.router, prefix="/api/v1", tags=["extractors"])
app.include_router(plugins_router.router, prefix="/api/v1", tags=["plugins"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])

# ---------------------------------------------------------------------------
# Serve frontend static files (SPA fallback)
# ---------------------------------------------------------------------------
# In production (Docker), static files are at /app/static
# In local dev, this directory might not exist (proxied by Vite)
STATIC_DIR = os.getenv("STATIC_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "static"))


@app.get("/{path:path}", include_in_schema=False)
async def spa_fallback(path: str):
    """Serve static files or fall back to index.html for SPA routing."""
    if path.startswith("api/") or path.startswith("metrics") or path.startswith("healthz"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    file_path = os.path.join(STATIC_DIR, path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)

    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)

    return JSONResponse({"detail": "Not Found"}, status_code=404)


# Mount static directory for direct static file access (after routes so API takes priority)
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="static-assets")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
