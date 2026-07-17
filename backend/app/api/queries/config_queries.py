from __future__ import annotations

from typing import Any

from .base import execute as _execute
from .base import insert_and_return as _insert_and_return
from .base import query_all as _query_all
from .base import query_one as _query_one


def query_all_configs(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    return _query_all(sql, params)


def query_one_config(sql: str, params: tuple | None = None) -> dict[str, Any] | None:
    return _query_one(sql, params)


def execute_config(sql: str, params: tuple | None = None) -> None:
    _execute(sql, params)


def insert_config_and_return(sql: str, params: tuple, returning: str = "id") -> str:
    return _insert_and_return(sql, params, returning)
