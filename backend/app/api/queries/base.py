"""Base query helpers — thin wrappers around the connection pool.

Kept as a separate module so tests can patch get_connection /
release_connection at this namespace without affecting db.py internals.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import psycopg
from psycopg.rows import dict_row

from ..db import get_connection, release_connection

logger = logging.getLogger(__name__)


def query_one(sql: str, params: tuple | None = None) -> dict[str, Any] | None:
    conn = get_connection()
    converted: list[Any] = []
    if params:
        for p in params:
            converted.append(json.dumps(p) if isinstance(p, dict) else p)
        params = tuple(converted)

    try:
        with conn.cursor(row_factory=dict_row) as cur:  # type: ignore[arg-type]
            cur.execute(sql, params)
            row = cur.fetchone()

        if row:
            result: dict[str, Any] = {}
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
    except psycopg.Error:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def query_all(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    conn = get_connection()
    converted: list[Any] = []
    if params:
        for p in params:
            converted.append(json.dumps(p) if isinstance(p, dict) else p)
        params = tuple(converted)

    try:
        with conn.cursor(row_factory=dict_row) as cur:  # type: ignore[arg-type]
            cur.execute(sql, params)
            rows = cur.fetchall()

        result = []
        for row in rows:
            converted_row: dict[str, Any] = {}
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
    except psycopg.Error:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def execute(sql: str, params: tuple | None = None) -> None:
    conn = get_connection()
    converted: list[Any] = []
    if params:
        for p in params:
            converted.append(json.dumps(p) if isinstance(p, dict) else p)
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
    from psycopg.types.json import Jsonb

    conn = get_connection()
    converted: list[Any] = [Jsonb(p) if isinstance(p, dict) else p for p in params]

    try:
        with conn.cursor(row_factory=dict_row) as cur:  # type: ignore[arg-type]
            cur.execute(sql, tuple(converted))
            result = cur.fetchone()
        conn.commit()
        if result is None:
            raise ValueError(f"No result returned for returning clause: {returning}")
        return str(result[returning])
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
