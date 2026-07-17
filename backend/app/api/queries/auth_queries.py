from __future__ import annotations

from typing import Any

from .base import insert_and_return as _insert_and_return
from .base import query_one as _query_one


def query_one_user(sql: str, params: tuple | None = None) -> dict[str, Any] | None:
    return _query_one(sql, params)


def insert_user_and_return(sql: str, params: tuple, returning: str = "id") -> str:
    return _insert_and_return(sql, params, returning)
