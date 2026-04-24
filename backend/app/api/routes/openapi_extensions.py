"""OpenAPI extensions: rate-limiting middleware and error response schemas."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING

from fastapi import Request, Response
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import Callable

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 100  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds


class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""

    def __init__(self, requests: int = RATE_LIMIT_REQUESTS, window: int = RATE_LIMIT_WINDOW):
        self.requests = requests
        self.window = window
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed and record it."""
        now = time.time()
        # Clean old entries
        self._requests[key] = [t for t in self._requests[key] if now - t < self.window]
        # Check limit
        if len(self._requests[key]) >= self.requests:
            return False
        # Record this request
        self._requests[key].append(now)
        return True

    def get_remaining(self, key: str) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        valid_requests = [t for t in self._requests[key] if now - t < self.window]
        return max(0, self.requests - len(valid_requests))

    def get_reset_time(self, key: str) -> float:
        """Get Unix timestamp when the window resets."""
        if not self._requests[key]:
            return time.time() + self.window
        return self._requests[key][0] + self.window


rate_limiter = RateLimiter()


def create_rate_limiting_middleware():
    """Create a FastAPI middleware for rate limiting."""

    async def middleware(request: Request, call_next: Callable) -> Response:
        # Use client IP as key
        client_ip = request.client.host if request.client else "anonymous"
        rate_limiting_key = f"ip:{client_ip}"

        if not rate_limiter.is_allowed(rate_limiting_key):
            remaining = 0
            reset_time = int(rate_limiter.get_reset_time(rate_limiting_key))
            return JSONResponse(
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(rate_limiter.requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(rate_limiter.window),
                },
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": rate_limiter.window,
                },
            )

        response = await call_next(request)

        # Add rate limit headers to successful responses
        remaining = rate_limiter.get_remaining(rate_limiting_key)
        reset_time = int(rate_limiter.get_reset_time(rate_limiting_key))
        response.headers["X-RateLimit-Limit"] = str(rate_limiter.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    return middleware


# Error response schemas for OpenAPI
ERROR_RESPONSE_404 = {
    "description": "Resource not found",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "required": ["detail"],
                "properties": {
                    "detail": {
                        "type": "string",
                        "example": "Resource not found",
                    },
                },
            },
            "example": {"detail": "Resource not found"},
        },
    },
}

ERROR_RESPONSE_422 = {
    "description": "Validation error",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "required": ["detail", "errors"],
                "properties": {
                    "detail": {"type": "string", "example": "Validation error"},
                    "errors": {
                        "type": "array",
                        "items": {"type": "object"},
                        "example": [{"loc": ["body", "field"], "msg": "field required"}],
                    },
                },
            },
        },
    },
}

PaginationLinksSchema = {
    "type": "object",
    "properties": {
        "next": {"type": "string", "description": "Link to next page"},
        "prev": {"type": "string", "description": "Link to previous page"},
        "first": {"type": "string", "description": "Link to first page"},
        "last": {"type": "string", "description": "Link to last page"},
    },
}

PaginationHeadersSchema = {
    "description": "Pagination headers",
    "headers": {
        "Link": {
            "schema": PaginationLinksSchema,
            "description": "Pagination links following RFC 5988",
        },
        "X-Total-Count": {
            "schema": {"type": "integer"},
            "description": "Total number of items across all pages",
        },
        "X-Page": {
            "schema": {"type": "integer"},
            "description": "Current page number",
        },
        "X-Page-Count": {
            "schema": {"type": "integer"},
            "description": "Total number of pages",
        },
        "X-Limit": {
            "schema": {"type": "integer"},
            "description": "Maximum number of items per page",
        },
    },
}

RateLimitingHeadersSchema = {
    "description": "Rate limiting headers",
    "headers": {
        "X-RateLimit-Limit": {
            "schema": {"type": "integer"},
            "description": "Maximum number of requests allowed in the current window",
        },
        "X-RateLimit-Remaining": {
            "schema": {"type": "integer"},
            "description": "Number of requests remaining in the current window",
        },
        "X-RateLimit-Reset": {
            "schema": {"type": "integer"},
            "description": "Unix timestamp when the rate limit window resets",
        },
        "Retry-After": {
            "schema": {"type": "integer"},
            "description": "Seconds to wait before retrying after rate limit is exceeded",
        },
    },
}

RATE_LIMIT_429_RESPONSE = {
    "description": "Rate limit exceeded",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "required": ["detail", "retry_after"],
                "properties": {
                    "detail": {
                        "type": "string",
                        "example": "Rate limit exceeded",
                    },
                    "retry_after": {
                        "type": "integer",
                        "example": 60,
                    },
                },
            },
            "example": {
                "detail": "Rate limit exceeded",
                "retry_after": 60,
            },
        },
    },
    "headers": RateLimitingHeadersSchema,
}
