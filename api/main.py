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
    # Startup: initialize database tables
    from api.db import get_pg_dsn

    if get_pg_dsn():
        try:
            from api.db import init_db

            init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.warning(
                f"Could not initialize DB: {e}. Will retry on first request."
            )

    yield

    # Shutdown: cleanup
    from api.db import _sync_pool

    if _sync_pool and _sync_pool.get("conn"):
        _sync_pool["conn"].close()
        logger.info("Database connection closed")


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
    from api.db import get_pg_dsn

    status = {
        "status": "ok",
        "api": "finops-orchestrator",
    }

    # Check database
    try:
        from api.db import get_connection

        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        status["database"] = "ok"
    except Exception as e:
        status["database"] = f"error: {e}"
        status["status"] = "degraded"

    return JSONResponse(status, status_code=200 if status["status"] == "ok" else 503)


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
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
