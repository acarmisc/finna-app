"""Database connection and helpers for API."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

import psycopg
from psycopg import AsyncConnection
from psycopg.rows import dict_row

logger = logging.getLogger("api.db")

# Global connection pool (used in sync context for extractor subprocesses)
_sync_pool: Optional[dict[str, Any]] = None


def get_pg_dsn() -> str:
    """Get PostgreSQL DSN from environment."""
    dsn = os.getenv("PG_DSN")
    if not dsn:
        raise ValueError("PG_DSN environment variable is required")
    return dsn


def get_sync_pool() -> dict[str, Any]:
    """Get or create sync connection pool."""
    global _sync_pool
    if _sync_pool is None:
        pg_dsn = get_pg_dsn()
        _sync_pool = {"dsn": pg_dsn, "conn": None}
    return _sync_pool


def get_connection() -> psycopg.Connection:
    """Get a sync PostgreSQL connection."""
    pool = get_sync_pool()
    if pool["conn"] is None or pool["conn"].closed:
        pool["conn"] = psycopg.connect(pool["dsn"], row_factory=dict_row)
    return pool["conn"]


@asynccontextmanager
async def get_async_connection() -> AsyncIterator[AsyncConnection]:
    """Get an async PostgreSQL connection."""
    dsn = get_pg_dsn()
    async with await AsyncConnection.connect(dsn, row_factory=dict_row) as conn:
        yield conn


def init_db() -> None:
    """Initialize database tables if they don't exist."""
    from pathlib import Path

    from api.db import get_connection

    # Run migration files
    migrations_dir = Path(__file__).parent.parent / "sql" / "migrations"
    conn = get_connection()
    try:
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
        conn.close()


def query_one(sql: str, params: tuple | None = None) -> dict[str, Any] | None:
    """Execute a query and return one result."""
    import json

    conn = get_connection()

    # Convert dict params to JSON strings
    converted = []
    if params:
        for p in params:
            if isinstance(p, dict):
                converted.append(json.dumps(p))
            else:
                converted.append(p)
        params = tuple(converted)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()

    # Convert JSON strings back to dict
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


def query_all(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """Execute a query and return all results."""
    import json

    conn = get_connection()

    # Convert dict params to JSON strings
    converted = []
    if params:
        for p in params:
            if isinstance(p, dict):
                converted.append(json.dumps(p))
            else:
                converted.append(p)
        params = tuple(converted)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    # Convert JSON strings back to dict
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


def execute(sql: str, params: tuple | None = None) -> None:
    """Execute a query without returning results."""
    import json

    conn = get_connection()

    # Convert dict params to JSON strings
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


def insert_and_return(sql: str, params: tuple, returning: str = "id") -> str:
    """Insert a row and return the specified column."""
    import json

    conn = get_connection()
    try:
        # Convert dict params to JSON strings
        converted = []
        for p in params:
            if isinstance(p, dict):
                converted.append(json.dumps(p))
            else:
                converted.append(p)

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, tuple(converted))
            result = cur.fetchone()
        conn.commit()
        return result[returning] if result else None
    except Exception:
        conn.rollback()
        raise
