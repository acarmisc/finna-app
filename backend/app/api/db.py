"""Database connection and helpers for API."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

import psycopg
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool, ConnectionPool, PoolTimeout

logger = logging.getLogger("api.db")

# Pool size constants
POOL_MIN_CONNS = int(os.getenv("POOL_MIN_CONNS", "2"))
POOL_MAX_CONNS = int(os.getenv("POOL_MAX_CONNS", "10"))
POOL_RECYCLE = int(os.getenv("POOL_RECYCLE", "3600"))

# Global connection pools
_async_pool: Optional[AsyncConnectionPool] = None
_sync_pool: Optional[ConnectionPool] = None


def get_pg_dsn() -> str:
    """Get PostgreSQL DSN from environment."""
    dsn = os.getenv("PG_DSN")
    if not dsn:
        raise ValueError("PG_DSN environment variable is required")
    return dsn


def get_pool_config() -> dict[str, Any]:
    """Get pool configuration from environment variables."""
    return {
        "min_size": int(os.getenv("POOL_MIN_CONNS", "2")),
        "max_size": int(os.getenv("POOL_MAX_CONNS", "10")),
    }


async def init_async_pool() -> AsyncConnectionPool:
    """Initialize async connection pool."""
    global _async_pool
    if _async_pool is not None:
        return _async_pool

    config = get_pool_config()
    dsn = get_pg_dsn()

    logger.info(
        "Initializing async connection pool (min=%d, max=%d)",
        config["min_size"],
        config["max_size"],
    )

    _async_pool = AsyncConnectionPool(
        dsn,
        min_size=config["min_size"],
        max_size=config["max_size"],
        kwargs={
            "connect_timeout": 10,
            "row_factory": dict_row,
        },
    )

    await _async_pool.wait(timeout=30)
    logger.info("Async connection pool initialized successfully")
    return _async_pool


def init_sync_pool() -> ConnectionPool:
    """Initialize sync connection pool."""
    global _sync_pool
    if _sync_pool is not None:
        return _sync_pool

    config = get_pool_config()
    dsn = get_pg_dsn()

    logger.info(
        "Initializing sync connection pool (min=%d, max=%d)",
        config["min_size"],
        config["max_size"],
    )

    _sync_pool = ConnectionPool(
        dsn,
        min_size=config["min_size"],
        max_size=config["max_size"],
        kwargs={
            "connect_timeout": 10,
            "row_factory": dict_row,
        },
    )

    _sync_pool.wait(timeout=30)
    logger.info("Sync connection pool initialized successfully")
    return _sync_pool


async def get_async_pool() -> AsyncConnectionPool:
    """Get or create async connection pool."""
    global _async_pool
    if _async_pool is None:
        await init_async_pool()
    return _async_pool


def get_sync_pool() -> ConnectionPool:
    """Get or create sync connection pool."""
    global _sync_pool
    if _sync_pool is None:
        init_sync_pool()
    return _sync_pool


@asynccontextmanager
async def get_async_connection() -> AsyncIterator[AsyncConnection]:
    """Get an async PostgreSQL connection from the pool."""
    pool = await get_async_pool()
    try:
        async with pool.connection() as conn:
            yield conn
    except psycopg.PoolTimeout:
        logger.error("Connection pool exhausted - no available connections")
        raise
    except psycopg.Error as e:
        logger.exception("Database error: %s", e)
        raise


def get_connection() -> psycopg.Connection:
    """Get a sync PostgreSQL connection from the pool."""
    pool = get_sync_pool()
    try:
        conn = pool.getconn()
        if conn is None or conn.closed:
            conn = psycopg.connect(pool.dsn, row_factory=dict_row)
        return conn
    except PoolTimeout:
        logger.error("Connection pool exhausted - no available connections")
        raise


def release_connection(conn: psycopg.Connection) -> None:
    """Return a connection to the pool."""
    global _sync_pool
    if _sync_pool is not None and conn is not None:
        _sync_pool.putconn(conn)


def close_pools() -> None:
    """Close both async and sync connection pools."""
    import asyncio

    global _async_pool, _sync_pool
    if _async_pool is not None:
        logger.info("Closing async connection pool")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_async_pool.close())
            else:
                loop.run_until_complete(_async_pool.close())
        except Exception:
            pass
        _async_pool = None
    if _sync_pool is not None:
        logger.info("Closing sync connection pool")
        _sync_pool.close()
        _sync_pool = None


def get_pool_stats() -> dict[str, Any]:
    """Get pool statistics for monitoring."""
    stats = {"async": None, "sync": None}

    if _async_pool is not None:
        stats["async"] = {
            "min_size": _async_pool.min_size,
            "max_size": _async_pool.max_size,
            "size": len(_async_pool),
        }

    if _sync_pool is not None:
        stats["sync"] = {
            "min_size": _sync_pool.min_size,
            "max_size": _sync_pool.max_size,
            "size": len(_sync_pool),
        }

    return stats


def init_db() -> None:
    """Initialize database tables if they don't exist."""
    from pathlib import Path

    conn = get_connection()
    try:
        migrations_dir = Path(__file__).parent.parent / "sql" / "migrations"
        with conn.cursor() as cur:
            for migration_file in sorted(migrations_dir.glob("*.sql")):
                logger.info("Running migration: %s", migration_file.name)
                sql = migration_file.read_text()
                cur.execute(sql)
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception:
        conn.rollback()
        logger.exception("Failed to initialize database")
        raise
    finally:
        release_connection(conn)


def query_one(sql: str, params: tuple | None = None) -> dict[str, Any] | None:
    """Execute a query and return one result."""
    import json

    conn = get_connection()
    converted = []
    if params:
        for p in params:
            if isinstance(p, dict):
                converted.append(json.dumps(p))
            else:
                converted.append(p)
        params = tuple(converted)

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()

        if row:
            result = {}
            for k, v in row.items():
                if isinstance(v, str) and v.startswith("{") and ":" in v:
                    try:
                        result[k] = json.loads(v)
                    except Exception:
                        result[k] = v
                else:
                    result[k] = v
            return result
        return None
    finally:
        release_connection(conn)


def query_all(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """Execute a query and return all results."""
    import json

    conn = get_connection()
    converted = []
    if params:
        for p in params:
            if isinstance(p, dict):
                converted.append(json.dumps(p))
            else:
                converted.append(p)
        params = tuple(converted)

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        result = []
        for row in rows:
            converted_row = {}
            for k, v in row.items():
                if isinstance(v, str) and v.startswith("{") and ":" in v:
                    try:
                        converted_row[k] = json.loads(v)
                    except Exception:
                        converted_row[k] = v
                else:
                    converted_row[k] = v
            result.append(converted_row)
        return result
    finally:
        release_connection(conn)


def execute(sql: str, params: tuple | None = None) -> None:
    """Execute a query without returning results."""
    import json

    conn = get_connection()
    converted = []
    if params:
        for p in params:
            if isinstance(p, dict):
                converted.append(json.dumps(p))
            else:
                converted.append(p)
        params = tuple(converted)

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def insert_and_return(sql: str, params: tuple, returning: str = "id") -> str:
    """Insert a row and return the specified column."""
    import json

    conn = get_connection()
    converted = []
    for p in params:
        if isinstance(p, dict):
            converted.append(json.dumps(p))
        else:
            converted.append(p)

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, tuple(converted))
            result = cur.fetchone()
        conn.commit()
        return result[returning] if result else None
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
