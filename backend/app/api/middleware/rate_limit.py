"""Rate limiting middleware for FastAPI."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from fastapi import Request, Response

from ..auth import get_current_user

# Rate limit configuration
RATE_LIMIT_REQUESTS = 100  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds


@dataclass
class RateLimitInfo:
    """Rate limit metadata for response headers."""
    limit: int
    remaining: int
    reset: float
    retry_after: int | None = None


# In-memory rate limiting storage (for production, use Redis)
rate_limit_storage: dict[str, list[float]] = defaultdict(list)


async def check_rate_limit(client_id: str) -> RateLimitInfo:
    """Check if client is rate limited and return rate limit info."""
    current_time = time.time()
    window_start = current_time - RATE_LIMIT_WINDOW

    # Clean old entries and get current request timestamps
    rate_limit_storage[client_id] = [
        t for t in rate_limit_storage[client_id]
        if t > window_start
    ]

    # Check if rate limited
    if len(rate_limit_storage[client_id]) >= RATE_LIMIT_REQUESTS:
        retry_after = int(RATE_LIMIT_WINDOW - (current_time - rate_limit_storage[client_id][0]))
        return RateLimitInfo(
            limit=RATE_LIMIT_REQUESTS,
            remaining=0,
            reset=current_time + RATE_LIMIT_WINDOW,
            retry_after=retry_after
        )

    # Record this request
    rate_limit_storage[client_id].append(current_time)

    return RateLimitInfo(
        limit=RATE_LIMIT_REQUESTS,
        remaining=RATE_LIMIT_REQUESTS - len(rate_limit_storage[client_id]),
        reset=current_time + RATE_LIMIT_WINDOW
    )


def add_rate_limit_headers(response: Response, info: RateLimitInfo) -> Response:
    """Add rate limit headers to response."""
    response.headers["X-RateLimit-Limit"] = str(info.limit)
    response.headers["X-RateLimit-Remaining"] = str(info.remaining)
    response.headers["X-RateLimit-Reset"] = str(int(info.reset))

    if info.retry_after is not None:
        response.headers["Retry-After"] = str(info.retry_after)

    return response


async def rate_limit_middleware(request: Request, call_next: Any) -> Response:
    """FastAPI HTTP rate limiting middleware."""
    # Get client identifier (could be user ID, API key, or IP)
    client_id = "anonymous"

    try:
        user = await get_current_user(request)
        if user:
            client_id = user.get("username", "anonymous")
    except Exception:
        # Fall back to IP if auth fails
        pass

    # Check rate limit
    rate_info = await check_rate_limit(client_id)

    # Create response
    response = await call_next(request)

    # Add rate limit headers
    add_rate_limit_headers(response, rate_info)

    return response
