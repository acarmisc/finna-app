"""Shared PostgreSQL database helpers for FinOps extractors.

This module provides common database operations used across all extractors
to avoid code duplication and ensure consistent batch-insert patterns.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Sequence

import psycopg
from psycopg import sql

logger = logging.getLogger(__name__)

__all__ = ["batch_insert_named", "batch_insert_tuple"]


def batch_insert_named(
    conn: psycopg.Connection,
    records: Sequence[dict[str, Any]],
    insert_sql: str,
    commit: bool = True,
) -> int:
    """Insert records using executemany() with named placeholders.

    Designed for use with SQL like:
        INSERT INTO table (col1, col2) VALUES (%(col1)s, %(col2)s)

    Args:
        conn: Open PostgreSQL connection.
        records: Sequence of dicts, each containing all named parameters.
        insert_sql: INSERT SQL with named placeholders.
        commit: Whether to commit (default True).

    Returns:
        Number of records inserted.
    """
    if not records:
        return 0

    with conn.cursor() as cur:
        cur.executemany(insert_sql, records)

    if commit:
        conn.commit()

    return len(records)


def batch_insert_tuple(
    conn: psycopg.Connection,
    records: Sequence[tuple],
    insert_sql: sql.SQL,
    commit: bool = True,
) -> int:
    """Insert records using executemany() with tuple values.

    Designed for use with SQL like:
        INSERT INTO table VALUES (%s, %s)

    Args:
        conn: Open PostgreSQL connection.
        records: Sequence of tuples with values in SQL order.
        insert_sql: psycopg.sql.SQL INSERT statement with %s placeholders.
        commit: Whether to commit (default True).

    Returns:
        Number of records inserted.
    """
    if not records:
        return 0

    with conn.cursor() as cur:
        cur.executemany(insert_sql, records)

    if commit:
        conn.commit()

    return len(records)
