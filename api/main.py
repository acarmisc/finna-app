"""FastAPI application for FinOps orchestrator."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Application lifecycle: startup and shutdown."""
    # Startup: initialize connection pool
    from api.db import get_pg_dsn

    if get_pg_dsn():
        try:
            from api.db import init_sync_pool

            init_sync_pool()
            logger.info("Connection pool initialized")
        except Exception as e:
            logger.warning(
                f"Could not initialize connection pool: {e}. Will retry on first request."
            )

        try:
            from api.db import init_db

            init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.warning(
                f"Could not initialize DB: {e}. Will retry on first request."
            )

    yield

    # Shutdown: close connection pools
    from api.db import close_pools

    close_pools()
    logger.info("Connection pools closed")


app = FastAPI(
    title="FinOps Orchestrator API",
    description="Centralized orchestration for FinOps extractors",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for CLI (local development)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz() -> JSONResponse:
    """Health check endpoint."""
    from api.db import get_pg_dsn, get_connection, release_connection

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
    from api.db import get_pool_stats

    return JSONResponse(get_pool_stats())


# Mount routers
from api.routes import auth, config as config_router, extractors  # noqa: E402

app.include_router(config_router.router, prefix="/api/v1", tags=["config"])
app.include_router(extractors.router, prefix="/api/v1", tags=["extractors"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000"),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
