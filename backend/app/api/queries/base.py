"""Base query functions for database operations.

This module contains the core query functions used by domain-specific query modules.
"""

from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row

from ..db import get_connection, release_connection


def query_one(sql: str, params: tuple | None = None) -> dict[str, Any] | None:
    """Execute a query and return one result."""
    conn = get_connection()
    converted = []
    if params:
        for p in params:
            if isinstance(p, dict):
                # Use psycopg's Jsonb type for proper JSON handling
                from psycopg.types.json import Jsonb
                converted.append(Jsonb(p))
            else:
                converted.append(p)
        params = tuple(converted)

    try:
        with conn.cursor(row_factory=dict_row) as cur:  # type: ignore[arg-type]
            cur.execute(sql, params)
            row = cur.fetchone()

        if row:
            return dict(row)
        return None
    finally:
        release_connection(conn)


def query_all(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """Execute a query and return all results."""
    conn = get_connection()
    converted = []
    if params:
        for p in params:
            if isinstance(p, dict):
                # Use psycopg's Jsonb type for proper JSON handling
                from psycopg.types.json import Jsonb
                converted.append(Jsonb(p))
            else:
                converted.append(p)
        params = tuple(converted)

    try:
        with conn.cursor(row_factory=dict_row) as cur:  # type: ignore[arg-type]
            cur.execute(sql, params)
            rows = cur.fetchall()

        return [dict(row) for row in rows]
    finally:
        release_connection(conn)


def execute(sql: str, params: tuple | None = None) -> None:
    """Execute a query without returning results."""
    conn = get_connection()
    converted = []
    if params:
        for p in params:
            if isinstance(p, dict):
                # Use psycopg's Jsonb type for proper JSON handling
                from psycopg.types.json import Jsonb
                converted.append(Jsonb(p))
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
    from psycopg.types.json import Jsonb

    conn = get_connection()
    converted = []
    for p in params:
        if isinstance(p, dict):
            converted.append(Jsonb(p))
        else:
            converted.append(p)

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
