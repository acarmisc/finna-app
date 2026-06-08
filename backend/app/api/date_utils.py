"""Shared date/window resolution utilities."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Union


def resolve_window(
    window: Optional[str],
    start_date: Optional[Union[str, datetime]],
    end_date: datetime,
) -> tuple[datetime, datetime]:
    """Resolve window shortcut + CLI aliases into concrete start/end dates."""
    if window and window not in ("mtd", "7d", "30d", "90d"):
        window = None

    if window == "mtd":
        start = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif window == "7d":
        start = end_date - timedelta(days=7)
    elif window == "30d":
        start = end_date - timedelta(days=30)
    elif window == "90d":
        start = end_date - timedelta(days=90)
    else:
        if isinstance(start_date, str):
            start = datetime.fromisoformat(start_date)
        else:
            start = start_date or (end_date - timedelta(days=30))

    return start, end_date
